from unit import TranslationUnit
from sys  import argv
from data import *

if len(argv) == 1 or argv[1].startswith('-'):
  f = 'samples/simple.c0'
else:
  f = argv[1]

t = TranslationUnit(f)

try:
  t.lex()

  t.dparse()
  t.dump_root()

  t.gen()
  t.dump_tab()

  # t.chip()
  # t.dump_cmod()

  # t.compile()
except CompilationException as e:
  t.print_error(e.message, e.loc)