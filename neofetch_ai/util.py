"""Мелкие утилиты: запуск процессов, чтение файлов, поиск бинарников, форматирование.

Всё здесь обязано быть «непадким»: информационная утилита не должна ронять
вывод только потому, что в системе нет lspci, /proc смонтирован частично
или бинарник вернул мусор вместо UTF-8.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Sequence

DEFAULT_TIMEOUT = 1.0


def run(
    cmd: Sequence[str] | str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    shell: bool = False,
) -> tuple[int, str, str]:
    """Запускает команду и возвращает ``(returncode, stdout, stderr)``.

    Никогда не бросает исключений: отсутствующий бинарник, таймаут и битый
    вывод — нормальная ситуация для утилиты, которая опрашивает чужие системы.
    """
    try:
        proc = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            timeout=timeout,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.SubprocessError):
        return 1, "", ""
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def out(
    cmd: Sequence[str] | str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    shell: bool = False,
) -> str:
    """stdout команды либо ``''``, если запуск не удался."""
    code, stdout, _ = run(cmd, timeout=timeout, shell=shell)
    return stdout if code == 0 else ""


@lru_cache(maxsize=None)
def which(name: str) -> str | None:
    """Абсолютный путь к бинарнику или ``None``."""
    return shutil.which(name)


def read(path: str | Path) -> str:
    """Содержимое файла без завершающих пробелов, ``''`` при любой ошибке."""
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").strip()
    except (OSError, ValueError):
        return ""


def read_lines(path: str | Path) -> list[str]:
    text = read(path)
    return text.splitlines() if text else []


def parse_env_file(path: str | Path) -> dict[str, str]:
    """Разбирает shell-подобный файл вида ``КЛЮЧ="значение"`` (os-release и т.п.)."""
    result: dict[str, str] = {}
    for line in read_lines(path):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip().strip("'\"")
    return result


def grep_value(text: str, pattern: str, group: int = 1) -> str:
    """Первое совпадение ``pattern`` в многострочном тексте."""
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(group).strip() if match else ""


def first_number(text: str) -> str:
    """Первое ``12.34``-подобное число в строке (используется для версий)."""
    match = re.search(r"\d+(?:\.\d+)+", text)
    return match.group(0) if match else ""


def version_of(binary: str, *, timeout: float = 0.5) -> str:
    """Версия программы из её ``--version`` (или ``-v``), ``''`` если не вышло."""
    if not which(binary):
        return ""
    for flag in ("--version", "-v", "-V"):
        text = out([binary, flag], timeout=timeout)
        if text:
            version = first_number(text.splitlines()[0])
            if version:
                return version
    return ""


def human_bytes(num: float, *, suffix: str = "B", base: int = 1024) -> str:
    """Байты в человекочитаемый вид: ``15918.0 MiB`` -> ``15.5 GiB``."""
    if num <= 0:
        return f"0 {suffix}"
    units = ["", "Ki", "Mi", "Gi", "Ti", "Pi"]
    value = float(num)
    index = 0
    while value >= base and index < len(units) - 1:
        value /= base
        index += 1
    if value >= 100 or index == 0:
        return f"{value:.0f} {units[index]}{suffix}"
    return f"{value:.1f} {units[index]}{suffix}"


def human_uptime(seconds: float) -> str:
    """Секунды в формат neofetch: ``2 days, 3 hours, 15 mins``."""
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds} secs"
    minutes, _ = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    parts: list[str] = []
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} min{'s' if minutes != 1 else ''}")
    return ", ".join(parts[:3]) if parts else f"{seconds} secs"


def count_dirs(path: str | Path) -> int:
    """Число подкаталогов в каталоге (0, если каталога нет или нет прав)."""
    try:
        with os.scandir(path) as entries:
            return sum(1 for entry in entries if entry.is_dir())
    except OSError:
        return 0


def count_lines(path: str | Path, starts_with: str) -> int:
    """Число строк файла, начинающихся с ``starts_with``."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return sum(1 for line in handle if line.startswith(starts_with))
    except OSError:
        return 0


def is_linux() -> bool:
    import platform

    return platform.system() == "Linux" or Path("/proc/version").exists()


def is_macos() -> bool:
    import platform

    return platform.system() == "Darwin"


def is_windows() -> bool:
    import platform

    return platform.system() == "Windows"


def unquote_gsettings(value: str) -> str:
    """gsettings возвращает значения в кавычках — снимаем их."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value
