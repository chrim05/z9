//
// Created by admin on 14/06/2023.
//

#ifndef SOURCE_COMPILATION_TOWER_H
#define SOURCE_COMPILATION_TOWER_H

#include "misc.h"

typedef struct {
    // an arena allocator for whatever can be allocated there
    storage_t storage;
    // this must be an absolute path
    char const* filepath;
    FILE* filestream;

} compilation_tower_t;

compilation_tower_t create_compilation_tower(char const* file) {
    return (compilation_tower_t) {
        .filepath = file
    };
}

void drop_compilation_tower(compilation_tower_t* c) {
    drop_storage(&c->storage);
    fclose(c->filestream);
}

void compilation_tower_read_file(compilation_tower_t* c) {
    c->filestream = fopen(c->filepath, "r");

    if (c->filestream == NULL)
        panic("file not found");

    storage_read_file(c->filestream);
}

#endif //SOURCE_COMPILATION_TOWER_H
