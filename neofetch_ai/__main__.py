"""Позволяет запускать пакет как ``python -m neofetch_ai`` (режим neofetch)."""

from __future__ import annotations

import sys

from .cli import neofetch_main

if __name__ == "__main__":
    sys.exit(neofetch_main())
