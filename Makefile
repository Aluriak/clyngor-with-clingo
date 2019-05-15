
test-install:
	- rm venv/bin/clingo
	python setup.py install

clean:
	- rm -r clyngor_with_clingo.egg-info build dist

test_build: clean
	python setup.py clean --all
	python setup.py build
	python setup.py sdist
test_upload:
	twine upload dist/*
