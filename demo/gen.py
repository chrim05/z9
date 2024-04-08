from data import *
from typing import cast

def get_declaration_name(node: Node | None) -> Token | None:
  if isinstance(node, Token) and node.kind == 'id':
    return node

  if not isinstance(node, SyntaxNode):
    return None

  match node.syntax_name:
    case 'Declarator':
      return get_declaration_name(node['direct_declarator'])

    case                       \
      'ArrayDeclarator'      | \
      'Declaration'          | \
      'ParameterDeclaration' | \
      'FunctionDefinition'   | \
      'ParameterListDeclarator':
        return get_declaration_name(node['declarator'])

    case _:
      return None

class Gen:
  '''
  the idea of this module is to generate a middle represetation
  parsing the bodies into stack based bytecode
  for each global scope lazy node parsed by dparse

  c code is generated simultaneously to comptime execution
  '''

  def __init__(self, unit) -> None:
    from unit import TranslationUnit

    self.unit: TranslationUnit = unit
    self.lparsers: list['LParse'] = []

  # current local parser
  @property
  def lparser(self) -> 'LParse':
    return self.lparsers[-1]

  @property
  def root(self) -> MultipleNode:
    return self.unit.root

  @property
  def tab(self) -> SymTable:
    return self.unit.tab

  def predeclare_top_level(self, node: Node) -> None:
    if node.is_empty_decl():
      raise NotImplementedError()

    assert isinstance(node, SyntaxNode)

    key = {
      'Declaration': 'initializer',
      'FunctionDefinition': 'body'
    }[node.syntax_name]
    
    name = cast(Token, get_declaration_name(node))
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

        self.lparsers.append(LParse(
          self,
          # cast(FnTyp, typ),
          node
        ))

        self.lparser.process()

        fn = self.lparsers.pop()
        decl_name_token = cast(Token, get_declaration_name(node))
        name = cast(str, decl_name_token.value)
        return FnSymbol(name, decl_name_token.loc, fn)

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

class CBody:
  def __init__(self) -> None:
    self.c: str = ''
    self.vstack: list[Val] = []
    self.locals: dict[str, Typ] = []
  
  def load(self, v: Val) -> None:
    self.vstack.append(v)
  
  def load_name(self, name: str) -> None:
    pass

# TODO: execute at comptime certain operations
class LParse:
  '''
  content parser also from:
  https://github.com/katef/kgt/blob/main/examples/c99-grammar.iso-ebnf
  '''

  def __init__(self, gen: Gen, node: SyntaxNode) -> None:
    self.gen: Gen = gen
    # self.typ: FnTyp = typ
    self.node: SyntaxNode = node
    
    self.tokens: list[Token]
    self.index: int = 0
    self.cbody: CBody = CBody()

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
      raise CompilationException(
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
      # TODO: gen code for these operators
      self.pg_unary_expression()
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
      raise CompilationException(
        'expected primary expression', self.cur.loc
      )

    p = self.bck

    match p.kind:
      case 'num':
        constant = cast(int, self.bck.value)
        self.cbody.load(Val(
          LitIntTyp(),
          constant,
          p.loc
        ))

      case 'id':
        self.cbody.load_name(cast(str, p.value))

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
      self.cbody(op.kind, op.loc)

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

    # TODO: while self.token('?')
    
    # the top of the chain
    self.pg_binary_expression(*or_)

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
      self.cbody.ret_void(l)
      return
    
    self.pg_expression()
    self.cbody.ret(l)
    self.expect_token(';')

  def jump_statement(self) -> bool:
    if self.token('return'):
      self.pg_return(self.bck.loc)
      return True

    # TODO: add other jump statements
    return False

  def pg_rounded_expression(self) -> None:
    self.expect_token('(')
    self.pg_expression()
    self.expect_token(')')

  def pg_statement(self) -> None:
    self.expect_matching(
      self.statement(),
      'expected statement'
    )

  def pg_if(self, loc: Loc) -> None:
    self.pg_rounded_expression()
    jumpi = self.cbody.jump_if_false(loc)

    self.pg_statement()

    if self.token('else'):
      quiti = self.cbody.jump(loc)
      jumpi.ex = self.cbody.cursor
      
      self.pg_statement()
      quiti.ex = self.cbody.cursor
    else:
      jumpi.ex = self.cbody.cursor

  def selection_statement(self) -> bool:
    if self.token('if'):
      self.pg_if(self.bck.loc)
      return True
    
    return False

  def statement(self) -> bool:
    if self.jump_statement():
      return True
    
    if self.selection_statement():
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

    raise CompilationException(
      f'{error_message}, matched token "{self.cur.kind}"',
      self.cur.loc
    )

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