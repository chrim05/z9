cmake_minimum_required(VERSION 3.25)
project(source C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_FLAGS_DEBUG "${CMAKE_C_FLAGS_DEBUG} -DDEBUG")

add_executable(source main.c misc.h compilation_tower.h)
