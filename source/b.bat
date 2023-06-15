@if not exist "build" mkdir build
@rem remember to add `-g0 -O3 -UDEBUG` for release builds
@call gcc -Wall -Wextra -Werror -DDEBUG main.c compilation_tower.c misc.c -o build\cxc