// based on
// https://github.com/rui314/chibicc/blob/main/include/stdbool.h

#ifndef _STDBOOL_H
#define _STDBOOL_H 1

  // #define bool                          _Bool
  // #define true                          1
  // #define false                         0
  #define __bool_true_false_are_defined 1

  typedef bool _Bool;
  const bool true  = 1;
  const bool false = 0;

#endif