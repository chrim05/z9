# the official repository for the cx compiler
(please use `.cx` extension when writing c code that can only be compiled by cxc)

cxc compiles c99, but supports new features as well.

several new ideas introduced are inherited from more mature languages, such as the circle lang, zig and some old private compiler project of mine

this is actually a personal experiment, i wanted to start since i think having new languages with amazing features makes sense to a certain extent;

i wanted to make a game without engine; i chose zig (i love it), but it wasn't mature enough
(and yes it can import c libraries, but the whole thing worked yes and no, mainly because of the lack of zig library maintainers).

circle lang is an incredible project, i don't care if it's closed source, but it was even more complex than cpp itself; however the problem (which was a problem of mine, no one seemed to complain about that) was that circle anyway did not support stuff like unordered declarations, which FOR ME is a feature way more important to have than all that amazing meta programming stuff.

i personally find it very hard to code having to pay attention where you declare some struct or spend time to move declarations around the file to make the compiler happy (probably just a problem of mine).

addionally, this introduces the need of header files; header files are a terrible idea, the real problem is not that you have to write them (in addition to source code), but they also heavily slow down compilation times.

i can't write a full cpp compiler.

but maybe i can write a minimal c99 compiler and extend it(?) i'll try my best.

**features i want in the compiler (see `examples/`):**
* 90% compatible with existing code
* tags, `@name` can be a new way to do something, for example `@include_once "..."` or `@execute_at_compile_time(...)` or `@defer` etc..
* members don't need to be forward declared:
```c
// int add(int a, int b); -> this is not necessary anymore, neither with typedefs

int main() { return add(1, 2); }
int add(int a, int b) { return a + b; }
```
* kind operator overloading
* generics
* foreach (with a lot of extensions, for example `for @zip(auto e1 : iterable1, auto e2 : iterable2) {}` or `for @idx(auto i, auto e : iterable) {}`)
* auto will be used for type inference instead
* const doesn't need the type specifier (type inference)
* const can work as constexpr (called meta value) when the initializer is constexpr (a meta value)
* compile time code execution, maybe jitted
* compile time code execution can work as small build script with simple cases (for example raylib)
