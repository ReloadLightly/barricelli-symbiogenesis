PYTHON ?= .venv/bin/python

.PHONY: build test reproduce figures art atlas descendants partner-dyad corrections
build:
	$(PYTHON) scripts/build.py
test: build
	$(PYTHON) -m unittest discover -s tests -v
reproduce:
	/usr/bin/time -v -o results/milestone-resource.txt $(PYTHON) scripts/milestone.py
figures:
	$(PYTHON) scripts/figures.py
	$(PYTHON) scripts/comparison_figures.py
	$(PYTHON) scripts/descendant_figures.py
	$(PYTHON) scripts/partner_dyad_figures.py
descendants: build
	$(PYTHON) scripts/descendant_detector.py --phase all
	$(PYTHON) scripts/descendant_figures.py
partner-dyad: build
	$(PYTHON) scripts/partner_dyad.py --phase all
	$(PYTHON) scripts/partner_dyad_figures.py
art:
	$(PYTHON) scripts/art.py
atlas:
	$(PYTHON) scripts/register.py
	$(PYTHON) scripts/build_atlas.py

corrections:
	$(PYTHON) scripts/correct_descriptors.py
	$(PYTHON) scripts/correction_figures.py
