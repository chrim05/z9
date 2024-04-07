from data import *
from typing import Callable, cast, NoReturn
from json import dumps

CLASS_SPECS = (
  'typedef', 'extern', 'static',
  '_Thread_local', 'auto', 'register'
)

FUNCTION_SPECS = ('inline', '_Noreturn')

TYPE_QUALS = (
  'const', 'restrict',
  'volatile', '_Atomic',
  '_Cdecl'
)

TYPE_SPECS = (
  'void', 'char', 'short',
  'int', 'long', 'float',
  'double', 'signed',
  'unsigned', '_Bool',
  '_Complex', '_Imaginary'
)

class DParser:
  '''
  Lazy parser for declarations, from:
  https://github.com/katef/kgt/blob/main/examples/c99-grammar.iso-ebnf

  i use multiple parsing hacks for recognizing identifiers
  as typedef-ed names, and this allows the compiler to avoid
  forward declarations for members
  '''

  def __init__(self, unit) -> None:
    from unit import TranslationUnit
    self.unit: TranslationUnit = unit
    self.index: int = 0
    # i just assign it with a placeholder, because it will be always
    # overwritten
    self.current_dspecs: MultipleNode = MultipleNode(self.cur.loc)

  @property
  def cur(self) -> Token:
    return self.tok(0)

  def tok(self, offset: int) -> Token:
    if not self.has_token(offset):
      return Token('eof', None, self.unit.tokens[-1].loc)

    return self.unit.tokens[self.index + offset]

  def has_token(self, offset: int = 0) -> bool:
    return self.index + offset < len(self.unit.tokens)

  def skip(self, count: int = 1):
    self.index += count

  def token(self, *kinds: str) -> Token | None:
    tok: Token = self.cur

    for kind in kinds:
      if kind == tok.kind:
        self.skip()
        return tok

    return None

  def identifier(self) -> Token | None:
    return self.token('id')

  def expect_token(self, kind: str) -> Token:
    token: Token | None = self.token(kind)

    if token is None:
      self.unit.report(
        f'expected token "{kind}", matched "{self.cur.kind}"',
        self.cur.loc
      )
      return self.cur

    return token

  def collect_compound_statement(self) -> CompoundNode:
    if self.cur.kind != '{':
      self.unit.report(
        'after declarator, function definition wants a compound statement (its body)',
        self.cur.loc
      )
      return CompoundNode(self.cur.loc)

    opener: Token = self.expect_token('{')
    compound = CompoundNode(opener.loc)
    nest_level: int = 0

    while True:
      if not self.has_token():
        self.unit.report('body not closed', opener.loc)
        break

      if self.cur.kind == '{':
        nest_level += 1
      elif self.cur.kind == '}':
        if nest_level == 0:
          break

        nest_level -= 1

      compound.tokens.append(self.cur)
      self.skip()

    self.token('}')
    return compound

  def log(self, obj: object) -> None:
    print(f'LOG(cur: {self.cur}): {obj}')

  @recoverable
  def function_definition(
    self,
    dspecs: Node,
    declarator: Node,
    allow_method_mods: bool
  ) -> Node | None:
    '''
    TODO:
      * [declaration-list]
    '''

    if not isinstance(declarator, SyntaxNode):
      return None

    if declarator.syntax_name == 'ParameterListDeclarator':
      actual_decl = declarator.data['declarator']
    elif (
      declarator.syntax_name == 'Declarator' and
      isinstance(dd := declarator.data['direct_declarator'], SyntaxNode) and
      dd.syntax_name == 'ParameterListDeclarator'
    ):
      actual_decl = dd
    else:
      return None

    # it may be a function pointer, this means no body is involved
    # but it must be interpreted as a declaration
    if (
      isinstance(actual_decl, SyntaxNode) and
      actual_decl.syntax_name == 'Declarator' and
      actual_decl.data['pointer'] is not None
    ):
      return None

    mmod: Token | None = None
    if allow_method_mods:
      mmod = self.token('static', 'const')

    body: Node | None
    if self.token(';') is not None:
      body = None
    else:
      body = self.collect_compound_statement()

    fndef = SyntaxNode(declarator.loc, 'FunctionDefinition', {
      'declaration_specifiers': dspecs,
      'declarator': declarator,
      'body': body,
    })

    if allow_method_mods:
      fndef.data['method_modifier'] = mmod

    return fndef

  # until terminator `,` `;` and they are not included
  # in the collection, and after calling this
  # function, `self.cur` will be the terminator
  def collect_initializer(
    self,
    terminator: list[str],
    loc: Loc,
    allow_empty: bool = False
  ) -> CompoundNode:
    compound = CompoundNode(loc)
    nest_levels: dict[str, int] = {
      '(': 0, '[': 0, '{': 0
    }

    flip = lambda c: {
      ')': '(', ']': '[', '}': '{'
    }[c]

    is_nested = lambda: \
      nest_levels['('] > 0 or \
      nest_levels['['] > 0 or \
      nest_levels['{'] > 0

    while True:
      if not self.has_token():
        self.unit.report('initializer not closed, did you forget a ";"?', loc)
        break

      if not is_nested() and self.cur.kind in terminator:
        break

      if self.cur.kind in ['(', '[', '{']:
        nest_levels[self.cur.kind] += 1
      elif self.cur.kind in [')', ']', '}']:
        flipped = flip(self.cur.kind)

        if nest_levels[flipped] > 0:
          nest_levels[flipped] -= 1

      compound.tokens.append(self.cur)
      self.skip()

    if not allow_empty and len(compound.tokens) == 0:
      self.unit.report(
        'initializer cannot be empty',
        compound.loc
      )

    return compound

  def declaration(self, dspecs: Node, declarator: Node, allow_bitfield: bool) -> Node | None:
    TERMINATOR: list[str] = [',', ';']
    first: Node | None = None
    bitfield: Token | None = None

    if allow_bitfield and self.token(':') is not None:
      bitfield = self.expect_token('num')

    if (eq := self.token('=')) is not None:
      first = self.collect_initializer(TERMINATOR, eq.loc)

    first_decl = SyntaxNode(declarator.loc, 'Declaration', {
      'declaration_specifiers': dspecs,
      'declarator': declarator,
      'initializer': first,
    })

    if allow_bitfield:
      first_decl.data['bitfield'] = bitfield

    if self.token(';') is not None:
      return first_decl

    decls = MultipleNode(dspecs.loc)
    decls.nodes.append(first_decl)

    while self.token(',') is not None:
      declarator = self.expect_node(
        self.declarator(),
        'in multiple declaration, a declarator (such as a name) is expected after ","'
      )
      initializer: Node | None = None

      if (eq := self.token('=')) is not None:
        initializer = self.collect_initializer(TERMINATOR, eq.loc)

      new_decl = SyntaxNode(declarator.loc, 'Declaration', {
        'declaration_specifiers': dspecs,
        'declarator': declarator,
        'initializer': initializer,
      })

      decls.nodes.append(new_decl)

    # when not new decls are being added
    if len(decls.nodes) == 1:
      self.unit.report(f'did you mean {" ".join(map(repr, TERMINATOR))}?', self.cur.loc)

    return decls

  def collect_sequence_into(
    self,
    fn: Callable[[], Node | None],
    mn: MultipleNode
  ) -> None:
    while (dspec := fn()) is not None:
      mn.nodes.append(dspec)

  def collect_sequence(self, fn: Callable[[], Node | None]) -> MultipleNode:
    mn = MultipleNode(self.cur.loc)
    self.collect_sequence_into(fn, mn)

    return mn

  def storage_class_specifier(self) -> Token | DeclSpecNode | None:
    if (ds := self.token('__declspec')) is not None:
      # we don't need `@recoverable` anyway for this function
      self.expect_token('(')
      name = str(self.expect_token('id').value)
      self.expect_token(')')

      return DeclSpecNode(name, ds.loc)

    return self.token(*CLASS_SPECS)

  def id_should_be_type(self) -> bool:
    '''
    we can also recognize an identifier as a typedef-ed name
    when the current declaration specifiers list follow these rules:
    * the dspecs is empty (then a type is needed)
    * the dspecs only contain qualifiers
    '''

    # is the dspecs list empty?
    if len(self.current_dspecs.nodes) == 0:
      return True

    # otherwise let's check if the
    # dspecs contains an effective type
    # or just qualifiers, such as `volatile`, `const`, 'static' etc..
    name: str = cast(str, self.cur.value)
    QUALS = CLASS_SPECS + FUNCTION_SPECS + TYPE_QUALS

    for t in self.current_dspecs.nodes:
      # `__declspec` is a class specifier just like `extern`
      # but it is a bit more complex as data, so here i avoid
      # it to be interpreted as a type
      if isinstance(t, DeclSpecNode):
        continue

      if not isinstance(t, Token):
        return False

      if t.kind not in QUALS:
        return False

    return True

  def typedef_name(self) -> Token | None:
    '''
    we know when an identifier is a typedef or
    not, in declaration specifiers, because
    the only other accepted identifiers are those
    of the declarator, which is always followed
    by specific tokens, such as `=` for intializers
    or `(` for functions' params list
    '''

    if self.cur.kind not in ['id', 'meta_id']:
      return None

    if not self.has_token(offset=1):
      return None

    if not self.id_should_be_type():
      return None

    '''
    # meta_id are always types in these cases,
    # because a declarator name cannot be a meta_id
    if self.cur.kind == 'id' and self.tok(offset=1).kind in [
      ',', ';', '=', '(', ')'
    ]:
      if not self.id_should_be_type():
        return None
    '''

    return self.identifier_or_meta_id()

  def identifier_or_meta_id(self) -> Token | None:
    return self.token('id', 'meta_id')

  @recoverable
  def struct_or_union_declaration_list_into(
    self,
    body: MultipleNode,
    expect_braces: bool,
    allow_method_mods: bool
  ) -> MultipleNode | None:
    if expect_braces and (opener := self.token('{')) is None:
      return None
    else:
      # this is just for the location,
      # we actually don't need the cur token
      opener = self.cur

    while True:
      if not self.has_token():
        if expect_braces:
          self.unit.report('body not closed', opener.loc)

        break

      if expect_braces and self.token('}') is not None:
        break

      edecl = self.external_declaration(allow_method_mods)

      # we may parse a standalone semicolon
      if isinstance(edecl, PlaceholderNode):
        continue

      body.nodes.append(edecl)

    return body

  @recoverable
  def struct_or_union_declaration_list(
    self,
    expect_braces: bool,
    allow_method_mods: bool
  ) -> MultipleNode | None:
    return self.struct_or_union_declaration_list_into(
      MultipleNode(self.cur.loc),
      expect_braces,
      allow_method_mods,
    )

  @recoverable
  def comma_enumerator(self) -> Node | None:
    if self.token(',') is None:
      return None

    return self.enumerator()

  @recoverable
  def enumerator(self) -> Node | None:
    if (name := self.identifier()) is None:
      return None

    if (eq := self.token('=')) is None:
      return name

    initializer = self.collect_initializer([',', '}'], eq.loc)

    return SyntaxNode(name.loc, 'EnumeratorWithValue', {
      'name': name,
      'initializer': initializer,
    })

  @recoverable
  def enumerator_list(self) -> MultipleNode | None:
    if self.token('{') is None:
      return None

    if (first := self.enumerator()) is None:
      return None

    mn = self.collect_sequence(self.comma_enumerator)
    mn.nodes.insert(0, first)

    # trailing commas are allowed
    self.token(',')
    self.expect_token('}')
    return mn

  @recoverable
  def type_specifier(self) -> Node | None:
    if self.cur.kind == 'meta_id' and self.cur.value == 'builtin_t':
      tag = self.expect_token('meta_id')
      self.expect_token('(')
      name = str(self.expect_token('str').value)
      self.expect_token(')')

      return TypeBuiltinNode(name, tag.loc)

    if self.cur.kind == 'meta_id' and self.cur.value in META_TYPES:
      return self.expect_token('meta_id')

    builtin = self.token(*TYPE_SPECS)

    if builtin is not None:
      return builtin

    '''
    TODO:
      * atomic-type-specifier
    '''

    if (spec_kw := self.token('enum')) is not None:
      is_enum_struct = self.token('struct')
      tname = self.identifier()
      body = self.enumerator_list()

      if tname is None and body is None:
        self.unit.report(
          'expected identifier, enum body or both',
          self.cur.loc
        )

      return SyntaxNode(spec_kw.loc, 'EnumSpecifier', {
        'is_struct': is_enum_struct,
        'name': tname,
        'body': body,
      })

    if (spec_kw := self.token('struct', 'union')) is not None:
      tname = self.identifier()
      body = self.struct_or_union_declaration_list(
        expect_braces=True, allow_method_mods=True
      )

      if tname is None and body is None:
        self.unit.report(
          f'expected identifier, {spec_kw.kind} body or both',
          self.cur.loc
        )

      return SyntaxNode(spec_kw.loc, f'{spec_kw.kind.capitalize()}Specifier', {
        'name': tname,
        'body': body,
      })

    if (tydef_name := self.typedef_name()) is not None:
      if (tmpl := self.template_arguments(tydef_name)) is not None:
        return tmpl

      return tydef_name

    return None

  @recoverable
  def template_arguments(self, typedef_name: Token) -> TypeTemplatedNode | None:
    if self.token('<') is None:
      return None

    # TODO: collect template argument's as tokens
    #       because they could be ambiguous,
    #       compiler can't distinguish `some_t` from `some`
    #       since templates can accept expressions as well

    self.expect_token('>')
    raise NotImplementedError(
      f'TODO: template_arguments -> templated_name: {typedef_name}, loc: {self.cur.loc}'
    )

  def function_specifier(self) -> Token | None:
    return self.token(*FUNCTION_SPECS)

  def type_qualifier(self) -> Token | None:
    return self.token(*TYPE_QUALS)

  @recoverable
  def declaration_specifier(self) -> Node | None:
    if (storage_cls := self.storage_class_specifier()) is not None:
      return storage_cls

    if (ty_spec := self.type_specifier()) is not None:
      return ty_spec

    if (ty_qual := self.type_qualifier()) is not None:
      return ty_qual

    if (fn_spec := self.function_specifier()) is not None:
      return fn_spec

    '''
    TODO:
      * alignment-specifier
      ? __attribute__
    '''

    return None

  @recoverable
  def declaration_specifiers(self) -> MultipleNode | None:
    # saving the old one shouldn't be
    # necessary
    old, self.current_dspecs = self.current_dspecs, MultipleNode(self.cur.loc)

    self.collect_sequence_into(
      self.declaration_specifier,
      self.current_dspecs
    )

    dspecs, self.current_dspecs = self.current_dspecs, old

    if len(dspecs.nodes) == 0:
      return None

    return dspecs

  @recoverable
  def type_qualifier_list(self) -> Node:
    return self.collect_sequence(self.type_qualifier)

  @recoverable
  def pointer(self) -> Node | None:
    if (p := self.token('*')) is None:
      return None

    return SyntaxNode(p.loc, 'Pointer', {
      'type_qualifier_list': self.type_qualifier_list(),
      'pointer': self.pointer()
    })

  @recoverable
  def direct_abstract_declarator(self) -> Node | None:
    dad: Node | None = None

    if (dad := self.parameter_list_declarator(dad)) is not None:
      pass # just to keep lines cleaner, they are really messy here
    elif (opener := self.token('(')) is not None:
      if (dad := self.abstract_declarator(opener.loc)) is None:
        dad = SyntaxNode(opener.loc, 'EmptyParameterListAbstractDeclarator', {})

      self.expect_token(')')
    else:
      dad = self.array_declarator(dad, midfix='Abstract')

    if dad is None:
      return None

    while self.has_token() and self.cur.kind in ['(', '[']:
      loc: Loc = self.cur.loc

      if (new_dd := self.parameter_list_declarator(dad)) is not None:
        dd = new_dd
      elif (new_dd := self.array_declarator(dad)) is not None:
        dd = new_dd
      else:
        break

    return dad

  @recoverable
  def abstract_declarator(self, loc: Loc) -> Node | None:
    if (pointer := self.pointer()) is None:
      return self.direct_abstract_declarator()

    dad = self.direct_abstract_declarator()

    return SyntaxNode(loc, 'AbstractDeclarator', {
      'pointer': pointer,
      'direct_abstract_declarator': dad,
    })

  @recoverable
  def parameter_declaration(self) -> Node | None:
    if (dspecs := self.declaration_specifiers()) is None:
      return None

    if (declarator := self.declarator()) is None:
      declarator = self.abstract_declarator(dspecs.loc)

    loc = declarator.loc if declarator is not None else dspecs.loc

    return SyntaxNode(loc, 'ParameterDeclaration', {
      'declaration_specifiers': dspecs,
      'declarator': declarator,
    })

  @recoverable
  def parameter_list(self) -> tuple[Node, Node | None] | None:
    def parse_pdecl() -> Node | None:
      if self.token(',') is None:
        return None

      return self.parameter_declaration()

    if (first := self.parameter_declaration()) is None:
      return None

    plist = self.collect_sequence(parse_pdecl)
    plist.nodes.insert(0, first)

    if len(plist.nodes) == 0:
      return None

    return plist, self.token('...')

  @recoverable
  def direct_declarator(self) -> Node | None:
    dd: Node | None = self.identifier()

    if dd is None and self.token('(') is not None:
      dd = self.declarator()
      self.expect_token(')')

    if dd is None:
      return None

    '''
    TODO:
      ? direct-declarator '(' identifier-list ')'
    '''

    while self.has_token() and self.cur.kind in ['(', '[']:
      loc: Loc = self.cur.loc

      if (new_dd := self.parameter_list_declarator(dd)) is not None:
        dd = new_dd
      elif (new_dd := self.array_declarator(dd)) is not None:
        dd = new_dd
      else:
        break

    return dd

  @recoverable
  def array_declarator(self, dd: Node | None, midfix: str = '') -> Node | None:
    if (opener := self.token('[')) is None:
      return None

    if \
      (initializer := self.collect_initializer([']'], opener.loc, allow_empty=True)) is None:
        return None

    self.expect_token(']')

    return SyntaxNode(opener.loc, f'Array{midfix}Declarator', {
      'declarator': dd,
      'size_initializer': initializer
    })

  @recoverable
  def parameter_list_declarator(self, dd: Node | None) -> Node | None:
    if (opener := self.token('(')) is None:
      return None

    if self.token(')') is not None:
      plist = (MultipleNode(opener.loc), None)
    elif (plist := self.parameter_list()) is not None:
      self.expect_token(')')
    else:
      return None

    return SyntaxNode(opener.loc, 'ParameterListDeclarator', {
      'declarator': dd,
      'parameter_list': plist[0],
      'ellipsis': plist[1]
    })

  @recoverable
  def declarator(self) -> Node | None:
    pointer = self.pointer()
    direct_declarator = self.direct_declarator()

    if direct_declarator is None:
      return None

    # this is useful to make the tree cleaner
    if pointer is None:
      return direct_declarator

    return SyntaxNode(direct_declarator.loc, 'Declarator', {
      'pointer': pointer,
      'direct_declarator': direct_declarator
    })

  def parse_use_feature(self, loc: Loc) -> UseFeatureDirective:
    d = UseFeatureDirective(loc)
    d.features.append(self.expect_token('id'))

    while self.has_token() and self.token(',') is not None:
      d.features.append(
        self.expect_token('id')
      )

    if self.cur.kind == '{':
      d.body = self.struct_or_union_declaration_list(
        expect_braces=True, allow_method_mods=False
      )
    else:
      self.expect_token(';')

    return d

  def parse_import_details(self, loc: Loc) -> tuple[str, Token, Loc]:
    if (ident := self.token('id')) is not None:
      if self.token('(') is not None:
        to_import = self.expect_token('str')
        self.expect_token(')')
        return (str(ident.value), to_import, loc)

      return ('pkg', ident, loc)

    if (path := self.token('str')) is not None:
      return ('local', path, loc)

    self.raise_malformed_import(loc)

  def parse_aliased_import(self, alias: Token, loc: Loc) -> AliasedImportDirective:
    details: tuple[str, Token, Loc]
    if self.token('=') is not None:
      details = self.parse_import_details(loc)
    else:
      details = ('pkg', alias, loc)

    self.expect_token(';')
    return AliasedImportDirective(alias, *details)

  def parse_full_import(self, loc: Loc) -> FullImportDirective:
    self.expect_token('=')
    details = self.parse_import_details(loc)
    self.expect_token(';')

    return FullImportDirective(*details)

  def raise_malformed_import(self, loc: Loc) -> NoReturn:
    self.unit.report('import directive is malformed', loc)
    raise ParsingError()

  def parse_name_of_partial_import(self) -> tuple[Token, Token]:
    alias = self.expect_token('id')

    if self.token('=') is not None:
      to_import = self.expect_token('id')
    else:
      to_import = alias

    return (alias, to_import)

  def parse_partial_import(self, loc: Loc) -> PartialImportDirective:
    if self.token('{') is None:
      self.raise_malformed_import(loc)

    names: list[tuple[Token, Token]] = [
      self.parse_name_of_partial_import()
    ]

    while self.token(','):
      names.append(
        self.parse_name_of_partial_import()
      )

    self.expect_token('}')
    self.expect_token('=')
    details = self.parse_import_details(loc)
    self.expect_token(';')

    return PartialImportDirective(names, *details)

  def parse_import(self, loc: Loc) -> GenericImportDirective:
    if (alias_token := self.token('id')) is not None:
      return self.parse_aliased_import(alias_token, loc)

    if self.token('*') is not None:
      return self.parse_full_import(loc)

    return self.parse_partial_import(loc)

  def parse_test(self, loc: Loc) -> TestDirective:
    desc = str(self.expect_token('str').value)
    body = self.expect_node(
      self.collect_compound_statement(),
      'test directive always wants a body'
    )

    return TestDirective(
      desc,
      cast(CompoundNode, body),
      loc
    )

  def parse_meta_directive(self) -> Node:
    mdir: Token = self.token('meta_id') # type: ignore[assignment]

    match mdir.value:
      case 'use_feature':
        return self.parse_use_feature(mdir.loc)

      case 'test':
        return self.parse_test(mdir.loc)

      case 'import':
        return self.parse_import(mdir.loc)

      case _:
        raise UnreachableError()

  def external_declaration(self, is_inside_structunion: bool) -> Node:
    '''
    TODO:
      * _Static_assert
    '''

    # parsing meta directives, such as `use_feature`
    if \
      not is_inside_structunion and \
        self.cur.kind == 'meta_id' and \
          self.cur.value in META_DIRECTIVES:
      return self.parse_meta_directive()

    if self.token(';') is not None:
      return PlaceholderNode()

    dspecs = self.expect_node(
      self.declaration_specifiers(),
      'top level members must start with a declaration specifier (such as a type)'
    )

    # to avoid getting stuck on a token
    # in loop
    if dspecs is None or isinstance(dspecs, PoisonedNode):
      loc = self.cur.loc
      self.skip()
      return PoisonedNode(loc)

    if self.token(';') is not None:
      return SyntaxNode(
        dspecs.loc,
        'EmptyDeclaration',
        {'declaration_specifiers': dspecs}
      )

    declarator = self.expect_node(
      self.declarator(),
      'top level members must have a declarator (such as a name)'
    )

    if (node := self.function_definition(dspecs, declarator, is_inside_structunion)) is None:
      node = cast(SyntaxNode, self.expect_node(
        self.declaration(dspecs, declarator, is_inside_structunion),
        'top level members must be either function definition or declaration'
      ))

    return node

  def expect_node(
    self,
    node: Node | None,
    error_message: str
  ) -> Node:
    if node is not None:
      return node

    self.unit.report(
      f'{error_message}, matched token "{self.cur.kind}"',
      self.cur.loc
    )
    raise ParsingError()