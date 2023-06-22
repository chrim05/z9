from data import *
from typing import Callable, cast
from json import dumps

META_DIRECTIVES = [
  'use_feature',
]

CLASS_SPECS = (
  'typedef', 'extern', 'static',
  '_Thread_local', 'auto', 'register'
)

FUNCTION_SPECS = ('inline', '_Noreturn')

TYPE_QUALS = (
  'const', 'restrict',
  'volatile', '_Atomic'
)

def recoverable(func):
  '''
  this is a decorator for parsing methods of DParser;
  it becomes useful to easily restore/recover
  previous branch index when the parsing function
  fails, basically when returns `None`, then we know
  that it may moved advanced the index to next tokens,
  but if it failed, we need to come back to the original tokens index
  that there was before calling the parsing function
  '''

  def wrapper(*args, **kwargs):
    this = args[0]

    this.clone_branch()
    result = func(*args, **kwargs)

    if result is None:
      this.discard_branch()
    else:
      this.merge_branch()

    return result

  return wrapper

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
    self.branches: list[int] = [0]
    # i just assign it with a placeholder, because it will be always
    # overwritten
    self.current_dspecs: MultipleNode = MultipleNode(self.cur.loc)

  @property
  def index(self) -> int:
    return self.branches[-1]

  @index.setter
  def index(self, value: int) -> None:
    self.branches[-1] = value

  @property
  def cur(self) -> Token:
    return self.tok(0)

  def tok(self, offset: int) -> Token:
    if not self.has_token(offset):
      return Token('eof', '\0', self.unit.tokens[-1].loc)

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

  def clone_branch(self) -> None:
    self.branches.append(self.index)

  def discard_branch(self) -> None:
    self.branches.pop()

  def merge_branch(self) -> None:
    self.index = self.branches.pop()

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

  def log(self, message: str) -> None:
    print(f'LOG(cur: {self.cur}): {message}')

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

    direct_decl = declarator.data['direct_declarator']

    if \
      not isinstance(direct_decl, SyntaxNode) or \
        direct_decl.syntax_name != 'ParameterListDeclarator':
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
  def collect_initializer(self, loc: Loc) -> CompoundNode:
    compound = CompoundNode(loc)
    nest_levels: dict[str, int] = {
      '(': 0, '[': 0, '{': 0
    }

    flip = lambda c: {
      ')': '(', ']': '[', '}': '{'
    }[c]

    while True:
      if not self.has_token():
        self.unit.report('initializer not closed, did you forget a ";"?', loc)
        break

      if self.cur.kind in [',', ';']:
        break

      if self.cur.kind in ['(', '[', '{']:
        nest_levels[self.cur.kind] += 1
      elif self.cur.kind in [')', ']', '}']:
        flipped = flip(self.cur.kind)

        if nest_levels[flipped] > 0:
          nest_levels[flipped] -= 1

      compound.tokens.append(self.cur)
      self.skip()

    return compound

  def declaration(self, dspecs: Node, declarator: Node) -> Node | None:
    first: Node | None = None

    if (eq := self.token('=')) is not None:
      first = self.collect_initializer(eq.loc)

    first_decl = SyntaxNode(declarator.loc, 'Declaration', {
      'declaration_specifiers': dspecs,
      'declarator': declarator,
      'initializer': first,
    })

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
        initializer = self.collect_initializer(eq.loc)

      new_decl = SyntaxNode(declarator.loc, 'Declaration', {
        'declaration_specifiers': dspecs,
        'declarator': declarator,
        'initializer': initializer,
      })

      decls.nodes.append(new_decl)

    # when not new decls are being added
    if len(decls.nodes) == 1:
      self.unit.report('did you mean ";" or ","?', self.cur.loc)

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

  def storage_class_specifier(self) -> Token | None:
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

    # meta_id are always types in these cases,
    # because a declarator name cannot be a meta_id
    if self.cur.kind == 'id' and self.tok(offset=1).kind in [
      ',', ';', '=', '(', ')'
    ]:
      if not self.id_should_be_type():
        return None

    return self.identifier_or_meta_id()

  def identifier_or_meta_id(self) -> Token | None:
    return self.token('id', 'meta_id')

  @recoverable
  def struct_or_union_declaration_list(
    self,
    expect_braces: bool,
    allow_method_mods: bool
  ) -> MultipleNode | None:
    if expect_braces and (opener := self.token('{')) is None:
      return None
    else:
      # this is just for the location,
      # we actually don't need the cur token
      opener = self.cur

    body = MultipleNode(opener.loc)

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
  def type_specifier(self) -> Node | None:
    if self.cur.kind == 'meta_id' and self.cur.value == 'i':
      tag = self.expect_token('meta_id')
      self.expect_token('(')
      size = self.expect_token('num').value
      self.expect_token(')')

      return TypeSizedIntNode(
        # just for error recovery
        size if isinstance(size, int) else 32,
        tag.loc
      )

    builtin = self.token(
      'void', 'char', 'short',
      'int', 'long', 'float',
      'double', 'signed',
      'unsigned', '_Bool',
      '_Complex', '_Imaginary'
    )

    if builtin is not None:
      return builtin

    '''
    TODO:
      * atomic-type-specifier
      * struct-or-union-specifier
      * enum-specifier
    '''

    if (spec_kw := self.token('struct', 'union')) is not None:
      name = self.identifier()
      body = self.struct_or_union_declaration_list(
        expect_braces=True, allow_method_mods=True
      )

      return SyntaxNode(spec_kw.loc, f'{spec_kw.kind.capitalize()}Specifier', {
        'name': name,
        'body': body,
      })

    if (tydef_name := self.typedef_name()) is not None:
      if (tmpl := self.template_arguments(tydef_name)) is not None:
        return tmpl

      return tydef_name

    return None

  def template_arguments(self, typedef_name: Token) -> TypeTemplatedNode | None:
    if self.token('(') is None:
      return None

    # TODO: collect template argument's as tokens
    #       because they could be ambiguous,
    #       compiler can't distinguish `some_t` from `some`
    #       since templates can accept expressions as well

    self.expect_token(')')
    raise NotImplementedError('TODO')

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
  def parameter_declaration(self) -> Node | None:
    if (dspecs := self.declaration_specifiers()) is None:
      return None

    declarator = self.declarator()
    loc = declarator.loc if declarator is not None else dspecs.loc

    '''
    TODO:
      * abstract-declarator
    '''

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
      ? direct-declarator '[', ['*'] ']'
      * direct-declarator '[' 'static' [type-qualifier-list] assignment-expression ']'
      * direct-declarator '[' type-qualifier-list ['*'] ']'
      * direct-declarator '[' type-qualifier-list ['static'] assignment-expression ']'
      * direct-declarator '[' assignment-expression ']'
      ? direct-declarator '(' identifier-list ')'
    '''

    if (opener := self.token('(')) is not None:
      if self.token(')') is not None:
        plist = (MultipleNode(opener.loc), None)
      elif (plist := self.parameter_list()) is not None:
        self.expect_token(')')
      else:
        return None

      dd = SyntaxNode(opener.loc, 'ParameterListDeclarator', {
        'declarator': dd,
        'parameter_list': plist[0],
        'ellipsis': plist[1]
      })

    return dd

  @recoverable
  def declarator(self) -> Node | None:
    pointer = self.pointer()
    direct_declarator = self.direct_declarator()

    if direct_declarator is None:
      return None

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

  def parse_meta_directive(self) -> Node:
    mdir: Token = self.token('meta_id') # type: ignore[assignment]

    match mdir.value:
      case 'use_feature':
        return self.parse_use_feature(mdir.loc)

      case _:
        return PoisonedNode(mdir.loc) # unreachable

  def external_declaration(self, allow_method_mods: bool) -> Node:
    '''
    TODO:
      * _Static_assert
    '''

    # parsing meta directives, such as `use_feature`
    if \
      not allow_method_mods and \
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
      self.skip()
      return PlaceholderNode()

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

    # to avoid getting stuck on a token
    # in loop
    if declarator is None or isinstance(declarator, PoisonedNode):
      self.skip()
      return PlaceholderNode()

    if (node := self.function_definition(dspecs, declarator, allow_method_mods)) is None:
      node = cast(SyntaxNode, self.expect_node(
        self.declaration(dspecs, declarator),
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

    self.unit.report(f'unexpected token "{self.cur.kind}", {error_message}', self.cur.loc)
    return PoisonedNode(self.cur.loc)