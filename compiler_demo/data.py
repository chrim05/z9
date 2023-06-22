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

  def as_serializable(self) -> object:
    raise NotImplementedError(type(self).__name__)

def optional_as_serializable(optional: Node | None) -> object:
  if optional is None:
    return None

  return optional.as_serializable()


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

  def as_serializable(self) -> object:
    return {
      '@class': type(self).__name__,
      'kind': self.kind,
      'value': self.value
    }

  def __repr__(self) -> str:
    return f'{self.loc}: Token({repr(self.kind)}, {repr(self.value)})'

class PoisonedNode(Node):
  def as_serializable(self) -> object:
    return {
      '@class': type(self).__name__
    }

class CompoundNode(Node):
  def __init__(self, loc: Loc) -> None:
    super().__init__(loc)
    self.tokens: list[Token] = []

  def as_serializable(self) -> object:
    return {
      '@class': type(self).__name__,
      'tokens': [
        t.as_serializable() for t in self.tokens
      ]
    }

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

  def as_serializable(self) -> object:
    return {
      '@class': type(self).__name__,
      'syntax_name': self.syntax_name,
      'data': {
        k: v.as_serializable() if v else None
          for k, v in self.data.items()
      }
    }

class MultipleNode(Node):
  def __init__(self, loc: Loc) -> None:
    super().__init__(loc)

    self.nodes: list[Node] = []

  '''
  def as_serializable(self) -> object:
    return {
      '@class': type(self).__name__,
      'nodes': [
        n.as_serializable() for n in self.nodes
      ]
    }
  '''

  def as_serializable(self) -> object:
    return [
      n.as_serializable() for n in self.nodes
    ]

class PlaceholderNode(Node):
  def __init__(self) -> None:
    pass

class UseFeatureDirective(Node):
  def __init__(self, loc: Loc) -> None:
    super().__init__(loc)

    self.features: list[Token] = []
    self.body: MultipleNode | None = None

  def as_serializable(self) -> object:
    return {
      '@class': type(self).__name__,
      'features': [
        f.as_serializable() for f in self.features
      ],
      'body': optional_as_serializable(self.body)
    }

class TypeSizedIntNode(Node):
  def __init__(self, size: int, loc: Loc) -> None:
    super().__init__(loc)

    self.size:int = size

  def as_serializable(self) -> object:
    return {
      '@class': type(self).__name__,
      'size': self.size
    }

class TypeTemplatedNode(Node):
  def __init__(self, loc: Loc) -> None:
    super().__init__(loc)

  def as_serializable(self) -> object:
    return {
      '@class': type(self).__name__,
    }