#ifndef SOURCE_COMPILATION_TOWER_H
#define SOURCE_COMPILATION_TOWER_H

#include "misc.h"

#define TEMP_STORAGE_BYTES_SIZE 10000

typedef char const* string_value_content_t;
typedef uint32_t    string_value_length_t;
typedef uint32_t    string_value_hash_t;

// string values are all the identifiers
// 
typedef struct {
    string_value_content_t* contents; // jointly allocated
    string_value_length_t*  lengths;  // jointly allocated
    string_value_hash_t*    hashes;   // jointly allocated

    // these are used to append and resize `contents` and `lengths`
    size_t length;
    size_t capacity;
} string_values_t;

void drop_string_values(string_values_t* s);

// all the token kinds
enum {
    TK_RETURN, TK_WHILE, TK_IF,
    TK_INT,
    TK_ID, TK_NUM,
    TK_LPAR = '(', TK_RPAR = ')',
    TK_LBRACE = '{', TK_RBRACE = '}',
    TK_LBRACK = '[', TK_RBRACK = ']',
    TK_SEMI = ';'
};

typedef uint8_t  token_kind_t;
typedef uint32_t token_value_t;

typedef struct {
    token_kind_t*  kinds;  // jointly allocated
    token_value_t* values; // jointly allocated

    // these are used to append and resize `kinds` and `values`
    size_t length;
    size_t capacity;

    // when token kind is `id` or `string`
    // or whatever has a string representation
    // then, the token value is an index to this array
    string_values_t string_values;
} tokens_t;

void drop_tokens(tokens_t* t);

typedef struct {
    // an arena allocator for whatever needs to be temporary allocated
    storage_t temp;
    // this must be an absolute path
    char const* filepath;
    char const* source_code;
    size_t source_size;

    tokens_t tokens;
} compilation_tower_t;

compilation_tower_t create_compilation_tower(char const* filepath);

void drop_compilation_tower(compilation_tower_t* c);

void compilation_tower_read_file(compilation_tower_t* c);

void compilation_tower_tokenizer(compilation_tower_t* c);

#endif //SOURCE_COMPILATION_TOWER_H
