PYTHON ?= python3

.PHONY: install install-dev test smoke acceptance check

install:
	$(PYTHON) -m pip install -r requirements.txt

install-dev:
	$(PYTHON) -m pip install -r requirements-dev.txt

check:
	$(PYTHON) -m compileall -q .

test:
	$(PYTHON) -m unittest tests.test_registry_manager tests.test_cli_smoke

smoke:
	$(PYTHON) -m unittest tests.test_cli_smoke

acceptance:
	$(PYTHON) -m scripts.run_acceptance
