.PHONY: install uninstall

install:
	python -m venv venv
	. venv/bin/activate && pip install .
	@echo "Creating symlink in ~/.local/bin..."
	ln -sf $(shell pwd)/venv/bin/scrapetubefzf ~/.local/bin/

uninstall:
	@if [ -f venv/bin/activate ]; then \
		. venv/bin/activate && pip uninstall -y scrapetubefzf; \
	fi
	@echo "Removing symlink..."
	rm -f ~/.local/bin/scrapetubefzf
	@echo "Removing virtual environment..."
	rm -rf venv
	@echo "Cleaning build artifacts..."
	rm -rf build/ src/__pycache__/ src/scrapetubefzf.egg-info/
