#include "misc.h"

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

size_t get_file_size(FILE* stream) {
    // save the current position in the file stream
    // and go to the end of it
    size_t current_pos = ftell(stream);
    fseek(stream, 0, SEEK_END);

    // get the file size and go back to the previus position
    size_t filesize = ftell(stream);
    fseek(stream, current_pos, SEEK_SET);

    return filesize;
}

void read_file_into(char* filebuffer, FILE* stream, size_t filesize) {
    fread(filebuffer, 1, filesize, stream);
}

void dbg_impl(char const* message, char const* file, int line) {
    fprintf(stderr, "[%s:%d] Dbg: '%s'\n", file, line, message);
}