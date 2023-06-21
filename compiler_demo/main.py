from unit import TranslationUnit

t = TranslationUnit('simple.cx')
t.lex()
t.dparse()

print(*t.tokens, sep='\n', end='\n\n')

t.print_diagnostic()