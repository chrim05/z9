from unit import TranslationUnit
from json import dumps
from sys  import argv

f = 'samples/simple.z9' if len(argv) == 1 else argv[1]
t = TranslationUnit(f)
t.lex()
t.dparse()

t.dump_root()
t.print_diagnostic()