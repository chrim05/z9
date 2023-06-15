#include <stdio.h>

#include "compilation_tower.h"
#include "tokenizer.h"

string_values_t create_string_values(size_t initial_capacity) {
    const size_t sizeof_contents = sizeof(string_value_content_t) * initial_capacity;
    const size_t sizeof_lengths = sizeof(string_value_length_t) * initial_capacity;

    uint8_t* const joint = malloc(sizeof_contents + sizeof_lengths);

    return (string_values_t) {
        .contents = (string_value_content_t*)(joint + 0),
        .lengths = (string_value_length_t*)(joint + sizeof_contents),
        .length = 0,
        .capacity = initial_capacity
    };
}

tokens_t create_tokens(size_t initial_capacity) {
    const size_t sizeof_kinds = sizeof(token_kind_t) * initial_capacity;
    const size_t sizeof_values = sizeof(token_value_t) * initial_capacity;

    uint8_t* const joint = malloc(sizeof_kinds + sizeof_values);

    return (tokens_t) {
        .kinds = (token_kind_t*)(joint + 0),
        .values = (token_value_t*)(joint + sizeof_kinds),
        .length = 0,
        .capacity = initial_capacity,
        .string_values = create_string_values(initial_capacity / 4)
    };
}

void compilation_tower_tokenizer(compilation_tower_t* c) {
    c->tokens = create_tokens(c->source_size / 4);

    tokenizer_t tokenizer = create_tokenizer(c);
    tokenizer_tokenize(&tokenizer);

    drop_tokenizer(&tokenizer);
}

char const* compilation_tower_preprocess_file(compilation_tower_t* c) {
    char const* const preprocessed_filepath = ".cx";

    char cmd[100];
    snprintf(cmd, sizeof(cmd), "cpp.exe %s %s", c->filepath, preprocessed_filepath);

    int code = system(cmd);

    if (code != 0)
        panic("c preprocessor failed");

    return preprocessed_filepath;
}

void compilation_tower_read_file(compilation_tower_t* c) {
    // preprocessing the file
    char const* const filepath = compilation_tower_preprocess_file(c);

    // opening a stream for the preprocessed file and checking
    FILE* filestream = fopen(filepath, "r");

    if (filestream == NULL)
        panic("file not found");

    // getting the filesize and initializing the arena allocator
    // based on that size, so that i don't need to reallocate
    // the storage too frequently.
    // with 1MB of source code we get 3MB of allocated memory
    c->source_size = get_file_size(filestream);
    c->source_code = malloc(c->source_size);

    // i read the file into the arena allocator
    read_file_into((char*)c->source_code, filestream, c->source_size);

    // closing the file because i already
    // read the whole content in a buffer
    fclose(filestream);
}

void drop_compilation_tower(compilation_tower_t* c) {
    free(&c->source_code);
    drop_storage(&c->temp);
    drop_tokens(&c->tokens);
}

compilation_tower_t create_compilation_tower(char const* filepath) {
    return (compilation_tower_t) {
        .filepath = filepath,
        .temp = create_storage(TEMP_STORAGE_BYTES_SIZE)
    };
}

void drop_tokens(tokens_t* t) {
    free(t->kinds);
    free(t->values);
    drop_string_values(&t->string_values);
}

void drop_string_values(string_values_t* s) {
    free(s->contents);
    free(s->lengths);
}