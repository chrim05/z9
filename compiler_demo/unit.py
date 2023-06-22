from data import *
from json import dumps

class TranslationUnit:
  def __init__(self, filepath: str) -> None:
    from subprocess import run
    from tempfile import NamedTemporaryFile

    preprocessed_filepath: str = NamedTemporaryFile().name
    x = run(f'cpp.exe -std=c99 {filepath} {preprocessed_filepath}')

    self.filepath: str = filepath
    self.source: str = open(preprocessed_filepath, 'r').read()

    self.errors: list[tuple[str, Loc]] = []
    self.warnings: list[tuple[str, Loc]] = []

  def print_diagnostic(self) -> None:
    from rich.console import Console
    console = Console()

    fix_message = lambda m: m.replace('[', '\[')

    for message, loc in self.errors:
      console.print(f'[red]{loc}[/]: {fix_message(message)}')

    for message, loc in self.warnings:
      console.print(f'[yellow]{loc}[/]: {fix_message(message)}')

  def report(self, message: str, loc: Loc) -> None:
    self.errors.append((message, loc))

  def warn(self, message: str, loc: Loc) -> None:
    self.warnings.append((message, loc))

  def lex(self) -> None:
    from cx_lexer import Lexer
    from data import Token

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

    if len(self.tokens) == 0:
      self.root: MultipleNode = MultipleNode(Loc(self.filepath, 1, 1))
      return

    # the top level scope behaves the same as a
    # struct's or union's body
    self.root = DParser(self).struct_or_union_declaration_list(
      expect_braces=False, allow_method_mods=False
    )