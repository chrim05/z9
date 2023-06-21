from unit import TranslationUnit
from json import dumps

t = TranslationUnit('simple.cx')
t.lex()
t.dparse()

print('\n--------\n')

#print(*t.tokens, sep='\n', end='\n\n')
print(dumps(t.root.as_serializable(), indent=4))

t.print_diagnostic()