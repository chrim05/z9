from data import *
from json import dumps

class TranslationUnit:
  def __init__(self, filepath: str) -> None:
    from subprocess import run
    from tempfile import NamedTemporaryFile
    from rich.console import Console

    self.console = Console()

    preprocessed_filepath: str = NamedTemporaryFile().name
    self.clang_cpp = run(
      f'clang-cpp.exe -std=c99 -nostdinc -Iinclude {filepath} -o {preprocessed_filepath}'
    ).returncode

    if self.clang_cpp != 0:
      return

    self.filepath: str = filepath
    self.source: str = open(preprocessed_filepath, 'r').read()

    self.errors: list[tuple[str, Loc]] = []
    self.warnings: list[tuple[str, Loc]] = []

  def fix_message(self, m: str) -> str:
    return m.replace('[', '\[')

  def print_diagnostic(self) -> None:
    if self.clang_cpp != 0:
      return

    dprint = lambda m, l, color: \
      self.console.print(
        f'[b][{color}]{l}[/{color}][/b]: [b]{self.fix_message(m)}[/b]'
      )

    for message, loc in self.errors:
      dprint(message, loc, 'red')

    for message, loc in self.warnings:
      dprint(message, loc, 'yellow')

  def report(self, message: str, loc: Loc) -> None:
    self.errors.append((message, loc))

  def warn(self, message: str, loc: Loc) -> None:
    self.warnings.append((message, loc))

  def lex(self) -> None:
    from cx_lexer import Lexer
    from data import Token

    if self.clang_cpp != 0:
      return

    self.tokens: list[Token] = []
    l = Lexer(self)

    while l.has_char():
      token: Token | None = l.next_token()

      if token is None:
        break

      self.tokens.append(token)

  def dparse(self) -> None:
    from cx_dparser import DParser
    from data import MultipleNode

    if self.clang_cpp != 0:
      return

    if len(self.tokens) == 0:
      self.root: MultipleNode = MultipleNode(Loc(self.filepath, 1, 1))
      return

    # the top level scope behaves the same as a
    # struct's or union's body, except that functions
    # cannot have method modifiers (such as `t f() const|static {}`)
    self.root = DParser(self).struct_or_union_declaration_list(
      expect_braces=False, allow_method_mods=False
    )

  def dump_root(self) -> None:
    if self.clang_cpp != 0:
      return

    self.console.print(
      self.fix_message(repr(self.root))
    )