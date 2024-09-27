SHELL=/bin/bash
.PHONY: clean test
clean:
	rm -fv *.txt *.csv *.jpg
test:
	./ol-poc.py 1565922255
