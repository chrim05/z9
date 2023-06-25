#include <stdio.h>

#include "compilation_tower.h"
#include "tokenizer.h"

ids_t create_ids(size_t initial_capacity) {
    const size_t sizeof_contents = sizeof(id_content_t) * initial_capacity;
    const size_t sizeof_lengths = sizeof(id_length_t) * initial_capacity;
    const size_t sizeof_hashes = sizeof(id_hash_t) * initial_capacity;

    uint8_t* const joint = malloc(sizeof_contents + sizeof_lengths + sizeof_hashes);

    return (ids_t) {
        .contents = (id_content_t*)(joint + 0),
        .lengths = (id_length_t*)(joint + sizeof_contents),
        .hashes = (id_hash_t*)(joint + sizeof_contents + sizeof_lengths),
        .length = 0,
        .capacity = initial_capacity
    };
}

tokens_t create_tokens(size_t initial_capacity) {
    const size_t sizeof_kinds = sizeof(token_kind_t) * initial_capacity;
    const size_t sizeof_values = sizeof(token_value_t) * initial_capacity;
    const size_t sizeof_locs = sizeof(token_loc_t) * initial_capacity;

    uint8_t* const joint = malloc(sizeof_kinds + sizeof_values + sizeof_locs);

    return (tokens_t) {
        .kinds = (token_kind_t*)(joint + 0),
        .values = (token_value_t*)(joint + sizeof_kinds),
        .locs = (token_loc_t*)(joint + sizeof_values),
        .length = 0,
        .capacity = initial_capacity,
        .ids = create_ids(initial_capacity / 4),
        .filepaths.length = 0,
    };
}

void compilation_tower_tokenizer(compilation_tower_t* c) {
    c->tokens = create_tokens(c->source_size / 4);

    tokenizer_t tokenizer = create_tokenizer(c);
    tokenizer_tokenize(&tokenizer);

    drop_tokenizer(&tokenizer);
}

dnodes_t create_dnodes(size_t initial_capacity) {
    return (dnodes_t) {
        
    };
}

// i intialize the declarations buffer with
// a precise number, when i go out space
// i resize the buffer;
// this number should be just right. (not sure which
// one pick)
#define INITIAL_DECLNS_ALLOCATION_COUNT 1000

void compilation_tower_dparser(compilation_tower_t* c) {
    c->declns = create_declns(INITIAL_DECLNS_ALLOCATION_COUNT);

    tokenizer_t tokenizer = create_tokenizer(c);
    tokenizer_tokenize(&tokenizer);

    drop_tokenizer(&tokenizer);
}

char const* compilation_tower_preprocess_file(compilation_tower_t* c) {
    char const* const preprocessed_filepath = ".z9";

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
    c->source_code = malloc(c->source_size + 1);

    // reading the file into the buffer
    // and updating the source size, i don't know why but
    // ftells often returns a wrong file size
    c->source_size = read_file_into((char*)c->source_code, filestream, c->source_size);

    // closing the file because i already
    // read the whole content in a buffer
    fclose(filestream);
    // removing the temporary file
    remove(filepath);
}

void drop_compilation_tower(compilation_tower_t* c) {
    free((void*)c->source_code);
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
    drop_ids(&t->ids);
}

void drop_ids(ids_t* s) {
    free(s->contents);
}