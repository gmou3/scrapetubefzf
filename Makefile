.PHONY: install uninstall

install:
	python -m venv venv
	venv/bin/pip install --upgrade pip
	venv/bin/pip install .
	@echo "Creating symlink in ~/.local/bin..."
	ln -sf $$(pwd)/venv/bin/scrapetubefzf ~/.local/bin/

uninstall:
	@if [ -d venv ]; then \
		echo "Removing virtual environment..."; \
		venv/bin/pip uninstall -y scrapetubefzf; \
		rm -rf venv; \
	fi
	@echo "Removing symlink..."
	rm -f ~/.local/bin/scrapetubefzf
	@echo "Cleaning build artifacts..."
	rm -rf build/ src/scrapetubefzf/__pycache__/ src/scrapetubefzf.egg-info/
