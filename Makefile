
test-install:
	- rm venv/bin/clingo
	python setup.py install

clean:
	rm -r clyngor_with_clingo.egg-info build dist
