from data import *
from typing import cast

def is_word_char(c: str) -> bool:
  return c.isalnum() or c == '_'

KEYWORDS: list[str] = [
  'auto', 'break', 'case', 'char',
  'const', 'continue', 'default', 'do',
  'double', 'else', 'enum', 'extern',
  'float', 'for', 'goto', 'if',
  'int', 'long', 'register', 'return',
  'short', 'signed', 'sizeof', 'static',
  'struct', 'switch', 'typedef', 'union',
  'unsigned', 'void', 'volatile',
  'while', '_Alignas', '_Alignof',
  '_Atomic', '_Bool', '_Complex',
  '_Generic', '_Imaginary', '_Noreturn',
  '_Static_assert', '_Thread_local',
  'inline', 'restrict', '_Cdecl'
]

PUNCTUATION: list[str] = [
  '=', ',', ';', ':', '(', ')', '{', '}', '[', ']',
  '<', '>', '.', '?', '!', '+', '-', '*', '/', '%',
  '&', '|', '^', '~',
]

DOUBLE_PUNCTUATION: list[str] = [
  '==', '!=', '>=', '<=', '&&', '||',
  '+=', '-=', '*=', '/=', '%=', '&=',
  '|=', '^=', '<<', '>>', '++', '--',
]

TRIPLE_PUNCTUATION: list[str] = [
  '...', '<<=', '>>=',
]

class Lexer:
  def __init__(self, unit) -> None:
    from unit import TranslationUnit
    self.unit: TranslationUnit = unit
    self.index: int = 0
    self.index_of_linestart: int = 0
    self.line: int = 0

  @property
  def cur(self) -> str:
    return self.char(0)

  @property
  def loc(self) -> Loc:
    return Loc(
      self.unit.filepath,
      self.line + 1,
      self.calculate_col() + 1
    )

  def calculate_col(self) -> int:
    return self.index - self.index_of_linestart

  def char(self, offset: int) -> str:
    return self.unit.source[self.index + offset]

  def has_char(self, offset: int = 0) -> bool:
    return self.index + offset < len(self.unit.source)

  def eat_cpp(self) -> None:
    # skipping `# `
    self.skip()

    self.eat_white()
    new_line: Token = self.collect_word_token(self.loc)

    if new_line.kind != 'num':
      return

    self.eat_white()
    new_path: Token = self.collect_stringed_token(self.loc)

    self.line = cast(int, new_line.value) - 2
    self.unit.filepath = cast(str, new_path.value)

    while self.has_char() and self.cur != '\n':
      self.skip()

    # so that `\n` is still processed by `eat_white`
    self.skip(count=-1)

  def eat_white(self) -> None:
    while self.has_char():
      match self.cur:
        case '#':
          self.eat_cpp()

        case '\t' | ' ' | '\r':
          pass

        case '\n':
          self.line += 1
          self.index_of_linestart = self.index + 1

        case _:
          return

      self.skip()

  def skip(self, count: int = 1) -> None:
    self.index += count

  def collect_word_token(self, loc: Loc) -> Token:
    value: str = ''

    while self.has_char() and is_word_char(self.cur):
      value += self.cur
      self.skip()

    if value[0].isdigit():
      return Token('num', eval(value), loc)

    if value in KEYWORDS:
      return Token(value, value, loc)

    return Token('id', value, loc)

  def collect_punctuation_token(self, loc: Loc) -> Token:
    if self.has_char(offset=2):
      triple: str = self.cur + self.char(1) + self.char(2)

      if triple in TRIPLE_PUNCTUATION:
        self.skip(count=3)
        return Token(triple, triple, loc)

    if self.has_char(offset=1):
      double: str = self.cur + self.char(offset=1)

      if double in DOUBLE_PUNCTUATION:
        self.skip(count=2)
        return Token(double, double, loc)

    single: str = self.cur
    if single not in PUNCTUATION:
      self.unit.report('bad token', loc)

    self.skip()
    return Token(single, single, loc)

  def escape_char(self, c: str, loc: Loc) -> str:
    try:
      return {
        '0': '\0',
        'n': '\n',
        't': '\t',
        'r': '\r',
        'b': '\b',
        'f': '\f',
        'v': '\v',
        'a': '\a',
        '\\': '\\',
        '\'': '\'',
        '\"': '\"',
      }[c]
    except IndexError:
      self.unit.report('bad escaped char', loc)
      return c

  def collect_stringed_token(self, loc: Loc) -> Token:
    apex: str = self.cur
    self.skip()

    value: str = ''

    while self.has_char() and self.cur != apex:
      c: str = self.cur

      if c == '\\':
        self.skip()
        c = self.escape_char(c, loc)

      value += c
      self.skip()

    if not self.has_char():
      self.unit.report('string not closed', loc)
    else:
      # skipping also the closing `"`
      self.skip()

    return Token(
      'str' if apex == '"' else 'chr',
      value,
      loc
    )

  def collect_meta_id(self, loc: Loc) -> Token:
    # skipping `@`
    self.skip()
    
    value: Token = self.collect_word_token(loc)
    value.kind = 'meta_id'

    return value

  def next_token(self) -> Token | None:
    self.eat_white()

    if not self.has_char():
      return None

    token: Token

    if is_word_char(self.cur):
      token = self.collect_word_token(self.loc)
    elif self.cur in ["'", '"']:
      token = self.collect_stringed_token(self.loc)
    elif self.cur == '@':
      token = self.collect_meta_id(self.loc)
    else:
      token = self.collect_punctuation_token(self.loc)

    return token