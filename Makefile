docs:
	rm -rf docs	
	mkdir docs
	lockey --help > "docs/lockey.txt"
	lockey init --help > "docs/lockey_init.txt"
	lockey add --help > "docs/lockey_add.txt"
	lockey get --help > "docs/lockey_get.txt"
	lockey ls --help > "docs/lockey_ls.txt"
	lockey rm --help > "docs/lockey_rm.txt"
	lockey destroy --help > "docs/lockey_destroy.txt"
