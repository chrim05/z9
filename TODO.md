TODO:
  * implement templates (instantiation, declaration)
  * implement `__attribute__`
  * `@"interpolated string {10}"` should be evaluated to
    array of strings, and then possibly merged into a single string;
    this should imply the change of calls to `print[ln]` to `print[ln]f`
    which would take as parameter an array of string;
    the array should be stack allocated and should have a comtime
    known size

  * find a better syntax for `@link_with` when the input is a package's name
  * design a pythonic `for` compression in initializer list