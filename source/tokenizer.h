#ifndef SOURCE_TOKENIZER_H
#define SOURCE_TOKENIZER_H

#include <memory.h>
#include <time.h>

#include "compilation_tower.h"
#include "misc.h"

typedef struct {
    compilation_tower_t* tower;
    size_t source_index;
    string_value_hash_t string_values_hash_seed;
} tokenizer_t;

tokenizer_t create_tokenizer(compilation_tower_t* c) {
    return (tokenizer_t) {
        .tower = c,
        .source_index = 0,
        .string_values_hash_seed = time(NULL)
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

    t->tower->tokens.capacity *= 2;
    const size_t sizeof_kinds = sizeof(token_kind_t) * t->tower->tokens.capacity;
    const size_t sizeof_values = sizeof(token_value_t) * t->tower->tokens.capacity;

    uint8_t* const joint = malloc(sizeof_kinds + sizeof_values);

    token_kind_t* const kinds = (token_kind_t*)(joint + 0);
    token_value_t* const values = (token_value_t*)(joint + sizeof_kinds);

    memcpy((void*)kinds, t->tower->tokens.kinds, old_sizeof_kinds);
    memcpy((void*)values, t->tower->tokens.values, old_sizeof_values);
    free((void*)t->tower->tokens.kinds);

    t->tower->tokens.kinds = kinds;
    t->tower->tokens.values = values;
}

void tokenizer_append_token(
    tokenizer_t* t,
    token_kind_t kind,
    token_value_t value
) {
    tokenizer_maybe_resize_tokens(t);

    const size_t idx = t->tower->tokens.length;
    t->tower->tokens.kinds[idx] = kind;
    t->tower->tokens.values[idx] = value;
    t->tower->tokens.length++;
}

bool tokenizer_can_append_string_value(tokenizer_t* t) {
    return
        t->tower->tokens.string_values.length + 1 <=
        t->tower->tokens.string_values.capacity;
}

void tokenizer_maybe_resize_string_values(tokenizer_t* t) {
    if (tokenizer_can_append_string_value(t))
        return;

    string_values_t* const string_values = &t->tower->tokens.string_values;

    const size_t old_sizeof_contents = sizeof(string_value_content_t) * string_values->capacity;
    const size_t old_sizeof_lengths = sizeof(string_value_length_t) * string_values->capacity;
    const size_t old_sizeof_hashes = sizeof(string_value_hash_t) * string_values->capacity;

    string_values->capacity *= 2;
    const size_t sizeof_contents = sizeof(string_value_content_t) * string_values->capacity;
    const size_t sizeof_lengths = sizeof(string_value_length_t) * string_values->capacity;
    const size_t sizeof_hashes = sizeof(string_value_hash_t) * string_values->capacity;

    uint8_t* const joint = malloc(sizeof_contents + sizeof_lengths + sizeof_hashes);

    string_value_content_t* const contents = (string_value_content_t*)(joint + 0);
    string_value_length_t* const lengths = (string_value_length_t*)(joint + sizeof_contents);
    string_value_hash_t* const hashes = (string_value_hash_t*)(joint + sizeof_contents + sizeof_lengths);

    memcpy((void*)contents, string_values->contents, old_sizeof_contents);
    memcpy((void*)lengths, string_values->lengths, old_sizeof_lengths);
    memcpy((void*)hashes, string_values->hashes, old_sizeof_hashes);
    free((void*)string_values->contents);

    string_values->contents = contents;
    string_values->lengths = lengths;
    string_values->hashes = hashes;
}

bool tokenizer_is_string_value(
    tokenizer_t* t,
    string_value_hash_t hash,
    size_t* out_idx
) {
    string_values_t* const string_values = &t->tower->tokens.string_values;

    for (size_t i = 0; i < string_values->length; i++)
        if (string_values->hashes[i] == hash) {
            *out_idx = i;
            return true;
        }

    return false;
}

void tokenizer_set_string_value(
    tokenizer_t* t,
    size_t idx,
    string_value_content_t content,
    string_value_length_t length,
    string_value_hash_t hash
) {
    string_values_t* const string_values = &t->tower->tokens.string_values;

    string_values->contents[idx] = content;
    string_values->lengths[idx] = length;
    string_values->hashes[idx] = hash;
}

// implementation from
// https://github.com/abrandoned/murmur2/blob/master/MurmurHash2.c
string_value_hash_t hash_string_value(
    string_value_content_t content,
    string_value_length_t length,
    string_value_hash_t seed
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

size_t tokenizer_append_string_value(
    tokenizer_t* t,
    string_value_content_t content,
    string_value_length_t length
) {
    const string_value_hash_t hash_seed = t->string_values_hash_seed;
    const string_value_hash_t hash = hash_string_value(content, length, hash_seed);
    string_values_t* const string_values = &t->tower->tokens.string_values;
    size_t idx = string_values->length;

    if (tokenizer_is_string_value(t, hash, &idx)) {
        tokenizer_set_string_value(t, idx, content, length, hash);
        return idx;
    }

    tokenizer_maybe_resize_string_values(t);
    string_values->length++;

    tokenizer_set_string_value(t, idx, content, length, hash);
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
    string_value_content_t content,
    string_value_length_t length
) {
    token_value_t result = 0;

    for (string_value_length_t i = 0; i < length; i++) {
        char c = content[i];
        // assert(is_digit_char(c));

        result = result * 10 + (c - '0');
    }

    return result;
}

#define KEYWORDS_COUNT 4
#define MAX_KEYWORD_LENGTH 8
const char keywords[KEYWORDS_COUNT][MAX_KEYWORD_LENGTH] = {
    {'r','e','t','u','r','n',  0,  0},
    {'w','h','i','l','e',  0,  0,  0},
    {'i','f',  0,  0,  0,  0,  0,  0},
    {'i','n','t',  0,  0,  0,  0,  0},
};

bool word_is_keyword(
    string_value_content_t content,
    string_value_length_t length,
    token_kind_t* out_kind
) {
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
    const string_value_content_t content = tokenizer_cur_addr(t);
    string_value_length_t length = 0;

    // collecting the word
    while (tokenizer_has_word_char(t)) {
        length++;
        tokenizer_skip(t);
    }

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
    *out_value = tokenizer_append_string_value(t, content, length);
}

void tokenizer_skip_cpp(tokenizer_t* t) {
    while (tokenizer_has_cur(t) && tokenizer_cur(t) != '\n')
        tokenizer_skip(t);
}

void tokenizer_skip_white(tokenizer_t* t) {
    while (tokenizer_has_cur(t)) {
        char c = tokenizer_cur(t);

        switch (c) {
            case '#':
                tokenizer_skip_cpp(t);
                break;

            case '\n':
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
}

void tokenizer_next_token(tokenizer_t* t) {
    tokenizer_skip_white(t);

    if (!tokenizer_has_cur(t))
        return;

    token_kind_t kind;
    token_value_t value;
    char c = tokenizer_cur(t);

    if (is_word_char(c))
        tokenizer_tokenize_word(t, &kind, &value);
    else
        tokenizer_tokenize_punctuation(t, &kind);
    
    tokenizer_skip(t);
    tokenizer_append_token(t, kind, value);
}

void tokenizer_tokenize(tokenizer_t* t) {
    // printf("source_code:\n```\n%s\n```\n", t->tower->source_code);

    while (tokenizer_has_cur(t))
        tokenizer_next_token(t);
}

#endif //SOURCE_TOKENIZER_H