TODO:
  * implement templates (instantiation, declaration) in the parser
  * implement `__attribute__`
  * `@"interpolated string {10}"` should be evaluated to
    array of strings, and then possibly merged into a single string;
    this should imply the change of calls to `print[ln]` to `print[ln]f`
    which would take as parameter an array of string;
    the array should be stack allocated and should have a comtime
    known size
  * design a pythonic `for` compression in initializer list
  * design `bucket_t`
  * think about how to implement `@multi_t` on user-defined types
  * think about how to implement `@multi_t` on interfaces,
    so that all the tags can be grouped
  * think about how to implement interfaces in the most efficient
    way (use references such as casey muratori's video about clean code);
    is it via vtable (it also requires memory overhead)? or is a jump table better
    (it also provides inline)?
  * `@unreachable`
  * `const x = expr;` is ambiguous in top level scope, because `x` is parsed as a type,
      to solve this ambiguity maybe check whether the next token is `=` and parse it as
      name