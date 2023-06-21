from data import *
from typing import Callable, cast
from json import dumps

'''
TOFIX:
  * currently i check for a lot of stuff
    and return None if they are None too,
    but this makes no sense when the called
    function moved throught tokens, an idiomatic
    solution should be to push and pop indices,
    but this makes the code bloated and a lot of checks
    are not even necessary, i can just write expecting functions
    instead of checking ones
'''

def recoverable(func):
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
  '''

  def __init__(self, unit) -> None:
    from unit import TranslationUnit
    self.unit: TranslationUnit = unit
    self.branches: list[int] = [0]

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

  def todo(self, message: str = '') -> Node | None:
    # self.unit.warn(f'TODO: {message}', self.cur.loc)
    # return None
    raise NotImplementedError(message)

  def expect_token(self, kind: str) -> Token:
    token: Token | None = self.token(kind)

    if token is None:
      self.unit.report(
        f'expected token "{kind}", matched "{self.cur.kind}"',
        self.cur.loc
      )
      return self.cur

    return token

  def collect_compound_statement(self) -> CompoundStatementNode:
    opener: Token = self.expect_token('{')
    compound = CompoundStatementNode(opener.loc)
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
  def function_definition(self, loc: Loc) -> SyntaxNode | None:
    return SyntaxNode(loc, 'FunctionDefinition', {
      'compound_statement': self.expect_node(
        self.collect_compound_statement(),
        'function definition wants a compund statement (its body)'
      )
    })

  def declaration(self, loc: Loc) -> SyntaxNode | None:
    return self.todo()

  def collect_sequence(self, fn: Callable[[], Node | None]) -> MultipleNode:
    mn = MultipleNode(self.cur.loc)

    while (dspec := fn()) is not None:
      mn.nodes.append(dspec)

    return mn

  def storage_class_specifier(self) -> Token | None:
    return self.token(
      'typedef', 'extern', 'static',
      '_Thread_local', 'auto', 'register'
    )

  def typedef_name(self) -> Token | None:
    '''
    we know when an identifier is a typedef or
    not, in declaration specifiers, because
    the only other accepted identifiers are those
    of the declarator, which is always followed
    by specific tokens, such as `=` for intializers
    or `(` for functions' params list
    '''

    if self.cur.kind != 'id':
      return None

    if not self.has_token(offset=1):
      return None

    if self.tok(offset=1).kind in [
      ',', ';', '=', '(', ')'
    ]:
      return None

    return self.identifier()

  @recoverable
  def type_specifier(self) -> Node | None:
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

    if (tydef_name := self.typedef_name()) is not None:
      return tydef_name

    return None

  def function_specifier(self) -> Token | None:
    return self.token(
      'inline', '_Noreturn'
    )

  def type_qualifier(self) -> Token | None:
    return self.token(
      'const', 'restrict',
      'volatile', '_Atomic'
    )

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
    '''

    return None

  @recoverable
  def declaration_specifiers(self) -> MultipleNode | None:
    dspecs = self.collect_sequence(self.declaration_specifier)

    if len(dspecs.nodes) == 0:
      return None

    return dspecs

  @recoverable
  def type_qualifier_list(self) -> Node | None:
    ty_quals = self.collect_sequence(self.type_qualifier)

    if len(ty_quals.nodes) == 0:
      return None

    return ty_quals

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

  def external_declaration(self) -> Node:
    dspecs = self.expect_node(
      self.declaration_specifiers(),
      'top level members must start with a declaration specifier (such as a type)'
    )

    declarator = self.expect_node(
      self.declarator(),
      'top level members must have a declarator (such as a name)'
    )

    if (node := self.function_definition(declarator.loc)) is None:
      node = cast(SyntaxNode, self.expect_node(
        self.declaration(declarator.loc),
        'top level members must be either function definition or declaration'
      ))

    node.data['declaration_specifiers'] = dspecs
    node.data['declarator'] = declarator
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