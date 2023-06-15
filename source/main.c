#include <stdio.h>

#include "misc.h"
#include "compilation_tower.h"

int main(int argc, char const* const* argv) {
	if (argc != 2)
		panic("expected 2 command line arguments");

	compilation_tower_t tower = create_compilation_tower(argv[1]);
    compilation_tower_read_file(&tower);

    compilation_tower_tokenizer(&tower);
    // compilation_tower_dparser(&tower);
    // compilation_tower_semanalyzer(&tower);

    drop_compilation_tower(&tower);
	return 0;
}
