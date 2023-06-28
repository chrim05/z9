from typing import Callable, Any, cast

META_TYPES = [
  'this_t', 'info_t',
  'builtin_t'
]

META_DIRECTIVES = [
  'use_feature', 'test',
  'import',
]

META_TAGS = META_DIRECTIVES + META_TYPES + [
  'this'
]

INDENT_DEPTH: int = 2
INDENT_STEP: str = ' ' * INDENT_DEPTH

indent_level: int = 0

def indent() -> str:
  return INDENT_STEP * indent_level

def indented_line() -> str:
  return f'\n{indent()}'

def indented_repr(
  collection: list[Any],
  repr_fn: Callable[[Any], str],
  edges: tuple[str, str]
) -> str:
  global indent_level
  indent_level += INDENT_DEPTH

  s: str = ''
  sep: str = ','

  for i, e in enumerate(collection):
    if i == len(collection) - 1:
      sep = ''

    s += f'{indented_line()}{repr_fn(e)}{sep}'

  indent_level -= INDENT_DEPTH
  return f'{edges[0]}{s}{indented_line()}{edges[1]}'

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

  def is_empty_decl(self) -> bool:
    return isinstance(self, SyntaxNode) and self.syntax_name == 'EmptyDeclaration'

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
    if self.kind == self.value:
      return repr(self.value)

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

  def __getitem__(self, key: Any) -> Node | None:
    assert isinstance(key, str)

    return self.data[key]

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

    global indent_level
    indent_level += INDENT_DEPTH

    il = indented_line()
    features = indented_repr(
      self.features, repr, ("[", "]")
    )
    features = f'{il}features: {features}'

    body = f'{il}body: {repr(self.body)}'

    indent_level -= INDENT_DEPTH

    return \
      f'UseFeatureDirective({features},{body}{indented_line()})'

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

class GenericImportDirective(Node):
  '''
  this is only used internally for code reused, (for inheritance purpose);
  never allocated by the parser
  '''

  def __init__(self, kind: str, to_import: Token, loc: Loc) -> None:
    super().__init__(loc)

    # manual(std, url) auto(pkg, local)
    self.kind: str = kind
    self.to_import: Token = to_import

class AliasedImportDirective(GenericImportDirective):
  '''
  @import some = ...;
  '''

  def __init__(self, alias: Token, kind: str, to_import: Token, loc: Loc) -> None:
    super().__init__(kind, to_import, loc)

    self.alias: Token = alias

  def __repr__(self) -> str:
    return \
      f'AliasedImportDirective(alias: {self.alias}, ' \
      f'kind: {repr(self.kind)}, to_import: {self.to_import})'

class FullImportDirective(GenericImportDirective):
  '''
  @import * = ...;
  '''

  def __repr__(self) -> str:
    return \
      f'FullImportDirective(kind: {repr(self.kind)}, to_import: {self.to_import})'

class PartialImportDirective(GenericImportDirective):
  '''
  @import {...} = ...;
  '''

  def __init__(
    self,
    names: list[tuple[Token, Token]],

    kind: str, to_import: Token, loc: Loc
  ) -> None:
    super().__init__(kind, to_import, loc)

    self.names: list[tuple[Token, Token]] = names

  def __repr__(self) -> str:
    return \
      f'PartialImportDirective(names: {self.names}, ' \
      f'kind: {repr(self.kind)}, to_import: {self.to_import})'

class TestDirective(Node):
  def __init__(self, desc: str, body: CompoundNode, loc: Loc) -> None:
    super().__init__(loc)

    self.desc: str = desc
    self.body: CompoundNode = body

  def __repr__(self) -> str:
    global indent_level
    indent_level += INDENT_DEPTH

    il = indented_line()
    desc = f'{il}desc: {repr(self.desc)}'
    body = f'{il}body: {repr(self.body)}'

    indent_level -= INDENT_DEPTH

    return \
      f'TestDirective({desc},{body}{indented_line()})'

class ParsingError(Exception):
  pass

class UnreachableError(Exception):
  pass

class Typ:
  def __init__(
    self,
    is_const: bool = False
  ) -> None:
    self.is_const: bool = is_const

  def quals(self) -> list[str]:
    r = []

    if self.is_const:
      r.append('const')

    return r

  def are_quals_eq(self, other: 'Typ') -> bool:
    return (
      self.is_const == other.is_const
    )

  def is_eq(self, other) -> bool:
    raise NotImplementedError(type(self).__name__)

  def __eq__(self, other: object) -> bool:
    if isinstance(self, PoisonedTyp) or isinstance(other, PoisonedTyp):
      return True

    if type(self) != type(other):
      return False

    if not self.are_quals_eq(cast(Typ, other)):
      return False

    return self.is_eq(other)

  def __repr__(self) -> str:
    raise NotImplementedError(type(self).__name__)

class IntTyp(Typ):
  def __init__(self, kind: str, is_signed: bool) -> None:
    super().__init__()

    self.kind: str = kind
    self.is_signed: bool = is_signed

  def is_eq(self, other: 'IntTyp') -> bool:
    return (
      self.kind == other.kind and
      self.is_signed == other.is_signed
    )

  def __repr__(self) -> str:
    if self.kind == 'longlong':
      return 'long long'

    quals = self.quals()
    quals.insert(0, self.kind)

    return ' '.join(quals)

class VoidTyp(Typ):
  def __init__(self) -> None:
    super().__init__()

  def is_eq(self, other: 'VoidTyp') -> bool:
    return True

  def __repr__(self) -> str:
    quals = self.quals()
    quals.insert(0, 'void')

    return ' '.join(quals)

class PointerTyp(Typ):
  def __init__(self, pointee: Typ) -> None:
    super().__init__()

    self.pointee: Typ = pointee

  def is_eq(self, other: 'PointerTyp') -> bool:
    return self.pointee == other.pointee

  def __repr__(self) -> str:
    quals = self.quals()
    quals.insert(0, repr(self.pointee))

    '''
    if len(quals) == 1:
      return f'{quals[0]}*'

    return (
      quals[0] + ' (' +
        ' '.join(quals[1:]) +
      '*)'
    )
    '''

    return ' '.join(quals) + '*'

class FnTyp(Typ):
  def __init__(
    self,
    ret: Typ,
    params: list[Typ],
    pnames: list[Token | None]
  ) -> None:
    super().__init__()

    self.ret: Typ = ret
    self.params: list[Typ] = params
    self.pnames: list[Token | None] = pnames

  def is_eq(self, other: 'FnTyp') -> bool:
    return (
      self.ret == other.ret and
      self.params == other.params
    )

  def __repr__(self) -> str:
    quals = self.quals()

    params = ', '.join(map(repr, self.params))
    quals.insert(0, f'{self.ret} ({params})')

    return '@fn ' + ' '.join(quals)

class ArrayTyp(Typ):
  def __init__(self, pointee: Typ, size: 'Val') -> None:
    super().__init__(pointee.is_const)

    self.pointee: Typ = pointee
    self.size: Val = size

  def is_eq(self, other: 'ArrayTyp') -> bool:
    return (
      self.pointee == other.pointee and
      self.size == other.size
    )

  def __repr__(self) -> str:
    return f'{self.pointee}[{self.size}]'

class PoisonedTyp(Typ):
  def __init__(self) -> None:
    super().__init__()

  def __repr__(self) -> str:
    return '?'

class Val:
  def __init__(self, typ: Typ, value: object) -> None:
    self.typ: Typ = typ
    self.value: object = value

  def __eq__(self, other: object) -> bool:
    if not isinstance(other, Val):
      return False

    raise NotImplementedError(type(self).__name__)

  def __repr__(self) -> str:
    if self.value is None:
      return '@undef'

    return repr(self.value)

POISONED_VAL = Val(PoisonedTyp(), None)

class Symbol:
  def __init__(self, typ: Typ) -> None:
    self.typ: Typ = typ

  def __repr__(self) -> str:
    raise NotImplementedError(type(self).__name__)

class ExternFnSymbol(Symbol):
  def __repr__(self) -> str:
    return f'ExternFnSymbol({self.typ})'

class FnSymbol(Symbol):
  def __init__(self, fn) -> None:
    super().__init__(fn.typ)

    from z9_mrgen import FnMrGen
    self.fn: FnMrGen = fn

  def __repr__(self) -> str:
    return f'FnSymbol({self.fn.code})'

class SemaTable:
  def __init__(self, unit) -> None:
    from unit import TranslationUnit

    self.unit: TranslationUnit = unit
    self.members: dict[str, Symbol | tuple[Node, bool]] = {}
    self.heading_decls: dict[str, list[Node]] = {}

  def is_weak(self, name: str) -> bool:
    return cast(tuple, self.members[name])[1]

  def save_weak_decl(self, name: str, decl: Node) -> None:
    if name not in self.heading_decls:
      self.heading_decls[name] = []

    self.heading_decls[name].append(decl)

  def declare(
    self,
    name: str,
    value: Node,
    is_weak: bool,
    loc: Loc
  ) -> None:
    if name in self.members:
      # we don't want the week declaration
      # to overwrite the complete one
      if is_weak:
        self.save_weak_decl(name, value)
        return

      if not self.is_weak(name):
        self.unit.report(f'name "{name}" already declared', loc)
        return

      self.save_weak_decl(
        name,
        cast(tuple[Node, bool], self.members[name])[0]
      )

    self.members[name] = (value, is_weak)

  def __repr__(self) -> str:
    return '\n\n'.join(
      f'{repr(name)} -> {m}' for name, m in self.members.items()
    )

from enum import IntEnum

class MidOpcode(IntEnum):
  RET_VOID = 0
  RET      = 1

class MidInstr:
  def __init__(self, op: MidOpcode, typ: Typ) -> None:
    self.op: MidOpcode = op
    self.typ: Typ  = typ

  def __repr__(self) -> str:
    return \
      f'MidInstr(op: {self.op.name}, typ: {self.typ})'

class MidRepr:
  def __init__(self) -> None:
    self.instructions: list[MidInstr] = []

  def emit(self, op: MidOpcode, t: Typ = VoidTyp()) -> None:
    self.instructions.append(MidInstr(
      op, t
    ))

  def ret_void(self) -> None:
    self.emit(MidOpcode.RET_VOID)

  def ret(self, t: Typ) -> None:
    self.emit(MidOpcode.RET, t)

  def __repr__(self) -> str:
    return '\n  ' + f'\n  '.join(
      map(repr, self.instructions)
    ) + '\n'