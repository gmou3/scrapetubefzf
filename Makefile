PYTHON ?= python3
PIP := venv/bin/python -m pip
USER_BIN := $(HOME)/.local/bin

.PHONY: install uninstall

venv:
	$(PYTHON) -m venv venv

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install .
	@echo "Creating symlink in $(USER_BIN)..."
	mkdir -p $(USER_BIN)
	ln -sf $$(pwd)/venv/bin/scrapetubefzf $(USER_BIN)

uninstall:
	@if [ -d venv ]; then \
		echo "Removing virtual environment..."; \
		$(PIP) uninstall -y scrapetubefzf; \
		rm -rf venv; \
	fi
	@echo "Removing symlink..."
	rm -f $(USER_BIN)/scrapetubefzf
	@echo "Cleaning build artifacts..."
	rm -rf build/ src/scrapetubefzf/__pycache__/ src/scrapetubefzf.egg-info/
