#!/usr/bin/env python3
"""neofetch — информация о системе рядом с ASCII-логотипом.

Запуск:
    ./neofetch.py                # полный вывод
    ./neofetch.py --logo none    # только текст
    ./neofetch.py --json         # машинный вывод
    ./neofetch.py --list-logos   # доступные логотипы
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from neofetch_ai.cli import neofetch_main  # noqa: E402

if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, OSError):
            pass
    sys.exit(neofetch_main())
