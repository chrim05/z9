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

void tokenizer_skip(tokenizer_t* t) {
    t->source_index++;
}

bool tokenizer_can_append_token(tokenizer_t* t) {
    return t->tower->tokens.length + 1 <= t->tower->tokens.capacity;
}

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

void tokenizer_next_token(tokenizer_t* t) {
    token_kind_t kind;
    token_value_t value;

    
    
    tokenizer_skip(t);
    tokenizer_can_append_token(t, kind, value);
}

void tokenizer_tokenize(tokenizer_t* t) {
    // printf("source_code:\n```\n%s\n```\n", t->tower->source_code);

    while (tokenizer_has_cur(t))
        tokenizer_next_token(t);
}

#endif //SOURCE_TOKENIZER_H