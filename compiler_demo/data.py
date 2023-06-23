from typing import Callable, Any

INDENT_STEP: str = '  '
indent_level: int = 0

def indent() -> str:
  return INDENT_STEP * indent_level

def idented_line() -> str:
  return f'\n{indent()}'

def indented_repr(
  collection: list[Any],
  repr_fn: Callable[[Any], str],
  edges: tuple[str, str]
) -> str:
  global indent_level
  indent_level += 2

  s: str = ''
  sep: str = ','

  for i, e in enumerate(collection):
    if i == len(collection) - 1:
      sep = ''

    s += f'{idented_line()}{repr_fn(e)}{sep}'

  indent_level -= 2
  return f'{edges[0]}{s}{idented_line()}{edges[1]}'

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

  def __repr__(self) -> str:
    raise NotImplementedError(type(self).__name__)

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
    return f'{self.kind}({repr(self.value)})'

class PoisonedNode(Node):
  def __repr__(self) -> str:
    return f'PoisonedNode'

class CompoundNode(Node):
  def __init__(self, loc: Loc) -> None:
    super().__init__(loc)
    self.tokens: list[Token] = []

  def __repr__(self) -> str:
    if len(self.tokens) <= 2:
      return f'CompoundNode{repr(self.tokens)}'

    body = indented_repr(
      self.tokens, repr, ('[', ']')
    )

    return f'CompoundNode{body}'

class SyntaxNode(Node):
  '''
  represents a whole sytax node,
  such as "FunctionDefinition" or a "Declaration"
  '''

  def __init__(
    self,
    loc: Loc,
    syntax_name: str,
    data: dict[str, Node | None],
  ) -> None:
    super().__init__(loc)
    
    self.syntax_name: str = syntax_name
    self.data: dict[str, Node | None] = data

  def __repr__(self) -> str:
    if len(self.data) == 1:
      k = next(iter(self.data))
      v = self.data[k]

      return f'{self.syntax_name}({k}: {v})'

    body = indented_repr(
      list(self.data.items()),
      lambda i: f'{i[0]}: {repr(i[1])}',
      ("(", ")")
    )

    return f'{self.syntax_name}{body}'

class MultipleNode(Node):
  def __init__(self, loc: Loc) -> None:
    super().__init__(loc)

    self.nodes: list[Node] = []

  def __repr__(self) -> str:
    if len(self.nodes) <= 1:
      return f'MultipleNode{repr(self.nodes)}'

    body = indented_repr(
      self.nodes, repr, ('[', ']')
    )

    return f'MultipleNode{body}'

class PlaceholderNode(Node):
  def __init__(self) -> None:
    pass

class UseFeatureDirective(Node):
  def __init__(self, loc: Loc) -> None:
    super().__init__(loc)

    self.features: list[Token] = []
    self.body: MultipleNode | None = None

  def __repr__(self) -> str:
    if self.body is None:
      return f'UseFeatureDirective{repr(self.features)}'

    features = indented_repr(
      self.features, repr, ("[", "]")
    )
    features = f'features: {features}'

    body = repr(self.body)
    body = f'body: {body}'

    return \
      f'UseFeatureDirective({idented_line()}{features},{idented_line()}{body})'

class TypeBuiltinNode(Node):
  def __init__(self, name: str, loc: Loc) -> None:
    super().__init__(loc)

    self.name: str = name

  def __repr__(self) -> str:
    return f'TypeBuiltinNode({repr(self.name)})'

class TypeTemplatedNode(Node):
  def __init__(self, loc: Loc) -> None:
    super().__init__(loc)

class DeclSpecNode(Node):
  def __init__(self, name: str, loc: Loc) -> None:
    super().__init__(loc)

    self.name: str = name

  def __repr__(self) -> str:
    return f'DeclSpecNode({repr(self.name)})'