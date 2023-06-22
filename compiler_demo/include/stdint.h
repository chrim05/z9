// based on
// https://en.wikibooks.org/wiki/C_Programming/stdint.h

#ifndef _STDINT_H
#define _STDINT_H 1

  // i use builtin meta tags
  // to express these types, because
  // it's way simpler than using
  // `long long long super long extra long ...` and so on
  // for windows and `short short extra large bim bum bam ...`
  // for unix for expressing the same type

  typedef signed   @i(8)  int8_t;
  typedef unsigned @i(8)  uint8_t;

  typedef signed   @i(16) int16_t;
  typedef unsigned @i(16) uint16_t;

  typedef signed   @i(32) int32_t;
  typedef unsigned @i(32) uint32_t;

  typedef signed   @i(64) int64_t;
  typedef unsigned @i(64) uint64_t;

  // please don't use these macros,
  // use `intN_t.[max | min]` instead
  // since macros are not supported in modules

  #define INT8_MAX   (127)
  #define UINT8_MAX  (255)

  #define INT16_MAX  (32767)
  #define UINT16_MAX (65535)

  #define INT32_MAX  (2147483647)
  #define UINT32_MAX (4294967295)

  #define INT64_MAX  (9223372036854775807)
  #define UINT64_MAX (18446744073709551615)

  #define INT8_MIN   (-128)
  #define INT16_MIN  (-32768)
  #define INT32_MIN  (-2147483648)
  #define INT64_MIN  (-9223372036854775808)

  // TODO:
  //  * int_leastN_t
  //  * uint_leastN_t
  //  * INT_LEAST_N_MAX
  //  * INT_LEAST_N_MIN
  //  * UINT_LEAST_N_MAX
  //
  //  * int_fastN_t
  //  * uint_fastN_t
  //  * INT_FAST_N_MAX
  //  * INT_FAST_N_MIN
  //  * UINT_FAST_N_MAX
  //
  //  * intptr_t

#endif