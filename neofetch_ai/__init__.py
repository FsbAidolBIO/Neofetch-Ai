"""Neofetch-Ai — neofetch и fastfetch на чистом Python без зависимостей.

Публичный API::

    from neofetch_ai import info, logos, render

    rows = info.collect()                       # как neofetch
    rows = info.collect_parallel()              # как fastfetch
    print(render.render(rows, logo="arch"))
"""

from __future__ import annotations

from . import colors, info, logos, render
from .cli import fastfetch_main, neofetch_main

__version__ = "1.0.0"

__all__ = [
    "colors",
    "info",
    "logos",
    "render",
    "neofetch_main",
    "fastfetch_main",
    "__version__",
]
