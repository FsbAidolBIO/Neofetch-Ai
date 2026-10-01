#!/usr/bin/env python3
"""fastfetch — та же информация, но быстро: параллельный сбор полей.

Запуск:
    ./fastfetch.py                # быстрый вывод
    ./fastfetch.py --stat         # + время сбора
    ./fastfetch.py --json         # машинный вывод
    ./fastfetch.py --no-logo      # только текст
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from neofetch_ai.cli import fastfetch_main  # noqa: E402

if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, OSError):
            pass
    sys.exit(fastfetch_main())
