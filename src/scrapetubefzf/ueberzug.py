"""Helpers to initialize and cleanup ueberzug external processes.

This module encapsulates creation of a FIFO used to send commands to
`ueberzug` / `ueberzugpp` and the helper `tail` process which pipes the
FIFO into ueberzug's stdin.

Functions:
  - setup_ueberzug(cache_dir: Path) -> Optional[Path]
  - cleanup_ueberzug(ueberzug_fifo: Path) -> None
"""
from pathlib import Path
import os
import shutil
import subprocess
import sys
from typing import Optional, Tuple


def setup_ueberzug(cache_dir: Path) -> Optional[Path]:
    """Initialize ueberzug process and FIFO if available.

    Returns ueberzug_fifo or None when ueberzug/ueberzugpp is not available
    or initialization fails.
    """
    # Detect ueberzug or ueberzugpp
    if not (shutil.which("ueberzug") or shutil.which("ueberzugpp")):
        return None

    ueberzug_fifo = cache_dir / f"ueberzug.{os.getpid()}"
    try:
        if not ueberzug_fifo.exists():
            os.mkfifo(ueberzug_fifo)

        # Prefer ueberzugpp if available
        ueberzug_cmd = 'ueberzugpp' if shutil.which("ueberzugpp") else 'ueberzug'
        ueberzug_process = subprocess.Popen(
            [ueberzug_cmd, 'layer', '--silent'],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        tail_process = subprocess.Popen(
            ['tail', '-f', f'--pid={os.getpid()}', str(ueberzug_fifo)],
            stdout=ueberzug_process.stdin,
            stderr=subprocess.DEVNULL,
        )

        return ueberzug_fifo

    except Exception as exc:
        if ueberzug_fifo.exists():
            os.remove(ueberzug_fifo)
        return None


def cleanup_ueberzug(ueberzug_fifo: Optional[Path]) -> None:
    """Remove the FIFO file used for ueberzug.

    Process termination is handled by passing `--pid=...` to the tail process.
    """
    if ueberzug_fifo and ueberzug_fifo.exists():
        os.remove(ueberzug_fifo)
