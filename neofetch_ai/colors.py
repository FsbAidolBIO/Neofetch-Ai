"""ANSI-цвета: палитра, градиенты для логотипа, определение возможностей терминала."""

from __future__ import annotations

import os
import re
import sys

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# Палитра 256 цветов, которой пользуемся по умолчанию.
NAMED_256: dict[str, int] = {
    "black": 0,
    "red": 1,
    "green": 2,
    "yellow": 3,
    "blue": 4,
    "magenta": 5,
    "cyan": 6,
    "white": 7,
    "grey": 8,
    "arch": 33,   # Arch Linux cyan
    "debian": 162,
    "ubuntu": 166,
    "fedora": 33,
    "gentoo": 141,
    "manjaro": 35,
}

HEX_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")


def supports_color() -> bool:
    """Можно ли писать цвет в текущий вывод."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR") or os.environ.get("CLICOLOR_FORCE"):
        return True
    stream = sys.stdout
    return bool(getattr(stream, "isatty", lambda: False)())


def supports_truecolor() -> bool:
    """Поддерживает ли терминал 24-битный цвет."""
    colorterm = os.environ.get("COLORTERM", "").lower()
    return "truecolor" in colorterm or "24bit" in colorterm


def fg_256(code: int) -> str:
    return f"\x1b[38;5;{code}m"


def fg_rgb(rgb: tuple[int, int, int]) -> str:
    return f"\x1b[38;2;{rgb[0]};{rgb[1]};{rgb[2]}m"


def bold(text: str) -> str:
    return f"{BOLD}{text}{RESET}"


def paint(text: str, color: str) -> str:
    """Красит ``text`` в ``color``; цвет задаётся hex (#1793d1) или именем."""
    return f"{color_code(color)}{text}{RESET}" if color else text


def color_code(color: str) -> str:
    """ANSI-последовательность включения цвета по имени или по hex."""
    if not color:
        return ""
    key = color.lower()
    if key in NAMED_256:
        return fg_256(NAMED_256[key])
    match = HEX_RE.match(color)
    if match:
        if supports_truecolor():
            return fg_rgb(hex_to_rgb(color))
        return fg_256(rgb_to_256(hex_to_rgb(color)))
    return ""


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    match = HEX_RE.match(color.strip())
    if not match:
        return (255, 255, 255)
    value = match.group(1)
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def rgb_to_256(rgb: tuple[int, int, int]) -> int:
    """Грубое приведение RGB к индексу палитры xterm-256."""
    red, green, blue = rgb
    if red == green == blue:
        if red < 8:
            return 16
        if red > 248:
            return 231
        return round(((red - 8) / 247) * 24) + 232
    return (
        16
        + 36 * round(red / 255 * 5)
        + 6 * round(green / 255 * 5)
        + round(blue / 255 * 5)
    )


def strip_ansi(text: str) -> str:
    """Убирает ANSI-последовательности (для подсчёта ширины и JSON)."""
    return ANSI_RE.sub("", text)


def visible_len(text: str) -> str.__len__:
    """Длина строки без учёта ANSI-кодов."""
    return len(strip_ansi(text))


def lerp_rgb(
    start: tuple[int, int, int],
    end: tuple[int, int, int],
    ratio: float,
) -> tuple[int, int, int]:
    ratio = max(0.0, min(1.0, ratio))
    return (
        round(start[0] + (end[0] - start[0]) * ratio),
        round(start[1] + (end[1] - start[1]) * ratio),
        round(start[2] + (end[2] - start[2]) * ratio),
    )


def gradient(
    lines: list[str],
    start: str,
    end: str,
    *,
    truecolor: bool | None = None,
) -> list[str]:
    """Раскрашивает строки логотипа вертикальным градиентом ``start`` -> ``end``.

    Пустые строки не трогаем, чтобы не засорять вывод лишними escape-кодами.
    """
    if truecolor is None:
        truecolor = supports_truecolor()
    start_rgb = hex_to_rgb(start)
    end_rgb = hex_to_rgb(end)
    total = max(1, len(lines) - 1)
    result: list[str] = []
    for index, line in enumerate(lines):
        if not line.strip():
            result.append(line)
            continue
        rgb = lerp_rgb(start_rgb, end_rgb, index / total)
        code = fg_rgb(rgb) if truecolor else fg_256(rgb_to_256(rgb))
        result.append(f"{code}{line}{RESET}")
    return result
