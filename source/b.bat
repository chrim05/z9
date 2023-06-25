@if not exist "build" mkdir build
@call gcc -Wall -Wextra -Werror -m64 -DDEBUG main.c compilation_tower.c misc.c -o build\z9

@rem remember to add `-O3 -UDEBUG` for release builds
@rem @call gcc -Wall -Wextra -Werror -m64 -O3 -UDEBUG main.c compilation_tower.c misc.c -o build\z9