#include <stdio.h>
#include <time.h>

#include "misc.h"
#include "compilation_tower.h"

#define CLOCK_TO_MS(clock_time) ((size_t)((double)clock_time / CLOCKS_PER_SEC * 1000))

int main(int argc, char const* const* argv) {
	if (argc != 2)
		panic("expected 2 command line arguments");

	compilation_tower_t tower = create_compilation_tower(argv[1]);
    clock_t reader_start = clock();
    compilation_tower_read_file(&tower);
    clock_t reader_end = clock();
    clock_t reader_time = reader_end - reader_start;

    clock_t tokenizer_start = clock();
    compilation_tower_tokenizer(&tower);
    clock_t tokenizer_end = clock();
    clock_t tokenizer_time = tokenizer_end - tokenizer_start;

    // compilation_tower_dparser(&tower);
    // compilation_tower_semanalyzer(&tower);

    printf("reader_time+cpp.exe:\t%ums\n", CLOCK_TO_MS(reader_time));
    printf("tokenizer_time:\t\t%ums\n", CLOCK_TO_MS(tokenizer_time));
    
    // /*
    fprintf(stderr, "\nIdentifiers\n");

    for (size_t i = 0; i < tower.tokens.ids.length; i++)
        fprintf(
            stderr,
            "i: %u, h: %u, id(len: %u): '%.*s'\n",
            i,
            tower.tokens.ids.hashes[i],
            tower.tokens.ids.lengths[i],
            tower.tokens.ids.lengths[i],
            tower.tokens.ids.contents[i]
        );

    fprintf(stderr, "-\nString Literals\n");

    for (size_t i = 0; i < tower.tokens.str_literals.length; i++)
        fprintf(
            stderr,
            "i: %u, str(len: %u): '%.*s'\n",
            i,
            tower.tokens.str_literals.lengths[i],
            tower.tokens.str_literals.lengths[i],
            tower.tokens.str_literals.contents[i]
        );

    // /*
    fprintf(stderr, "-\nTokens\n");

    for (size_t i = 0; i < tower.tokens.length; i++)
        fprintf(stderr, "k: %d, v: %u\n", tower.tokens.kinds[i], tower.tokens.values[i]);
    // */

    drop_compilation_tower(&tower);
	return 0;
}
