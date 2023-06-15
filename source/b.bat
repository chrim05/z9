@if not exist "build" mkdir build
@call gcc -Wall -Wextra -Werror -DDEBUG main.c compilation_tower.c misc.c -o build\cxc

@rem remember to add `-g0 -O3 -UDEBUG` for release builds
@rem @call gcc -Wall -Wextra -Werror -g0 -O3 -UDEBUG main.c compilation_tower.c misc.c -o build\cxc