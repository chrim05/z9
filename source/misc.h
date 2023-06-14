//
// Created by admin on 13/06/2023.
//

#ifndef SOURCE_MISC_H
#define SOURCE_MISC_H

#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>

#define panic(error) panic_impl(error, __FILE__, __LINE__)
#define assert(condition) assert_impl(condition, __FILE__, __LINE__)

_Noreturn void panic_impl(char const* error, char const* file, int line) {
	fprintf(stderr, "[%s:%d] Panic: '%s'\n", file, line, error);
	abort();
}

void assert_impl(bool condition, char const* file, int line) {
#if DEBUG
    if (condition)
        return;

    panic_impl("failed assert", file, line);
#endif
}

typedef struct {
    uint8_t* buffer;
    size_t capacity;
    size_t length;
} storage_t;

storage_t create_storage(size_t initial_capacity) {
    return (storage_t) {
        .buffer = malloc(initial_capacity),
        .capacity = initial_capacity,
        .length = 0
    };
}

bool storage_can_allocate(storage_t const* s, size_t bytes_size) {
    return s->length + bytes_size <= s->capacity;
}

void storage_maybe_resize(storage_t* s, size_t bytes_size) {
    if (storage_can_allocate(s, bytes_size))
        return;

    s->capacity = (s->capacity + bytes_size) * 2;
    s->buffer = realloc(s->buffer, s->capacity);
    assert(s->buffer != NULL);
}

uint8_t* storage_allocate(storage_t* s, size_t bytes_size) {
    storage_maybe_resize(s, bytes_size);

    uint8_t* allocation = &s->buffer[s->length];
    s->length += bytes_size;

    return allocation;
}

void drop_storage(storage_t* s) {
    free(s->buffer);
    s->buffer = NULL;
    s->capacity = 0;
    s->length = 0;
}

void storage_read_file(FILE* stream) {

}

size_t get_file_size(FILE* stream) {

}

FILE* open_file_stream(char const* file) {
    fopen(file, "r");
}

#endif //SOURCE_MISC_H
