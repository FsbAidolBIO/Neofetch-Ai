"""Сборка итогового вывода: логотип слева, информация справа."""

from __future__ import annotations

import json
import os
import shutil
import sys

from . import colors, logos


def info_lines(
    rows: list[tuple[str, str]],
    *,
    accent_color: str = "",
    use_color: bool = True,
) -> list[str]:
    """Строки вида ``OS: Arch Linux`` с подсвеченной подписью."""
    lines: list[str] = []
    for label, value in rows:
        prefix = f"{label}: "
        if use_color and accent_color:
            prefix = f"{colors.BOLD}{colors.color_code(accent_color)}{prefix}{colors.RESET}"
        lines.append(f"{prefix}{value}")
    return lines


def side_by_side(
    logo: list[str],
    info: list[str],
    *,
    gap: int = 2,
) -> list[str]:
    """Склеивает две колонки. Каждая колонка дополняется до нужной высоты."""
    if not logo:
        return list(info)
    if not info:
        return list(logo)

    width = max(colors.visible_len(line) for line in logo) + gap
    height = max(len(logo), len(info))
    result: list[str] = []
    for index in range(height):
        left = logo[index] if index < len(logo) else ""
        right = info[index] if index < len(info) else ""
        pad = " " * max(0, width - colors.visible_len(left))
        line = f"{left}{pad}{right}" if right else left
        result.append(line.rstrip() if not right else line)
    return result


def terminal_width(default: int = 80) -> int | None:
    """Ширина терминала.

    ``None`` — если понять её нельзя (вывод в pipe/файл): тогда колонки
    склеиваем всегда, не подстраиваясь под ширину (так же ведёт себя neofetch).
    """
    columns = os.environ.get("COLUMNS", "")
    if columns.isdigit() and int(columns) > 0:
        return int(columns)
    stream = sys.stdout
    if getattr(stream, "isatty", lambda: False)():
        try:
            return shutil.get_terminal_size((default, 24)).columns
        except (OSError, ValueError):
            return default
    return None


def render(
    rows: list[tuple[str, str]],
    *,
    logo: str = logos.DEFAULT_LOGO,
    use_color: bool = True,
    accent_color: str = "",
    gap: int = 2,
    width: int | None = None,
) -> str:
    """Готовый к печати вывод (с завершающим переводом строки)."""
    logo_lines = logos.render_logo(logo, use_color=use_color)
    info = info_lines(rows, accent_color=accent_color, use_color=use_color)
    if width is None:
        width = terminal_width()

    if not logo_lines:
        lines = info
    elif not info:
        lines = logo_lines
    elif width is None:
        # Ширину узнать не удалось — не подстраиваемся, просто склеиваем колонки.
        lines = side_by_side(logo_lines, info, gap=gap)
    else:
        needed = (
            max(colors.visible_len(line) for line in logo_lines)
            + gap
            + max(colors.visible_len(line) for line in info)
        )
        if needed > width:
            # Узкий терминал: печатаем логотип сверху, данные под ним.
            lines = logo_lines + [""] + info
        else:
            lines = side_by_side(logo_lines, info, gap=gap)

    return "\n".join(lines) + ("\n" if lines else "")


def render_json(rows: list[tuple[str, str]]) -> str:
    """Машиночитаемый вывод: ``{"OS": "Arch Linux", ...}``."""
    data = {label: value for label, value in rows}
    return json.dumps(data, ensure_ascii=False, indent=2)
