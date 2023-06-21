class Loc:
  def __init__(self, filepath: str, line: int, col: int) -> None:
    self.filepath: str = filepath
    self.line: int = line
    self.col: int = col

  def __repr__(self) -> str:
    return f'{self.filepath}:{self.line}:{self.col}'

class Node:
  def __init__(self, loc: Loc) -> None:
    self.loc: Loc = loc

class Token(Node):
  def __init__(
    self,
    kind: str,
    value: object,
    loc: Loc
  ) -> None:
    super().__init__(loc)

    self.kind: str = kind
    self.value: object = value

  def __repr__(self) -> str:
    return f'{self.loc}: Token({repr(self.kind)}, {repr(self.value)})'

class RootNode(Node):
  def __init__(self, nodes: list[Node], loc: Loc) -> None:
    super().__init__(loc)

    self.nodes: list[Node] = nodes

class PoisonedNode(Node):
  pass

class ZeroOrOneNode(Node):
  def __init__(self, node: Node | None) -> None:
    if node is not None:
      super().__init__(node.loc)
    
    self.node: Node | None = node

class CompoundStatementNode(Node):
  def __init__(self, loc: Loc) -> None:
    super().__init__(loc)
    self.tokens: list[Token] = []

class OneOrMoreNode(Node):
  def __init__(self, loc: Loc) -> None:
    super().__init__(loc)
    self.list: list[Node] = []

class SyntaxNode(Node):
  '''
  represents a whole sytax node,
  such as "FunctionDefinition" or a "Declaration"
  '''

  def __init__(self, syntax_name: str, loc: Loc) -> None:
    super().__init__(loc)
    
    self.syntax_name: str = syntax_name
    self.pattern: dict[str, Node] = {}