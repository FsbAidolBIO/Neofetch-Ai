"""ASCII-логотипы.

Каждый логотип — набор строк одинаковой ширины (последующие пробелы необязательны,
``render.py`` сам выровняет колонку) плюс два hex-цвета для вертикального градиента.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import colors
from .util import parse_env_file


@dataclass(frozen=True)
class Logo:
    name: str
    lines: tuple[str, ...]
    gradient: tuple[str, str]


_ARCH = (
    "                   -`",
    "                  .o+`",
    "                 `ooo/",
    "                `+oooo:",
    "               `+oooooo:",
    "               -+oooooo+:",
    "             `/:-:++oooo+:",
    "            `/++++/+++++++:",
    "           `/++++++++++++++:",
    "          `/+++ooooooooooooo/`",
    "         ./ooosssso++osssssso+`",
    "        .oossssso-````/ossssss+`",
    "       -osssssso.      :ssssssso.",
    "      :osssssss/        osssso+++.",
    "     /ossssssss/        +ssssooo/-",
    "   `/ossssso+/:-        -:/+osssso+-",
    "  `+sso+:-`                 `.-/+oso:",
    " `++:.                           `-/+/",
    " .`                                 `/",
)

_TUX = (
    "        .88888888:.",
    "      88888888.88888.",
    "     .8888888888888888.",
    "     888888888888888888",
    "     88' _`88'_  `88888",
    "     88 88 88 88  88888",
    "     88_88_::_::_:_:8888",
    "     88:::,::,:::::8888",
    "     88`:::::::::'`8888",
    "    .88  `::::'    8:88.",
    "   8888            `8:888.",
    " .8888'             `888888.",
    ".8888:..  .::.  ...:'8888888:.",
    " 8888'     :'     `'::`88:88888",
    " 8888      '         `.888:8888.",
    "  888      .           888:88888",
    "   `'      .           `8888888",
)

_APPLE = (
    "                    'c.",
    "                 ,xNMM.",
    "               .OMMMMo",
    "               OMMM0,",
    "     .;loddo:' loolloddol;.",
    "   cKMMMMMMMMMMNWMMMMMMMMMM0:",
    " .KMMMMMMMMMMMMMMMMMMMMMMMWd.",
    " XMMMMMMMMMMMMMMMMMMMMMMMX.",
    ";MMMMMMMMMMMMMMMMMMMMMMMM:",
    ":MMMMMMMMMMMMMMMMMMMMMMMM:",
    ".MMMMMMMMMMMMMMMMMMMMMMMMX.",
    " kMMMMMMMMMMMMMMMMMMMMMMMMWd.",
    " .XMMMMMMMMMMMMMMMMMMMMMMMMMMk",
    "  .XMMMMMMMMMMMMMMMMMMMMMMMMK.",
    "    kMMMMMMMMMMMMMMMMMMMMMMd",
    "     ;KMMMMMWXXWMMMMMMMk.",
    "       .cooc,.    .,coo:.",
)

_WINDOWS = (
    "        ,.=:^!^!t3Z3z.,",
    "       :tt:::tt333EE3",
    "       Et:::ztt33EEB  @Ee.,     ..,",
    "      ;tt:::tt333EE7 ;EEEEEEttttt33#",
    "     :Et:::zt333EEQ. $EEEEEttttt33QL",
    "     it::::tt333EEF @EEEEEEttttt33F",
    "    ;3=*^```\"*4EEV :EEEEEEttttt33@.",
    "    ,.=::::!t=., ` @EEEEEEtttz33QF",
    "     ;::::::::zt33)   \"4EEEtttji3P*",
    "    :t::::::::tt33.Z3z..  `` ,..g.",
    "     i::::::::zt33F AEEEtttt::::ztF",
    "    ;:::::::::tt33V ;EEEttttt::::t3",
    "     E::::::::zt33L @EEEtttt::::z3F",
    "    {3=*^```\"*4E3) ;EEEtttt:::::tZ`",
    "                  ` :EEEEtttt::::z7",
    "                      \"VEzjt:;;z>*`",
)

LOGOS: dict[str, Logo] = {
    "arch": Logo("arch", _ARCH, ("#1793d1", "#33c1ff")),
    "tux": Logo("tux", _TUX, ("#ffd93d", "#ff8c00")),
    "apple": Logo("apple", _APPLE, ("#c0c0c0", "#6e6e6e")),
    "windows": Logo("windows", _WINDOWS, ("#00a4ef", "#7fba00")),
}

# Синонимы, чтобы `--logo archlinux` и `--logo macos` тоже работали.
ALIASES: dict[str, str] = {
    "archlinux": "arch",
    "arch_linux": "arch",
    "manjaro": "arch",
    "endeavouros": "arch",
    "artix": "arch",
    "garuda": "arch",
    "cachyos": "arch",
    "linux": "tux",
    "penguin": "tux",
    "macos": "apple",
    "mac": "apple",
    "darwin": "apple",
    "apple": "apple",
    "win": "windows",
    "win10": "windows",
    "win11": "windows",
    "none": "none",
    "off": "none",
}

DEFAULT_LOGO = "arch"


def resolve(name: str) -> str | None:
    """Приводит пользовательское имя логотипа к каноническому. ``None`` — не найден."""
    key = name.strip().lower()
    key = ALIASES.get(key, key)
    if key == "none":
        return "none"
    return key if key in LOGOS else None


def logo_lines(name: str) -> list[str]:
    """Строки логотипа без цвета (``[]`` для ``none`` и неизвестных имён)."""
    canonical = resolve(name)
    if canonical is None or canonical == "none":
        return []
    return list(LOGOS[canonical].lines)


def colors_for(name: str) -> tuple[str, str]:
    canonical = resolve(name)
    if canonical is None or canonical == "none":
        return ("#ffffff", "#ffffff")
    return LOGOS[canonical].gradient


def detect() -> str:
    """Угадывает логотип по текущей ОС."""
    from .util import is_macos, is_windows

    if is_macos():
        return "apple"
    if is_windows():
        return "windows"
    release = parse_env_file("/etc/os-release")
    os_id = release.get("ID", "").lower()
    id_like = release.get("ID_LIKE", "").lower()
    arch_family = {
        "arch",
        "archarm",
        "manjaro",
        "manjaro-arm",
        "endeavouros",
        "artix",
        "garuda",
        "cachyos",
        "arcolinux",
        "archcraft",
        "rebornos",
        "blackarch",
    }
    if os_id in arch_family or any(item in arch_family for item in id_like.split()):
        return "arch"
    return "tux"


def render_logo(name: str, *, use_color: bool = True) -> list[str]:
    """Готовые строки логотипа: с градиентом, если цвет разрешён."""
    lines = logo_lines(name)
    if not lines:
        return []
    if not use_color:
        return lines
    start, end = colors_for(name)
    return colors.gradient(lines, start, end)
