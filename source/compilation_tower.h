#ifndef SOURCE_COMPILATION_TOWER_H
#define SOURCE_COMPILATION_TOWER_H

#include "misc.h"

#define TEMP_STORAGE_BYTES_SIZE 10000

typedef char const* id_content_t;
typedef uint8_t     id_length_t;
typedef uint32_t    id_hash_t;

typedef struct {
    // here i store all the identifiers used in the source code;
    // i don't store dupplicates of the same identifier
    // (that's why i also store their hashes)
    // this will get me a huge performance improvement
    // during sema
    id_content_t* contents; // jointly allocated
    id_length_t*  lengths;  // jointly allocated
    id_hash_t*    hashes;   // jointly allocated

    // these are used to append and resize `contents`
    uint32_t length;
    uint32_t capacity;
} ids_t;

typedef char const* str_literal_content_t;
typedef uint16_t    str_literal_length_t;

typedef struct {
    // here i store all the string literals
    str_literal_content_t* contents; // jointly allocated
    str_literal_length_t*  lengths;  // jointly allocated

    // these are used to append and resize `contents`
    uint16_t length;
    uint16_t capacity;
} str_literals_t;

void drop_ids(ids_t* s);

// all the token kinds
enum {
    TK_RETURN, TK_WHILE, TK_IF,
    TK_INT, TK_CONST, TK_CHAR, TK_VOID,
    TK_AUTO, TK_BREAK, TK_CASE, TK_CONTINUE,
    TK_DEFAULT, TK_DO, TK_DOUBLE, TK_ELSE,
    TK_ENUM, TK_EXTERN, TK_FLOAT, TK_FOR,
    TK_GOTO, TK_LONG, TK_REGISTER, TK_SHORT,
    TK_SIGNED, TK_SIZEOF, TK_STATIC, TK_STRUCT,
    TK_SWITCH, TK_TYPEDEF, TK_UNION, TK_UNSIGNED,
    TK_VOLATILE,

    TK_LPAR   = '(', TK_RPAR   = ')',
    TK_LBRACE = '{', TK_RBRACE = '}',
    TK_LBRACK = '[', TK_RBRACK = ']',
    TK_SEMI   = ';',
    TK_STAR   = '*',

    // ascii characters after 128 are not used
    // so ID, NUM, etc... can use them as their code;
    // this means that we can't lex those characters as symbols
    // because they would be recognized as ids, nums etc..
    // and this would lead to serious bugs
    TK_ID = 130, TK_NUM, TK_STR,
};

typedef uint8_t  token_kind_t;
typedef uint32_t token_value_t;

typedef struct {
    token_kind_t*  kinds;  // jointly allocated
    token_value_t* values; // jointly allocated

    // these are used to append and resize `kinds`
    size_t length;
    size_t capacity;

    // when token kind is `id`
    // then, the token value is an index to this array
    ids_t ids;
    // instead, when token kind is `str` the token value
    // is and index to this one
    str_literals_t str_literals;
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
