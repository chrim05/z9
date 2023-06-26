from data import *
from typing import cast

class MrGen:
  '''
  middle representation generator
  '''

  def __init__(self, unit) -> None:
    from unit import TranslationUnit

    self.unit: TranslationUnit = unit

  @property
  def root(self) -> MultipleNode:
    return self.unit.root

  @property
  def tab(self) -> SemaTable:
    return self.unit.tab

  def get_declaration_name(self, node: Node | None) -> str:
    if isinstance(node, Token) and node.kind == 'id':
      return cast(str, node.value)

    if not isinstance(node, SyntaxNode):
      raise UnreachableError()

    match node.syntax_name:
      case 'Declarator':
        return self.get_declaration_name(node['direct_declarator'])

      case \
        'Declaration' | \
        'FunctionDefinition' | \
        'ParameterListDeclarator':
          return self.get_declaration_name(node['declarator'])

      case _:
        raise UnreachableError()

  def create_numeric_typ_from_dspecs(
    self,
    loc: Loc,
    specs: dict[str, int],
    typedefed: Token | None
  ) -> Typ:
    if typedefed is not None:
      raise NotImplementedError()

    combinations = [
      ('void',     {'void': 1}),
      ('char',     {'char': 1}),
      ('int',      {'int': 1}),
      ('short',    {'short': 1, 'int': (0, 1)}),
      ('long',     {'long': 1, 'int': (0, 1)}),
      ('longlong', {'long': 2, 'int': (0, 1)}),
    ]

    def match_combination(comb: dict[str, int | tuple[int, ...]]) -> bool:
      for kind, count in comb.items():
        if kind not in specs:
          return False

        if isinstance(count, tuple) and specs[kind] not in count:
          return False

        if specs[kind] != count:
          return False

      return True

    for kind, comb in combinations:
      if not match_combination(comb): # type: ignore[arg-type]
        continue

      if kind == 'void':
        return VoidTyp()

      return IntTyp(kind)

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

    if isinstance(typ, VoidTyp) and len(quals) != 0:
      self.unit.report(
        'type specifier "void" does not accept any type qualifier',
        loc
      )
      return typ

    for qual in quals:
      match qual:
        case 'const':
          typ.is_const = True

        case _:
          raise UnreachableError()

    return typ

  def make_pointer_typ_from_pointer_declarator(
    self,
    typ: Typ,
    node: Node | None
  ) -> Typ:
    if not isinstance(node, SyntaxNode) or node is None:
      return typ

    # TODO: add the pointer qualifiers
    typ = self.make_pointer_typ_from_pointer_declarator(
      PointerTyp(typ),
      node['pointer']
    )

    return typ


  def make_pointer_typ_from_declaration(self, typ: Typ, node: Node) -> Typ:
    if not isinstance(node, SyntaxNode):
      raise UnreachableError()

    d = node['declarator']

    if (
      not isinstance(d, SyntaxNode) or 
      d.syntax_name != 'Declarator'
    ):
      return typ

    return self.make_pointer_typ_from_pointer_declarator(
      typ,
      d['pointer']
    )
    
  def get_declaration_typ(self, node: Node | None) -> Typ:
    if isinstance(node, MultipleNode):
      return self.create_typ_from_dspecs(node)

    if not isinstance(node, SyntaxNode):
      raise UnreachableError()

    match node.syntax_name:
      case \
        'Declaration' | \
        'FunctionDefinition':
          typ = self.get_declaration_typ(node['declaration_specifiers'])
          return self.make_pointer_typ_from_declaration(typ, node)

      case _:
        raise UnreachableError()

  def predeclare_top_level(self, node: Node) -> None:
    if node.is_empty_decl():
      raise NotImplementedError()

    name = self.get_declaration_name(node)
    self.tab.declare(name, node, node.loc)

  def process_top_level(self, node: Node) -> None:
    typ = self.get_declaration_typ(node)
    print(typ)

  def gen_whole_unit(self) -> None:
    for top_level in self.root.nodes:
      self.predeclare_top_level(top_level)

    for sym in self.tab.members.values():
      self.process_top_level(cast(Node, sym))