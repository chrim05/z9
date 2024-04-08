#ifndef SOURCE_MISC_H
#define SOURCE_MISC_H

#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>

#define panic(error) panic_impl(error, __FILE__, __LINE__)
#define assert(condition) assert_impl(condition, __FILE__, __LINE__)
#define dbg(message) dbg_impl(message, __FILE__, __LINE__)
#define here dbg("HERE")

_Noreturn void panic_impl(char const* error, char const* file, int line);

void dbg_impl(char const* error, char const* file, int line);

void assert_impl(bool condition, char const* file, int line);

typedef struct {
    uint8_t* buffer;
    size_t capacity;
    size_t length;
} storage_t;

storage_t create_storage(size_t initial_capacity);

bool storage_can_allocate(storage_t const* s, size_t bytes_size);

void storage_maybe_resize(storage_t* s, size_t bytes_size);

uint8_t* storage_allocate(storage_t* s, size_t bytes_size);

void drop_storage(storage_t* s);

size_t get_file_size(FILE* stream);

size_t read_file_into(char* filebuffer, FILE* stream, size_t filesize);

bool char_is_in_range(char c, char inclusive_start, char inclusive_stop);

bool is_alpha_char(char c);

bool is_digit_char(char c);

bool is_word_char(char c);

#endif //SOURCE_MISC_H
