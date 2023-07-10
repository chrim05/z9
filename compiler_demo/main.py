from unit import TranslationUnit
from sys  import argv

if len(argv) == 1 or argv[1].startswith('-'):
  f = 'samples/simple.z9'
else:
  f = argv[1]

t = TranslationUnit(f)

t.lex()

t.dparse()
# t.dump_root()

t.mrgen()
t.dump_tab()

print('\n-------\n')

t.mrchip()
t.dump_llmod()

t.print_diagnostic()
t.compile()