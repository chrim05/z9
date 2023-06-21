from data import *
from typing import Callable

class DParser:
  '''
  Lazy parser for declarations, from:
  https://github.com/katef/kgt/blob/main/examples/c99-grammar.iso-ebnf
  '''

  def __init__(self, unit) -> None:
    from unit import TranslationUnit
    self.unit: TranslationUnit = unit

    self.indexes: list[int] = [0]

  @property
  def index(self) -> int:
    return self.indexes[-1]

  @index.setter
  def index(self, value: int) -> None:
    self.indexes[-1] = value

  @property
  def cur(self) -> Token:
    return self.tok(0)

  def tok(self, offset: int) -> Token:
    return self.unit.tokens[self.index + offset]

  def has_token(self) -> bool:
    return self.index < len(self.unit.tokens)

  def skip(self, count: int = 1):
    self.index += count

  # an empty list is never returned,
  # instead `None` is returned
  def one_or_more(
    self,
    node_parser_fn: Callable[[], Node | None]
  ) -> OneOrMoreNode | None:
    node = OneOrMoreNode(self.cur.loc)

    while self.has_token():
      parsed: Node | None = node_parser_fn()

      if parsed is None:
        break

      node.list.append(parsed)

    if len(node.list) == 0:
      return None

    return node

  def token(self, *kinds: str) -> Token | None:
    tok: Token = self.cur

    for kind in kinds:
      if kind == tok.kind:
        self.skip()
        return tok

    return None

  def _storage_class_specififer(self) -> Node | None:
    '''
    storage-class-specifier =
      'typedef' |
      'extern' |
      'static' |
      '_Thread_local' |
      'auto' |
      'register';
    '''

    return self.token(
      'typedef', 'extern', 'static',
      '_Thread_local', 'auto', 'register'
    )

  def storage_class_specififer(self) -> Node | None:
    return self.recoverable(
      self._storage_class_specififer
    )

  def _type_name(self) -> Node | None:
    '''
    type-name =
      specifier-qualifier-list,
      [abstract-declarator];
    '''

    return self.all_of(
      'TypeName',
      {
        'specifier_qualifier_list': self.specifier_qualifier_list,
        'abstract_declarator': lambda: self.zero_or_one(self.abstract_declarator),
      }
    )

  def type_name(self) -> Node | None:
    return self.recoverable(
      self._type_name
    )

  def _atomic_type_specifier(self) -> Node | None:
    '''
    atomic-type-specifier =
      '_Atomic',
      '(',
      type-name,
      ')';
    '''

    return self.all_of(
      'AtomicTypeSpecifier',
      {
        '1': lambda: self.token('_Atomic'),
        '2': lambda: self.token('('),
        'type_name': self.type_name,
        '3': lambda: self.token(')')
      }
    )

  def atomic_type_specifier(self) -> Node | None:
    return self.recoverable(
      self._atomic_type_specifier
    )

  def struct_or_union(self) -> Token | None:
    '''
    struct-or-union =
      'struct' |
      'union';
    '''

    return self.token('struct', 'union')

  def _struct_or_union_specifier(self) -> Node | None:
    '''
    struct-or-union-specifier =
      struct-or-union, '{', struct-declaration-list, '}' |
      struct-or-union, identifier, ['{', struct-declaration-list, '}'];
    '''

    return self.todo('_struct_or_union_specifier')

  def struct_or_union_specifier(self) -> Node | None:
    return self.recoverable(
      self._struct_or_union_specifier
    )

  def _enumeration_constant(self) -> Node | None:
    '''
    enumeration-constant =
      identifier;
    '''

    return self.identifier()

  def enumeration_constant(self) -> Node | None:
    return self.recoverable(
      self._enumeration_constant
    )

  def _enumeration_expression(self) -> Node | None:
    return self.todo('_enumeration_expression')

  def enumeration_expression(self) -> Node | None:
    return self.recoverable(
      self._enumeration_expression
    )

  def _enumerator(self) -> Node | None:
    '''
    enumerator =
      enumeration-constant,
      ['=', constant-expression];
    '''

    return self.all_of(
      'Enumerator',
      {
        'enumeration_constant': self.enumeration_constant,
        'enumeration_expression': lambda: self.zero_or_one(
          lambda: self.all_of(
            'EnumeratorValue',
            {
              '0': lambda: self.token('='),
              'value': self.enumeration_expression,
            }
          )
        ),
      }
    )

  def enumerator(self) -> Node | None:
    return self.recoverable(
      self._enumerator
    )

  def _enumerator_list(self) -> Node | None:
    '''
    enumerator-list =
      enumerator,
      {',', enumerator};
    '''

    return self.all_of(
      'EnumeratorList',
      {
        'first': self.enumerator,
        'others': lambda: self.one_or_more(self.enumerator)
      }
    )

  def enumerator_list(self) -> Node | None:
    return self.recoverable(
      self._enumerator_list
    )

  def _enum_specifier(self) -> Node | None:
    '''
    enum-specifier =
      'enum', '{', enumerator-list, [','], '}' |
      'enum', identifier, ['{', enumerator-list, [','], '}'];
    '''

    return self.one_of(
      lambda: self.all_of(
        'EnumSpecifierWithoutName',
        {
          '1': lambda: self.token('enum'),
          '2': lambda: self.token('{'),
          'enumerator_list': self.enumerator_list,
          '3': lambda: self.zero_or_one(lambda: self.token(',')),
          '4': lambda: self.token('}'),
        }
      ),
      lambda: self.all_of(
        'EnumSpecifierWithName',
        {
          '1': lambda: self.token('enum'),
          'name': self.identifier,
          '2': lambda: self.token('{'),
          'enumerator_list': self.enumerator_list,
          '3': lambda: self.zero_or_one(lambda: self.token(',')),
          '4': lambda: self.token('}'),
        }
      )
    )

  def enum_specifier(self) -> Node | None:
    return self.recoverable(
      self._enum_specifier
    )

  def _typedef_name(self) -> Node | None:
    '''
    typedef-name =
      identifier;
    '''

    return self.identifier

  def typedef_name(self) -> Node | None:
    return self.recoverable(
      self._typedef_name
    )

  def _type_specifier(self) -> Node | None:
    '''
    type-specifier =
      'void' |
      'char' |
      'short' |
      'int' |
      'long' |
      'float' |
      'double' |
      'signed' |
      'unsigned' |
      '_Bool' |
      '_Complex' |
      '_Imaginary' |
      atomic-type-specifier |
      struct-or-union-specifier |
      enum-specifier |
      typedef-name;
    '''

    return self.one_of(
      lambda: self.token(
        'void', 'char', 'short', 'int',
        'long', 'float', 'double',
        'signed', 'unsigned', '_Bool',
        '_Complex', '_Imaginary'
      ),
      self.atomic_type_specifier,
      self.struct_or_union_specifier,
      self.enum_specifier,
      self.typedef_name
    )

  def type_specifier(self) -> Node | None:
    return self.recoverable(
      self._type_specifier
    )

  def _function_specifier(self) -> Node | None:
    '''
    function-specifier =
      'inline' |
      '_Noreturn';
    '''

    return self.token(
      'inline', '_Noreturn'
    )

  def function_specifier(self) -> Node | None:
    return self.recoverable(
      self._function_specifier
    )

  def _conditional_expression(self) -> Node | None:
    return self.todo('_conditional_expression')

  def conditional_expression(self) -> Node | None:
    return self.recoverable(
      self._conditional_expression
    )

  def _constant_expression(self) -> Node | None:
    '''
    constant-expression =
      conditional-expression;
    '''

    return self.conditional_expression()

  def constant_expression(self) -> Node | None:
    return self.recoverable(
      self._constant_expression
    )

  def _alignment_specifier(self) -> Node | None:
    '''
    alignment-specifier =
      '_Alignas', '(', type-name, ')' |
      '_Alignas', '(', constant-expression, ')';
    '''

    return self.one_of(
      lambda: self.all_of(
        'AlignmentSpecifierWithTypeName',
        {
          '1': lambda: self.token('_Alignas'),
          '2': lambda: self.token('('),
          'type_name': self.type_name,
          '3': lambda: self.token(')')
        }
      ),
      lambda: self.all_of(
        'AlignmentSpecifierWithConst',
        {
          '1': lambda: self.token('_Alignas'),
          '2': lambda: self.token('('),
          'constant_expression': self.constant_expression,
          '3': lambda: self.token(')')
        }
      )
    )

  def alignment_specifier(self) -> Node | None:
    return self.recoverable(
      self._alignment_specifier
    )

  def _declaration_specifier(self) -> Node | None:
    '''
    declaration-specifier =
      storage-class-specifier |
      type-specifier |
      type-qualifier |
      function-specifier |
      alignment-specifier;
    '''

    return self.one_of(
      self.storage_class_specififer,
      self.type_specifier,
      self.type_qualifier,
      self.function_specifier,
      self.alignment_specifier,
    )

  def declaration_specifier(self) -> Node | None:
    return self.recoverable(
      self._declaration_specifier
    )

  def _declaration_specifiers(self) -> Node | None:
    '''
    declaration-specifiers =
      declaration-specifier, {declaration-specifier};
    '''

    return self.one_or_more(
      self.declaration_specifier
    )

  def declaration_specifiers(self) -> Node | None:
    return self.recoverable(
      self._declaration_specifiers
    )

  def push_index(self) -> None:
    self.indexes.append(self.index)

  def pop_index(self) -> None:
    self.indexes.pop()

  def merge_index(self) -> None:
    self.index = self.indexes.pop()

  def zero_or_one(
    self,
    node_parser_fn: Callable[[], Node | None]
  ) -> ZeroOrOneNode:
    if (parsed := node_parser_fn()) is not None:
      return ZeroOrOneNode(parsed)

    return ZeroOrOneNode(None)

  def all_of(
    self,
    syntax_name: str,
    pattern: dict[str, Callable[[], Node | None]]
  ) -> SyntaxNode | None:
    node = SyntaxNode(syntax_name, self.cur.loc)

    for name, fn in pattern.items():
      if (parsed := fn()) is None:
        return None

      if not name.isdigit():
        node.pattern[name] = parsed

    return node

  def identifier(self) -> Token | None:
    return self.token('id')

  def todo(self, message: str) -> Node | None:
    self.unit.warn(f'TODO: {message}', self.cur.loc)
    return None
    # raise NotImplementedError(message)

  def select(self, name: str, syntax: Node | None) -> Node | None:
    if syntax is None:
      return None

    assert isinstance(syntax, SyntaxNode)
    return syntax.pattern[name]

  def _direct_declarator(self) -> Node | None:
    '''
    direct-declarator =
      identifier |
      '(', declarator, ')' |
      direct-declarator, '[', ['*'], ']' |
      direct-declarator, '[', 'static', [type-qualifier-list], assignment-expression, ']' |
      direct-declarator, '[', type-qualifier-list, ['*'], ']' |
      direct-declarator, '[', type-qualifier-list, ['static'], assignment-expression, ']' |
      direct-declarator, '[', assignment-expression, ']' |
      direct-declarator, '(', parameter-type-list, ')' |
      direct-declarator, '(', identifier-list, ')' |
      direct-declarator, '(', ')';
    '''

    print(self.cur)

    return self.one_of(
      self.identifier,

      lambda: self.select('declarator', self.all_of('', {
        '1': lambda: self.token('('),
        'declarator': self.declarator,
        '2': lambda: self.token(')'),
      })),

      lambda: self.all_of(
        'DirectDeclarator',
        {
          'direct_declarator': self.direct_declarator,
          '1': lambda: self.token('['),
          'pointer': lambda: self.token('*'),
          '2': lambda: self.token(']'),
        }
      )
    )

  def direct_declarator(self) -> Node | None:
    return self.recoverable(
      self._direct_declarator
    )

  def _type_qualifier(self) -> Node | None:
    '''
    type-qualifier =
      'const' |
      'restrict' |
      'volatile' |
      '_Atomic';
    '''

    return self.token(
      'const', 'restrict',
      'volatile', '_Atomic'
    )

  def type_qualifier(self) -> Node | None:
    return self.recoverable(
      self._type_qualifier
    )

  def _type_qualifier_list(self) -> Node | None:
    '''
    type-qualifier-list =
      type-qualifier,
      {type-qualifier};
    '''

    return self.one_or_more(
      self.type_qualifier
    )

  def type_qualifier_list(self) -> Node | None:
    return self.recoverable(
      self._type_qualifier_list
    )

  def _pointer(self) -> Node | None:
    '''
    pointer =
      '*',
      [type-qualifier-list],
      [pointer];
    '''

    return self.all_of(
      'Pointer',
      {
        '1': lambda: self.token('*'),
        'type_qualifier_list': lambda: self.zero_or_one(self.type_qualifier_list),
        'pointer': lambda: self.zero_or_one(self.pointer)
      }
    )

  def pointer(self) -> Node | None:
    return self.recoverable(
      self._pointer
    )

  def _declarator(self) -> Node | None:
    '''
    declarator =
      [pointer],
      direct-declarator;
    '''

    return self.all_of(
      'Declarator',
      {
        'pointer': lambda: self.zero_or_one(self.pointer),
        'direct_declarator': self.direct_declarator
      }
    )

  def declarator(self) -> Node | None:
    return self.recoverable(
      self._declarator
    )

  def _declaration_list(self) -> Node | None:
    '''
    declaration-list =
      declaration,
      {declaration};
    '''

    return self.one_or_more(
      self.declaration
    )

  def declaration_list(self) -> Node | None:
    return self.recoverable(
      self._declaration_list
    )

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

      if self.cur.kind == '{':
        nest_level += 1
      elif self.cur.kind == '}' and nest_level == 0:
        break

      compound.tokens.append(self.cur)
      self.skip()

    self.token('}')
    return compound

  def _compound_statement(self) -> Node | None:
    '''
    compound-statement =
      '{',
      {declaration-or-statement},
      '}';
    '''

    if self.cur.kind != '{':
      return None

    return self.collect_compound_statement()

  def compound_statement(self) -> Node | None:
    return self.recoverable(
      self._compound_statement
    )

  def log(self, message: str) -> Node | None:
    print(f'LOG(cur: {self.cur}): {message}')
    return ZeroOrOneNode(None)

  def log_none(self, message: str) -> Node | None:
    self.log(message)
    return None

  def _function_definition(self) -> Node | None:
    '''
    function-definition =
      declaration-specifiers,
      declarator,
      [declaration-list],
      compound-statement;
    '''

    return self.all_of(
      'FunctionDefinition',
      {
        'declaration_specifiers': self.declaration_specifiers,
        'declarator': self.declarator,
        'declaration_list': lambda: self.zero_or_one(self.declaration_list),
        'compound_statement': self.compound_statement,
      }
    )

  def function_definition(self) -> Node | None:
    return self.recoverable(
      self._function_definition
    )

  def _declaration(self) -> Node | None:
    '''
    declaration =
      declaration-specifiers, [init-declarator-list], ';' |
      static-assert-declaration |
      ';';
    '''

    return self.todo('_declaration')

  def declaration(self) -> Node | None:
    return self.recoverable(
      self._declaration
    )

  def one_of(
    self,
    *node_parser_fns: Callable[[], Node | None]
  ) -> Node | None:
    for fn in node_parser_fns:
      if (parsed := fn()) is not None:
        return parsed

    return None

  def external_declaration(self) -> Node:
    '''
    external-declaration =
      function-definition |
      declaration;
    '''

    return self.expect_node(
      lambda: self.one_of(
        self.function_definition,
        self.declaration
      ),
      'expected function definition or declaration'
    )

  def recoverable(
    self,
    node_parser_fn: Callable[[], Node | None]
  ) -> Node | None:
    self.push_index()

    parsed: Node | None = node_parser_fn()

    if parsed is None:
      self.pop_index()
    else:
      self.merge_index()

    return parsed

  def expect_node(
    self,
    node_parser_fn: Callable[[], Node | None],
    error_message: str
  ) -> Node:
    parsed: Node | None = node_parser_fn()

    if parsed is not None:
      return parsed

    self.unit.report(f'unexpected token "{self.cur.kind}", {error_message}', self.cur.loc)
    return PoisonedNode(self.cur.loc)