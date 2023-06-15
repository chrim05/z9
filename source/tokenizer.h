#ifndef SOURCE_TOKENIZER_H
#define SOURCE_TOKENIZER_H

#include "compilation_tower.h"
#include "misc.h"

typedef struct {
    compilation_tower_t* tower;
    size_t source_index;
} tokenizer_t;

tokenizer_t create_tokenizer(compilation_tower_t* c) {
    return (tokenizer_t) {
        .tower = c,
        .source_index = 0
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

    t->tower->tokens.capacity *= 2;
    const size_t sizeof_kinds = sizeof(token_kind_t) * t->tower->tokens.capacity;
    const size_t sizeof_values = sizeof(token_value_t) * t->tower->tokens.capacity;

    uint8_t* const joint = realloc(t->tower->tokens.kinds, sizeof_kinds + sizeof_values);

    t->tower->tokens.kinds = (token_kind_t*)(joint + 0);
    t->tower->tokens.values = (token_value_t*)(joint + sizeof_kinds);
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

    t->tower->tokens.capacity *= 2;
    const size_t sizeof_contents = sizeof(string_value_content_t) * string_values->capacity;
    const size_t sizeof_lengths = sizeof(string_value_length_t) * string_values->capacity;

    uint8_t* const joint = realloc(string_values->contents, sizeof_contents + sizeof_lengths);

    string_values->contents = (string_value_content_t*)(joint + 0);
    string_values->lengths = (string_value_length_t*)(joint + sizeof_contents);
}

size_t tokenizer_append_string_value(
    tokenizer_t* t,
    string_value_content_t content,
    string_value_length_t length
) {
    tokenizer_maybe_resize_string_values(t);

    string_values_t* const string_values = &t->tower->tokens.string_values;

    const size_t idx = string_values->length;
    string_values->contents[idx] = content;
    string_values->lengths[idx] = length;
    string_values->length++;

    return idx;
}

char const* tokenizer_cur_addr(tokenizer_t* t) {
    return &t->tower->source_code[t->source_index];
}

bool tokenizer_has_word_char(tokenizer_t* t) {
    return tokenizer_has_cur(t) && is_word_char(tokenizer_cur(t));
}

token_value_t parse_word_as_num(
    string_value_content_t content,
    string_value_length_t length
) {
    token_value_t result = 0;

    for (string_value_length_t i = 0; i < length; i++) {
        char c = content[i];
        assert(is_digit_char(c));

        result = result * 10 + (c - '0');
    }

    return result;
}

#define KEYWORDS_COUNT 3
#define MAX_KEYWORD_LENGTH 8
const char keyword_contents[KEYWORDS_COUNT][MAX_KEYWORD_LENGTH] = {
    {'r','e','t','u','r','n',  0,  0},
    {'w','h','i','l','e',  0,  0,  0},
    {'i','f',  0,  0,  0,  0,  0,  0}
};

inline uint64_t fw_as_word(char const* sentinel_buffer) {
    return *(uint64_t const*)sentinel_buffer;
}

bool word_is_keyword(
    string_value_content_t content,
    string_value_length_t length,
    token_kind_t* out_kind
) {
    // fixed word
    uint64_t fw = 0;

    // copying the word into a fixed buffer
    for (uint8_t i = 0; i < length; i++)
        ((char*)&fw)[i] = content[i];

    // comparing the fixed buffer to known keywords
    // in an efficient way
    for (uint8_t i = 0; i < KEYWORDS_COUNT; i++) {
        const uint64_t kw = *(uint64_t const*)(&keyword_contents[i]);

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