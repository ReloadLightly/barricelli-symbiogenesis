PYTHON ?= .venv/bin/python

.PHONY: build test reproduce figures art atlas
build:
	$(PYTHON) scripts/build.py
test: build
	$(PYTHON) -m unittest discover -s tests -v
reproduce:
	/usr/bin/time -v -o results/milestone-resource.txt $(PYTHON) scripts/milestone.py
figures:
	$(PYTHON) scripts/figures.py
	$(PYTHON) scripts/comparison_figures.py
art:
	$(PYTHON) scripts/art.py
atlas:
	$(PYTHON) scripts/register.py
	$(PYTHON) scripts/build_atlas.py
