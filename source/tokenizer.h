#ifndef SOURCE_TOKENIZER_H
#define SOURCE_TOKENIZER_H

#include <memory.h>
#include <time.h>
#include <string.h>

#include "compilation_tower.h"
#include "misc.h"

typedef struct {
    compilation_tower_t* tower;
    id_hash_t hash_seed;

    size_t source_index;
    size_t source_line;
    size_t index_of_linestart;
    // an index to tokens_t.filepaths
    uint16_t file;
} tokenizer_t;

uint16_t compilation_tower_append_filepath(
    compilation_tower_t* c,
    char const* path,
    uint16_t length,
    uint32_t hash
) {
    filepaths_t* const filepaths = &c->tokens.filepaths;
    const uint16_t idx = filepaths->length;

    filepaths->paths[idx] = path;
    filepaths->lengths[idx] = length;
    filepaths->hashes[idx] = hash;
    filepaths->length++;

    return idx;
}

id_hash_t hash_id(id_content_t content, id_length_t length, id_hash_t seed);
void tokenizer_tokenize_str(tokenizer_t* t, token_value_t* out_value);

tokenizer_t create_tokenizer(compilation_tower_t* c) {
    const id_hash_t hash_seed = time(NULL);
    const uint16_t filepath_len = strlen(c->filepath);
    const uint16_t file = compilation_tower_append_filepath(
        c,
        c->filepath,
        filepath_len,
        // this may cause bugs when paths are bigger than
        // 256 chars, however i don't really care
        // since the path would just be truncated,
        // no crash involved
        hash_id(c->filepath, filepath_len, hash_seed)
    );

    return (tokenizer_t) {
        .tower = c,
        .hash_seed = hash_seed,
        .source_index = 0,
        .source_line = 0,
        .index_of_linestart = 0,
        .file = file,
    };
}

void drop_tokenizer(tokenizer_t* t) {
    (void)t;
}

bool tokenizer_has_char(tokenizer_t* t, size_t offset) {
    return t->source_index + offset < t->tower->source_size;
}

bool tokenizer_has_cur(tokenizer_t* t) {
    return tokenizer_has_char(t, 0);
}

char tokenizer_char(tokenizer_t* t, size_t offset) {
    return t->tower->source_code[t->source_index + offset];
}

char tokenizer_cur(tokenizer_t* t) {
    return tokenizer_char(t, 0);
}

void tokenizer_advance(tokenizer_t* t, size_t count) {
    t->source_index += count;
}

void tokenizer_skip(tokenizer_t* t) {
    tokenizer_advance(t, 1);
}

bool tokenizer_can_append_token(tokenizer_t* t) {
    return t->tower->tokens.length + 1 <= t->tower->tokens.capacity;
}

// TODO: move all these functions to compilation_tower and
// make them to use the compilation_tower_t instance instead of
// the tokenizer_t one, since they are not actually related to the tokenizer
void tokenizer_maybe_resize_tokens(tokenizer_t* t) {
    if (tokenizer_can_append_token(t))
        return;

    const size_t old_sizeof_kinds = sizeof(token_kind_t) * t->tower->tokens.capacity;
    const size_t old_sizeof_values = sizeof(token_value_t) * t->tower->tokens.capacity;
    const size_t old_sizeof_locs = sizeof(token_loc_t) * t->tower->tokens.capacity;

    t->tower->tokens.capacity *= 2;
    const size_t sizeof_kinds = sizeof(token_kind_t) * t->tower->tokens.capacity;
    const size_t sizeof_values = sizeof(token_value_t) * t->tower->tokens.capacity;
    const size_t sizeof_locs = sizeof(token_loc_t) * t->tower->tokens.capacity;

    uint8_t* const joint = malloc(sizeof_kinds + sizeof_values + sizeof_locs);

    token_kind_t* const kinds = (token_kind_t*)(joint + 0);
    token_value_t* const values = (token_value_t*)(joint + sizeof_kinds);
    token_loc_t* const locs = (token_loc_t*)(joint + sizeof_values);

    memcpy((void*)kinds, t->tower->tokens.kinds, old_sizeof_kinds);
    memcpy((void*)values, t->tower->tokens.values, old_sizeof_values);
    memcpy((void*)locs, t->tower->tokens.locs, old_sizeof_locs);
    free((void*)t->tower->tokens.kinds);

    t->tower->tokens.kinds = kinds;
    t->tower->tokens.values = values;
    t->tower->tokens.locs = locs;
}

void tokenizer_append_token(
    tokenizer_t* t,
    token_kind_t kind,
    token_value_t value,
    token_loc_t loc
) {
    tokenizer_maybe_resize_tokens(t);

    const size_t idx = t->tower->tokens.length;
    t->tower->tokens.kinds[idx] = kind;
    t->tower->tokens.values[idx] = value;
    t->tower->tokens.locs[idx] = loc;
    t->tower->tokens.length++;
}

bool tokenizer_can_append_id(tokenizer_t* t) {
    return
        t->tower->tokens.ids.length + 1 <=
        t->tower->tokens.ids.capacity;
}

void tokenizer_maybe_resize_ids(tokenizer_t* t) {
    if (tokenizer_can_append_id(t))
        return;

    ids_t* const ids = &t->tower->tokens.ids;

    const size_t old_sizeof_contents = sizeof(id_content_t) * ids->capacity;
    const size_t old_sizeof_lengths = sizeof(id_length_t) * ids->capacity;
    const size_t old_sizeof_hashes = sizeof(id_hash_t) * ids->capacity;

    ids->capacity *= 4;
    const size_t sizeof_contents = sizeof(id_content_t) * ids->capacity;
    const size_t sizeof_lengths = sizeof(id_length_t) * ids->capacity;
    const size_t sizeof_hashes = sizeof(id_hash_t) * ids->capacity;

    uint8_t* const joint = malloc(sizeof_contents + sizeof_lengths + sizeof_hashes);

    id_content_t* const contents = (id_content_t*)(joint + 0);
    id_length_t* const lengths = (id_length_t*)(joint + sizeof_contents);
    id_hash_t* const hashes = (id_hash_t*)(joint + sizeof_contents + sizeof_lengths);

    memcpy((void*)contents, ids->contents, old_sizeof_contents);
    memcpy((void*)lengths, ids->lengths, old_sizeof_lengths);
    memcpy((void*)hashes, ids->hashes, old_sizeof_hashes);
    free((void*)ids->contents);

    ids->contents = contents;
    ids->lengths = lengths;
    ids->hashes = hashes;
}

bool tokenizer_is_id(
    tokenizer_t* t,
    id_hash_t hash,
    size_t* out_idx
) {
    ids_t* const ids = &t->tower->tokens.ids;

    for (size_t i = 0; i < ids->length; i++)
        if (ids->hashes[i] == hash) {
            *out_idx = i;
            return true;
        }

    return false;
}

void tokenizer_set_id(
    tokenizer_t* t,
    size_t idx,
    id_content_t content,
    id_length_t length,
    id_hash_t hash
) {
    ids_t* const ids = &t->tower->tokens.ids;

    ids->contents[idx] = content;
    ids->lengths[idx] = length;
    ids->hashes[idx] = hash;
}

// implementation from
// https://github.com/abrandoned/murmur2/blob/master/MurmurHash2.c
id_hash_t hash_id(
    id_content_t content,
    id_length_t length,
    id_hash_t seed
) {
    const uint32_t m = 0x5bd1e995;
    const int32_t r = 24;

    uint32_t h = seed ^ length;
    uint8_t const* data = (uint8_t const*)content;

    while (length >= 4) {
        uint32_t k = *(uint32_t*)data;

        k *= m;
        k ^= k >> r;
        k *= m;

        h *= m;
        h ^= k;

        data += 4;
        length -= 4;
    }

    switch (length) {
        case 3:
            h ^= data[2] << 16;
            /* fallthrough */
        case 2:
            h ^= data[1] << 8;
            /* fallthrough */
        case 1:
            h ^= data[0];
            h *= m;
            break;
    };
    
    h ^= h >> 13;
    h *= m;
    h ^= h >> 15;

    return h;
}

size_t tokenizer_append_id(
    tokenizer_t* t,
    id_content_t content,
    id_length_t length
) {
    const id_hash_t hash_seed = t->hash_seed;
    const id_hash_t hash = hash_id(content, length, hash_seed);
    ids_t* const ids = &t->tower->tokens.ids;
    size_t idx = ids->length;

    if (tokenizer_is_id(t, hash, &idx)) {
        tokenizer_set_id(t, idx, content, length, hash);
        return idx;
    }

    tokenizer_maybe_resize_ids(t);
    ids->length++;

    tokenizer_set_id(t, idx, content, length, hash);
    return idx;
}

char const* tokenizer_cur_addr(tokenizer_t* t) {
    return &t->tower->source_code[t->source_index];
}

bool tokenizer_has_word_char(tokenizer_t* t) {
    // we can avoid checking for `tokenizer_has_cur`
    // since the source code has the null terminator
    // and this function will return false whether
    // it's matched
    return is_word_char(tokenizer_cur(t));
}

token_value_t parse_word_as_num(
    id_content_t content,
    id_length_t length
) {
    token_value_t result = 0;

    for (id_length_t i = 0; i < length; i++) {
        char c = content[i];
        assert(is_digit_char(c));

        result = result * 10 + (c - '0');
    }

    return result;
}

// hardcoded keywords
#define KEYWORDS_COUNT 32
#define MAX_KEYWORD_LENGTH 8
const char keywords[KEYWORDS_COUNT][MAX_KEYWORD_LENGTH] = {
    {'r','e','t','u','r','n',  0,  0},
    {'w','h','i','l','e',  0,  0,  0},
    {'i','f',  0,  0,  0,  0,  0,  0},
    {'i','n','t',  0,  0,  0,  0,  0},
    {'c','o','n','s','t',  0,  0,  0},
    {'c','h','a','r',  0,  0,  0,  0},
    {'v','o','i','d',  0,  0,  0,  0},
    {'a','u','t','o',  0,  0,  0,  0},
    {'b','r','e','a','k',  0,  0,  0},
    {'c','a','s','e',  0,  0,  0,  0},
    {'c','o','n','t','i','n','u','e'},
    {'d','e','f','a','u','l','t',  0},
    {'d','o',  0,  0,  0,  0,  0,  0},
    {'d','o','u','b','l','e',  0,  0},
    {'e','l','s','e',  0,  0,  0,  0},
    {'e','n','u','m',  0,  0,  0,  0},
    {'e','x','t','e','r','n',  0,  0},
    {'f','l','o','a','t',  0,  0,  0},
    {'f','o','r',  0,  0,  0,  0,  0},
    {'g','o','t','o',  0,  0,  0,  0},
    {'l','o','n','g',  0,  0,  0,  0},
    {'r','e','g','i','s','t','e','r'},
    {'s','h','o','r','t',  0,  0,  0},
    {'s','i','g','n','e','d',  0,  0},
    {'s','i','z','e','o','f',  0,  0},
    {'s','t','a','t','i','c',  0,  0},
    {'s','t','r','u','c','t',  0,  0},
    {'s','w','i','t','c','h',  0,  0},
    {'t','y','p','e','d','e','f',  0},
    {'u','n','i','o','n',  0,  0,  0},
    {'u','n','s','i','g','n','e','d'},
    {'v','o','l','a','t','i','l','e'}
};

bool word_is_keyword(
    id_content_t content,
    id_length_t length,
    token_kind_t* out_kind
) {
    // this tokenizer only support keywords
    // that fit in 8bytes
    if (length > 8)
        return false;

    // fixed word
    uint64_t fw = 0;

    // copying the word into a fixed buffer
    // where the unused bytes on the right
    // are zero
    // memcpy resulted slower in stress test
    for (uint8_t i = 0; i < length; i++)
        ((char*)&fw)[i] = content[i];

    // comparing the fixed buffer to known keywords
    // in an efficient way
    for (uint8_t i = 0; i < KEYWORDS_COUNT; i++) {
        const uint64_t kw = *(uint64_t const*)(&keywords[i]);

        if (kw == fw) {
            *out_kind = i;
            return true;
        }
    }

    return false;
}

void tokenizer_tokenize_word(
    tokenizer_t* t,
    token_kind_t* out_kind,
    token_value_t* out_value
) {
    const id_content_t content = tokenizer_cur_addr(t);
    const size_t idx = t->source_index;

    // collecting the word
    while (tokenizer_has_word_char(t))
        tokenizer_skip(t);

    id_length_t length = t->source_index - idx;

    // going back to the last word's char
    // (tokernizer_next_token, which is the caller
    //  will skip this one, in this way we don't loose
    //  any char)
    tokenizer_advance(t, -1);

    // if the word starts with a digit
    // then the entire word must be a literal number
    if (is_digit_char(content[0])) {
        *out_kind = TK_NUM;
        *out_value = parse_word_as_num(content, length);
        return;
    }

    // otherwise it's an identifier
    // but is that identifier a keyword?
    if (word_is_keyword(content, length, out_kind))
        return;

    // otherwise must be an identifier
    *out_kind = TK_ID;
    *out_value = tokenizer_append_id(t, content, length);
}

size_t tokenizer_cpp_get_linenumber(tokenizer_t* t) {
    // skipping both the `#` and the whitespace
    // after it
    tokenizer_skip(t);
    tokenizer_skip(t);

    const id_content_t content = tokenizer_cur_addr(t);
    const size_t idx = t->source_index;

    // collecting the line number
    while (tokenizer_has_cur(t) && is_digit_char(tokenizer_cur(t)))
        tokenizer_skip(t);

    id_length_t length = t->source_index - idx;

    if (length == 0)
        return 0;

    return parse_word_as_num(content, length);
}

uint16_t tokenizer_cpp_get_file(tokenizer_t* t) {
    // skipping the whitespace between
    // the linenumber and the filepath
    tokenizer_skip(t);

    // a union is needed here to avoid
    // "error: dereferencing type-punned pointer will break strict-aliasing rules"
    // when compiling with optimizations
    union { token_value_t v; uint32_t u[2]; } value;
    tokenizer_tokenize_str(t, &value.v);

    const uint32_t idx = value.u[0];
    const uint32_t length = value.u[1];

    filepaths_t* const filepaths = &t->tower->tokens.filepaths;
    char const* const content = &t->tower->source_code[idx];

    const id_hash_t hash = hash_id(content, length, t->hash_seed);

    for (uint16_t i = 0; i < filepaths->length; i++)
        if (hash == filepaths->hashes[i])
            return i;

    return compilation_tower_append_filepath(t->tower, content, length, hash);
}

void tokenizer_skip_cpp(tokenizer_t* t) {
    // maybe the hashtag is not from cpp
    size_t new_source_line = tokenizer_cpp_get_linenumber(t);

    if (new_source_line != 0) {
        t->source_line = new_source_line - 1;
        t->file = tokenizer_cpp_get_file(t);
    }

    while (tokenizer_has_cur(t) && tokenizer_cur(t) != '\n')
        tokenizer_skip(t);
}

void tokenizer_skip_white(tokenizer_t* t) {
    // i don't need to check every time
    // if reached eof, in fact i placed
    // a null terminator at the end of the
    // soure code, so that if i match '\0'
    // i just break the cycle
    while (true) {
        char c = tokenizer_cur(t);

        switch (c) {
            case '#':
                tokenizer_skip_cpp(t);
                break;

            case '\n':
                t->index_of_linestart = t->source_index + 1;
                t->source_line++;
                /* fallthrough */
            case ' ':
                break;

            default:
                return;
        }

        tokenizer_skip(t);
    }
}

void tokenizer_tokenize_punctuation(tokenizer_t* t, token_kind_t* out_kind) {
    *out_kind = (token_kind_t)tokenizer_cur(t);

    assert(*out_kind != TK_ID);
    assert(*out_kind != TK_NUM);
    assert(*out_kind != TK_STR);
}

bool tokenizer_has_str_end_char(tokenizer_t* t) {
    char c = tokenizer_cur(t);
    return (c == '"') | (c == '\0');
}

void tokenizer_tokenize_str(tokenizer_t* t, token_value_t* out_value) {
    // skipping the first `"`
    tokenizer_skip(t);

    const size_t idx = t->source_index;

    while (!tokenizer_has_str_end_char(t))
        tokenizer_skip(t);

    const uint32_t length = t->source_index - idx;
    // the string may be enclosed
    // so i check if the last character of the token was an apex
    assert(t->tower->source_code[idx + length] == '"');

    ((uint32_t*)out_value)[0] = idx;
    ((uint32_t*)out_value)[1] = length;
}

uint16_t tokenizer_col(tokenizer_t* t) {
    return t->source_index - t->index_of_linestart;
}

token_loc_t tokenizer_loc(tokenizer_t* t) {
    return (token_loc_t) {
        // i add one, since line zero doesn't exist
        .line = t->source_line + 1,
        // the same here with columns
        .col = tokenizer_col(t) + 1,
        .file = t->file,
    };
}

void tokenizer_next_token(tokenizer_t* t) {
    tokenizer_skip_white(t);

    if (!tokenizer_has_cur(t))
        return;

    token_kind_t kind;
    token_value_t value;
    token_loc_t loc = tokenizer_loc(t);
    char c = tokenizer_cur(t);

    if (is_word_char(c))
        tokenizer_tokenize_word(t, &kind, &value);
    else if (c == '"') {
        kind = TK_STR;
        tokenizer_tokenize_str(t, &value);
    }
    else
        tokenizer_tokenize_punctuation(t, &kind);
    
    tokenizer_skip(t);
    tokenizer_append_token(t, kind, value, loc);
}

void tokenizer_tokenize(tokenizer_t* t) {
    // printf("source_code:\n```\n%s\n```\n", t->tower->source_code);

    while (tokenizer_has_cur(t))
        tokenizer_next_token(t);
}

#endif //SOURCE_TOKENIZER_H