#ifndef _STDARG_H
#define _STDARG_H 1

  // for nt, but probably not necessary
  #ifndef _VA_LIST_DEFINED
  #define _VA_LIST_DEFINED
  #endif

  #ifndef _VA_LIST
  #undef  _VA_LIST
  #endif

  #define _VA_LIST
  typedef @builtin_t("va_list") va_list;

#endif