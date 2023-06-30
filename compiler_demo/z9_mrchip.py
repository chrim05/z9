from data import *

class MrChip:
  def __init__(self, unit) -> None:
    from unit import TranslationUnit

    self.unit: TranslationUnit = unit
    self.vstack: list[Val | FinIndex] = []

    self.sym: Symbol
    self.code: FinRepr
    self.memories: list[SymTable] = [self.unit.tab]

  @property
  def mem(self) -> SymTable:
    return self.memories[-1]

  def push_mem(self) -> None:
    self.memories.append(self.mem.copy())

  def pop_mem(self) -> None:
    self.memories.pop()

  def create_numeric_typ_from_dspecs(
    self,
    loc: Loc,
    specs: dict[str, int],
    typedefed: Token | None
  ) -> Typ:
    if typedefed is not None:
      raise NotImplementedError()

    # awkward pythonic type notation
    combinations: list[tuple[str, dict[str, int]]]
    # https://en.wikipedia.org/wiki/C_data_types
    combinations = [
      ('void',     {'void': 1}),

      ('char',     {'char': 1}),

      ('int',      {'int': 1}),
      
      ('short',    {'short': 1}),
      ('short',    {'short': 1, 'int': 1}),

      ('long',     {'long': 1}),
      ('long',     {'long': 1, 'int': 1}),

      ('longlong', {'long': 2}),
      ('longlong', {'long': 2, 'int': 1}),
    ]

    def match_combination(comb: dict[str, int]) -> bool:
      if len(comb) != len(specs):
        return False

      for kind, count in comb.items():
        if kind not in specs:
          return False

        if specs[kind] != count:
          return False

      return True

    for kind, comb in combinations:
      if not match_combination(comb): # type: ignore[arg-type]
        continue

      if kind == 'void':
        return VoidTyp()

      return IntTyp(kind, 'unsigned' not in comb)

    self.unit.report('invalid combination of numeric types', loc)
    return PoisonedTyp()

  def create_typ_from_dspecs(self, dspecs: MultipleNode) -> Typ:
    from z9_dparser import TYPE_QUALS, TYPE_SPECS

    loc = dspecs.nodes[0].loc
    quals: set[str] = set()
    specs: dict[str, int] = {}
    typedefed: Token | None = None

    for dspec in dspecs.nodes:
      # not always true,
      # but at the moment it's okay
      assert isinstance(dspec, Token)
      k = dspec.kind

      if k in TYPE_QUALS:
        quals.add(k)
        continue

      if k in TYPE_SPECS:
        if k not in specs:
          specs[k] = 0

        specs[k] += 1
        continue

      if k == 'id':
        assert typedefed is None
        typedefed = dspec
        continue

      raise UnreachableError()

    if len(specs) == 0 and typedefed is None:
      self.unit.report('incomplete type', loc)
      return PoisonedTyp()

    typ = self.create_numeric_typ_from_dspecs(loc, specs, typedefed)

    self.apply_typequals_on_typ(typ, quals)

    return typ

  def apply_typequals_on_typ(self, typ: Typ, quals: set[str]) -> None:
    for qual in quals:
      match qual:
        case 'const':
          typ.is_const = True

        case _:
          raise UnreachableError()

  def type_qualifier_list_to_quals(self, qual_list: MultipleNode) -> set[str]:
    return set(
      # not always true,
      # but at the moment it's okay
      cast(Token, q).kind
        for q in qual_list.nodes
    )

  def make_fntyp_from_param_list_declarator(
    self,
    ret: Typ,
    node: SyntaxNode
  ) -> Typ:
    from z9_mrgen import get_declaration_name

    # TODO: implement ellipsis
    params = cast(MultipleNode, node['parameter_list'])

    typs: list[Typ] = [
      self.get_declaration_typ(p)
        for p in params.nodes
    ]
    names: list[Token | None] = [
      get_declaration_name(p)
        for p in params.nodes
    ]

    return FnTyp(ret, typs, names)

  def make_typ_from_declarator(self, typ: Typ, d: Node | None) -> Typ:
    if not isinstance(d, SyntaxNode):
      return typ

    match d.syntax_name:
      case 'ArrayDeclarator':
        return self.make_typ_from_declarator(
          # TODO: add the evaluated size initializer
          ArrayTyp(typ, POISONED_VAL), d['declarator']
        )

      case 'ParameterListDeclarator':
        typ = self.make_fntyp_from_param_list_declarator(
          typ, d
        )

        return self.make_typ_from_declarator(
          typ, d['declarator']
        )

      case 'Pointer':
        typ = self.make_typ_from_declarator(
          typ, d['pointer']
        )

        typ = PointerTyp(typ)

        self.apply_typequals_on_typ(
          typ,
          self.type_qualifier_list_to_quals(
            cast(MultipleNode, d['type_qualifier_list'])
          )
        )

        return typ

      case 'Declarator':
        # for the pointer
        typ = self.make_typ_from_declarator(
          typ, d['pointer']
        )

        # recursively (maybe there is the array too)
        typ = self.make_typ_from_declarator(
          typ, d['direct_declarator']
        )

        return typ

      case _:
        return typ
    
  def get_declaration_typ(self, node: Node | None) -> Typ:
    if isinstance(node, MultipleNode):
      return self.create_typ_from_dspecs(node)

    if not isinstance(node, SyntaxNode):
      raise UnreachableError()

    match node.syntax_name:
      case \
        'Declaration'        | \
        'FunctionDefinition' | \
        'ParameterDeclaration':
          typ = self.get_declaration_typ(node['declaration_specifiers'])
          typ = self.make_typ_from_declarator(typ, node['declarator'])
          return typ

      case _:
        raise UnreachableError()

  def maybe_coerce(self, expected: Typ, actual: Typ) -> Typ:
    typs  = [type(expected), type(actual)]
    get_t = lambda t: [expected, actual][typs.index(t)]

    if LitIntTyp in typs:
      if IntTyp in typs:
        return get_t(IntTyp)

      # the default type for literal ints
      # is `int`, which is always 32bit wide in z9
      return IntTyp('int', True)

    return actual

  def typcheck(self, expected: Typ, actual: Typ, l: Loc) -> Typ:
    actual = self.maybe_coerce(expected, actual)

    if expected == actual:
      return actual

    self.unit.report(
      f'expected type "{expected}", got "{actual}"', l
    )
    return expected

  def vload(self, val: Val | FinIndex) -> None:
    self.vstack.append(val)

  def vpop(self) -> Val | FinInstr:
    v = self.vstack.pop()

    if isinstance(v, FinIndex):
      return self.code[v]

    return v

  def maybe_coerce_binary(self, l: Typ, r: Typ) -> tuple[Typ, Typ]:
    typs  = [type(l), type(r)]
    get_t = lambda t: [l, r][typs.index(t)]

    if LitIntTyp in typs and IntTyp in typs:
      return (get_t(IntTyp), get_t(IntTyp))

    return (l, r)

  def typcheck_binary(self, l: Typ, r: Typ, opcode: Opcode, loc: Loc) -> tuple[Typ, Typ]:
    l, r = self.maybe_coerce_binary(l, r)

    if l == r:
      return (l, r)

    op = arithmetic_opcodes.inverse[opcode]
    self.unit.report(
      f'types "{l}" and "{r}" are not compatible for binary operator "{op}"',
      loc
    )
    return (l, r)

  def get_one_runtime_typ(self, l: Val | FinInstr, r: Val | FinInstr) -> Typ:
    if isinstance(l, FinInstr):
      return l.typ  # type: ignore[return-value]

    return r.typ  # type: ignore[return-value]

  def perform_meta_op(self, op: Opcode, l: Any, r: Any) -> Any:
    match op:
      case Opcode.ADD: return l + r
      case Opcode.SUB: return l - r
      case Opcode.MUL: return l * r

      case _:
        raise UnreachableError()

  def fold_meta(self, op: Opcode, l: Val | FinInstr, r: Val | FinInstr, loc: Loc) -> Val | None:
    if isinstance(l, FinInstr) or isinstance(r, FinInstr):
      return None

    if not l.is_meta() or not r.is_meta():
      return None

    # TODO: is this okay?
    #       i think it's broken
    if l.typ != r.typ:
      return None

    return Val(l.typ, self.perform_meta_op(op, l.meta, r.meta), loc)

  def as_typed(self, v: Val | FinIndex) -> Val | FinInstr:
    if isinstance(v, Val):
      return v

    return self.code[v]

  def fold_meta_or_typcheck_binary(self, op: Opcode, l: Val | FinInstr, r: Val | FinInstr, loc: Loc) -> None:
    if (binary := self.fold_meta(op, l, r, loc)) is not None:
      self.vload(binary)
      return

    # TODO: emit instructions
    l.typ, r.typ = self.typcheck_binary(l.typ, r.typ, op, loc)
    op_typ = self.get_one_runtime_typ(l, r)

    self.vload(
      self.code.emit(op, op_typ, (self.val_or_idx(l), self.val_or_idx(r)))
    )

  def val_or_idx(self, v: Val | FinInstr) -> Val | FinIndex:
    if isinstance(v, Val):
      return v

    return v.idx

  def process_instr(self, i: MidInstr) -> None:
    fntyp: FnTyp = cast(FnTyp, self.sym.typ)

    match i.op:
      case Opcode.RET_VOID:
        self.typcheck(fntyp.ret, VoidTyp(), i.loc)
        self.code.ret_void()

      case Opcode.LOAD_META_VALUE:
        self.vload(cast(Val, i.ex))

      case Opcode.RET:
        v = self.vpop()
        v.typ = self.typcheck(fntyp.ret, v.typ, i.loc)

        self.code.ret(self.val_or_idx(v))

      # TODO: implement also operators
      #       for user-defined types
      case Opcode.ADD | Opcode.SUB | Opcode.MUL:
        r = self.vpop()
        l = self.vpop()

        self.fold_meta_or_typcheck_binary(i.op, l, r, i.loc)

      case Opcode.LOAD_NAME:
        name = cast(str, i.ex)

        if (m := self.mem.get_member(name)) is not None:
          # TODO: add the ability to get non local symbols
          #       such as functions
          assert(isinstance(m, LocalSymbol))
          self.vload(self.code.load_ptr(m.i))
        else:
          self.vload(POISONED_VAL)

      case _:
        raise UnreachableError()

  def process_fnsym(self, sym: FnSymbol) -> None:
    self.sym = sym
    self.code = FinRepr()
    self.push_mem()

    sym.typ = fntyp = cast(FnTyp, self.get_declaration_typ(sym.fn.node))

    # declaring parameters as locals
    for ptyp, pname in zip(fntyp.params, fntyp.pnames):
      if pname is None:
        continue

      idx = self.code.local(ptyp)
      self.code.store_next_param(idx)

      self.mem.declare_local(
        cast(str, pname.value),
        idx,
        ptyp,
        pname.loc
      )

    for i in sym.fn.code.instructions:
      self.process_instr(i)

    sym.fn.code = self.code # type: ignore[assignment]
    self.pop_mem()

  def process_sym(self, sym: Symbol) -> None:
    if not isinstance(sym, FnSymbol):
      raise NotImplementedError()

    self.process_fnsym(sym)

  def process_whole_tab(self) -> None:
    for sym in self.unit.tab.members.values():
      self.process_sym(cast(Symbol, sym))