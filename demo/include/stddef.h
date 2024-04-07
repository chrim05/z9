// copied from
// https://github.com/rui314/chibicc/blob/main/include/stddef.h
//
// TODO:
//   * modify it so that it's correct
//     on both nt and unix

#ifndef _STDDEF_H
#define _STDDEF_H 1

  #define NULL ((void*)0)

  typedef unsigned long size_t;
  typedef long          ptrdiff_t;
  typedef unsigned int  wchar_t;
  typedef long          max_align_t;

  #define offsetof(type, member) ((size_t)&(((type *)0)->member))

#endif