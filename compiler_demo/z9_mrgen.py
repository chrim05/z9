from data import *
from typing import cast

'''
the idea of this module is to generate a bunch
of Middle Representations (Mr) for each top level declaration;

the idea is to generate untyped ir, but at the same time
to track the new declarations (and the top level ones),
so that it's easy to parse expressions/statements/local-declarations
correctly, without ambiguities, because we know at this stage
of the compilation all the declarations (top levels and local ones);

then the ir is checked and optionally runned by another component
'''

class MrGen:
  '''
  middle representation generator
  '''

  def __init__(self, unit) -> None:
    from unit import TranslationUnit

    self.unit: TranslationUnit = unit
    self.functions: list['FnMrGen'] = []

  @property
  def fn(self) -> 'FnMrGen':
    return self.functions[-1]

  @property
  def root(self) -> MultipleNode:
    return self.unit.root

  @property
  def tab(self) -> SymTable:
    return self.unit.tab

  def get_declaration_name(self, node: Node | None) -> Token | None:
    if isinstance(node, Token) and node.kind == 'id':
      return node

    if not isinstance(node, SyntaxNode):
      return None

    match node.syntax_name:
      case 'Declarator':
        return self.get_declaration_name(node['direct_declarator'])

      case                       \
        'ArrayDeclarator'      | \
        'Declaration'          | \
        'ParameterDeclaration' | \
        'FunctionDefinition'   | \
        'ParameterListDeclarator':
          return self.get_declaration_name(node['declarator'])

      case _:
        return None

  # CORRECTION: this stuff should be performed
  #             on the untyped ir on the next
  #             component, the one which also
  #             performs type checks
  '''
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
    # TODO: implement ellipsis
    params = cast(MultipleNode, node['parameter_list'])

    typs: list[Typ] = [
      self.get_declaration_typ(p)
        for p in params.nodes
    ]
    names: list[Token | None] = [
      self.get_declaration_name(p)
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
  '''

  def predeclare_top_level(self, node: Node) -> None:
    if node.is_empty_decl():
      raise NotImplementedError()

    assert isinstance(node, SyntaxNode)

    key = {
      'Declaration': 'initializer',
      'FunctionDefinition': 'body'
    }[node.syntax_name]
    
    name = cast(Token, self.get_declaration_name(node))
    is_weak = node[key] is None

    self.tab.declare(
      cast(str, name.value),
      node,
      is_weak,
      name.loc
    )

  def process_top_level(self, node: Node, is_weak: bool) -> Symbol:
    # typ = self.get_declaration_typ(node)
    
    assert isinstance(node, SyntaxNode)
    match node.syntax_name:
      case 'FunctionDefinition':
        # heading declaration (must be interpreted
        # as extern function, since at this stage
        # MrGen should already know its definition
        # but it doesn't)
        if is_weak:
          return ExternFnSymbol(node)

        self.functions.append(FnMrGen(
          self,
          # cast(FnTyp, typ),
          node
        ))

        try:
          self.fn.process()
        except ParsingError:
          # we can still parse and generate
          # ir for all other top level
          # declarations, even though
          # this one was internally
          # syntactically-malformed
          pass

        fn = self.functions.pop()

        return FnSymbol(fn)

      case _:
        raise UnreachableError()

  def gen_whole_unit(self) -> None:
    for top_level in self.root.nodes:
      self.predeclare_top_level(top_level)

    for name, value in self.tab.members.items():
      assert not isinstance(value, Symbol)
      sym, is_weak = value

      self.tab.members[name] = self.process_top_level(
        cast(Node, sym),
        is_weak
      )

    # checking that all weak declarations
    # match the signature with the complete ones
    #
    # CORRECTION: this should be done in the next component
    #             (the one which also type checks the ir)
    '''
    for name, weak_decls in self.tab.heading_decls.items():
      complete_decl = self.tab.members[name]
      assert isinstance(complete_decl, Symbol)

      for weak_decl in weak_decls:
        weak_decl_typ = self.get_declaration_typ(weak_decl)

        if complete_decl.typ != weak_decl_typ:
          self.unit.report(
            'heading declaration is not compatible with its definition',
            weak_decl.loc
          )
    '''

class FnMrGen:
  '''
  content parser also from:
  https://github.com/katef/kgt/blob/main/examples/c99-grammar.iso-ebnf
  '''

  def __init__(self, gen: MrGen, node: SyntaxNode) -> None:
    from unit import TranslationUnit

    self.gen: MrGen = gen
    # self.typ: FnTyp = typ
    self.node: SyntaxNode = node
    self.code: MidRepr = MidRepr()
    
    self.tokens: list[Token]
    self.index: int = 0

  @property
  def unit(self): # -> TranslationUnit:
    return self.gen.unit

  @property
  def cur(self) -> Token:
    return self.tok(0)

  @property
  def bck(self) -> Token:
    return self.tok(-1)

  def skip(self, count: int = 1) -> None:
    self.index += count

  def tok(self, offset: int) -> Token:
    if not self.has_token(offset):
      return Token('eof', None, self.tokens[-1].loc)

    return self.tokens[self.index + offset]

  def has_token(self, offset: int = 0) -> bool:
    return self.index + offset < len(self.tokens)

  def token(self, *kinds: str) -> bool:
    for kind in kinds:
      if kind == self.cur.kind:
        self.skip()
        return True

    return False

  def expect_token(self, kind: str) -> Token:
    token = self.cur

    if not self.token(kind):
      self.unit.report(
        f'expected token "{kind}", matched "{self.cur.kind}"',
        self.cur.loc
      )

    return token

  def pg_postfix_expression(self) -> None:
    # TODO: if `(type-name)` -> cast
    #
    # NOTE: this should be done here before
    #       (and not inside) `pg_primary_expression`
    #       because of the lower cast operator priority

    self.pg_primary_expression()

    while self.token('[', '(', '.', '->', '++', '--'):
      op = self.bck

      match op.kind:
        case _:
          raise NotImplementedError()
          # raise UnreachableError()

  @recoverable
  def typename(self) -> bool:
    # TODO
    return False

  def unary_operators(self) -> bool:
    return self.token(
      '&', '*', '+',
      '-', '~', '!',
    )

  def pg_cast_expression(self) -> None:
    if self.typename():
      raise NotImplementedError()
      return

    self.pg_unary_expression()

  def pg_unary_expression(self) -> None:
    if self.token('++', '--'):
      self.pg_unary_expression()
      # TODO: gen code for these operators
      return

    if self.unary_operators():
      op = self.bck
      raise NotImplementedError()
      return

    # TODO: sizeof expression | (sizeof | _Alignof)(type-name)

    self.pg_postfix_expression()

  def pg_primary_expression(self) -> None:
    # TODO: implement `__func__` and generic-selection here
    if not self.token('num', 'id', 'str', '('):
      self.unit.report(
        'expected primary expression', self.cur.loc
      )
      return

    p = self.bck

    match p.kind:
      case 'num':
        v = Val(
          MetaIntTyp(),
          cast(int, self.bck.value),
          self.bck.loc
        )

        self.code.load_metavalue(p.loc, v)

      case 'id':
        self.code.load_name(p.loc, cast(str, p.value))

      case '(':
        self.pg_expression()
        self.expect_token(')')

      case _:
        raise UnreachableError()      

  def assignment_operators(self) -> bool:
    return self.token(
      '=', '*=', '/=',
      '%=', '+=', '-=',
      '<<=', '>>=', '&=',
      '^=', '|=',
    )

  def pg_binary_expression(
    self,
    ops: tuple[str, ...],
    parse_fn: Callable[[], None]
  ) -> None:
    parse_fn()

    while self.token(*ops):
      op = self.bck

      parse_fn()
      self.code.emit_op(op.loc, op.kind)

  def pg_conditional_expression(self) -> None:
    # TODO: implement logical operators
    #       in a way that they are actually "logical"

    multiplicative = (
      ('*', '/', '%'), self.pg_cast_expression
    )

    additive = (
      ('+', '-'), lambda: self.pg_binary_expression(*multiplicative)
    )

    shift = (
      ('<<', '>>'), lambda: self.pg_binary_expression(*additive)
    )

    relational = (
      ('<', '>', '<=', '>='), lambda: self.pg_binary_expression(*shift)
    )

    equality = (
      ('==', '!='), lambda: self.pg_binary_expression(*relational)
    )

    and_ = (
      ('&',), lambda: self.pg_binary_expression(*equality)
    )

    xor = (
      ('^',), lambda: self.pg_binary_expression(*and_)
    )

    or_ = (
      ('|',), lambda: self.pg_binary_expression(*xor)
    )

    # the top of the chain
    self.pg_binary_expression(
      *or_
    )

    # TODO: while self.token('?')

  def pg_assignment_expression(self) -> None:
    self.pg_conditional_expression()

    if not self.assignment_operators():
      return

    raise NotImplementedError()

  def pg_expression(self, is_stmt: bool = False) -> None:
    self.pg_assignment_expression()

    while is_stmt and self.token(','):
      loc = self.cur.loc
      self.pg_assignment_expression()

  def pg_return(self, l: Loc) -> None:
    if self.token(';'):
      self.code.ret_void(l)
      return
    
    self.pg_expression()
    self.expect_token(';')
    self.code.ret(l)

  def jump_statement(self) -> bool:
    if self.token('return'):
      self.pg_return(self.bck.loc)
      return True

    # TODO: add other jump statements
    return False

  def statement(self) -> bool:
    if self.jump_statement():
      return True

    # TODO: add the other statements
    #       and remember that expression
    #       must be called with `is_stmt=True`
    #       to avoid ambiguity of `decl, decl, ...`
    #       vs `expr, expr, ...`
    return False

  def declaration(self) -> bool:
    # TODO: implement this
    #
    # NOTE: this function should also
    #       locally declare/register the declaration
    #       so that we can parse next local syntaxes
    #       without ambiguities, also when they use
    #       types declared locally
    return False

  def decl_or_statement(self) -> None:
    if self.statement():
      return

    self.expect_matching(
      self.declaration(),
      'expected either declaration or statement'
    )

  def expect_matching(self, matching: bool, error_message: str) -> None:
    if matching:
      return

    self.unit.report(
      f'{error_message}, matched token "{self.cur.kind}"',
      self.cur.loc
    )
    raise ParsingError()

  # "pg" stands for "parse and generate"
  # which means that function is gonna
  # parse the next tokens and in the mean while
  # emit untyped ir for the parsed tokens
  def pg_fnbody(self) -> None:
    # TODO: generate declaration instructions
    #       for parameters

    while self.has_token():
      self.decl_or_statement()

  def process(self) -> None:
    self.tokens = cast(CompoundNode, self.node['body']).tokens

    # an empty body may make the parsing functions
    # to raise errors because they need at least one token
    # to work with
    if len(self.tokens) == 0:
      return

    self.pg_fnbody()