from data import *
from subprocess import run as runprocess
from sys import argv

class TranslationUnit:
  def __init__(self, filepath: str) -> None:
    from tempfile import NamedTemporaryFile
    from rich.console import Console

    self.console = Console(emoji=False)

    preprocessed_filepath: str = NamedTemporaryFile().name
    clang_cpp = runprocess(
      f'clang-cpp.exe -std=c99 -nostdinc -Iinclude "{filepath}" -o "{preprocessed_filepath}"'
    ).returncode

    if clang_cpp != 0:
      raise CompilationException('clang preprocessor failed', None)

    self.filepath: str = filepath
    self.source: str = open(preprocessed_filepath, 'r').read()
    self.cmod: CModule = CModule(filepath + '.c')

  def compile(self) -> None:
    open(self.cmod.filepath, 'w').write(repr(self.cmod.c))

  def fix_message(self, message: str) -> str:
    return message.replace('[', '\\[')

  def print_error(self, message: str, loc: Loc | None) -> None:
    message = self.fix_message(message)
    prefix = str(loc) if loc else 'error'

    self.console.print(
      f'[b][red]{prefix}[/red][/b]: {message}'
    )

  def lex(self) -> None:
    from lex import Lexer
    from data import Token

    self.tokens: list[Token] = []
    l = Lexer(self)

    while l.has_char():
      token: Token | None = l.next_token()

      if token is None:
        break

      self.tokens.append(token)

  def gen(self) -> None:
    from gen import Gen
    from data import SymTable

    g = Gen(self)
    self.tab: SymTable = SymTable()

    g.gen_whole_unit()

  def dparse(self) -> None:
    from dparse import DParse
    from data import MultipleNode

    if len(self.tokens) == 0:
      self.root: MultipleNode = MultipleNode(Loc(self.filepath, 1, 1))
      return

    d = DParse(self)
    self.root = MultipleNode(d.cur.loc)

    # the top level scope behaves the same as a
    # struct's or union's body, except that functions
    # cannot have method modifiers (such as `t f() const|static {}`)
    d.struct_or_union_declaration_list_into(
      self.root, expect_braces=False, allow_method_mods=False
    )

  def dump_root(self) -> None:
    self.console.print('\n-- ROOT --\n')

    self.console.print(
      self.fix_message(repr(self.root))
    )
  
  def dump_cmod(self) -> None:
    self.console.print('\n-- CMOD --\n')

    self.console.print(
      self.fix_message(self.cmod.c)
    )

  def dump_tab(self) -> None:
    self.console.print('\n-- TAB --\n')

    self.console.print(
      self.fix_message(repr(self.tab))
    )