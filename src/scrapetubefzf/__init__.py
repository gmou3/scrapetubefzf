"""Package-wide constants and utilities."""
import os
from pathlib import Path

# Get the package's scripts directory
SCRIPTS_DIR = Path(__file__).parent / "scripts"

# Shell script paths
CLEAR_SCRIPT = SCRIPTS_DIR / "clear.sh"
DOWNLOAD_SCRIPT = SCRIPTS_DIR / "download.sh"
PREVIEW_SCRIPT = SCRIPTS_DIR / "preview.sh"

# Make scripts executable on import
for script in (CLEAR_SCRIPT, DOWNLOAD_SCRIPT, PREVIEW_SCRIPT):
    script.chmod(0o755)

# Import main function from __main__.py
from .__main__ import main

__version__ = "0.1.0"
__all__ = ['main']
