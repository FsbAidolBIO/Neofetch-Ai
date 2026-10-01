"""Тесты конфигов для настоящих neofetch и fastfetch.

Проверяем без самих утилит: синтаксис bash для config.conf и корректность
JSONC для config.jsonc. Запуск: ``pytest`` либо ``python3 tests/test_configs.py``.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEOFETCH_CONF = ROOT / "neofetch" / "config.conf"
FASTFETCH_CONF = ROOT / "fastfetch" / "config.jsonc"

# Модули fastfetch, использованные в конфиге; сводимся к списку, чтобы
# опечатка в имени модуля ловилась тестом, а не только самим fastfetch.
KNOWN_MODULES = {
    "title", "separator", "os", "host", "kernel", "uptime", "packages", "shell",
    "display", "de", "wm", "wmtheme", "theme", "icons", "font", "terminal",
    "terminalfont", "cpu", "gpu", "memory", "swap", "disk", "battery", "locale",
    "localip", "colors", "break", "custom", "media", "player",
}


def strip_jsonc(text: str) -> str:
    """Убирает комментарии // и /* */ (вне строк) и висячие запятые."""
    out: list[str] = []
    index, length = 0, len(text)
    in_string = escaped = False
    while index < length:
        char = text[index]
        if in_string:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
        elif char == '"':
            in_string = True
            out.append(char)
            index += 1
        elif text.startswith("//", index):
            while index < length and text[index] != "\n":
                index += 1
        elif text.startswith("/*", index):
            index = text.index("*/", index) + 2
        else:
            out.append(char)
            index += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


def test_configs_exist() -> None:
    assert NEOFETCH_CONF.is_file(), f"нет файла {NEOFETCH_CONF}"
    assert FASTFETCH_CONF.is_file(), f"нет файла {FASTFETCH_CONF}"


def test_neofetch_config_is_valid_bash() -> None:
    if not shutil.which("bash"):
        return
    result = subprocess.run(
        ["bash", "-n", str(NEOFETCH_CONF)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_neofetch_config_defines_print_info() -> None:
    text = NEOFETCH_CONF.read_text(encoding="utf-8")
    assert "print_info()" in text
    # Поля объявлены как info "Название" источник
    assert re.search(r'info\s+"OS"\s+distro', text)
    assert re.search(r'info\s+"Kernel"\s+kernel', text)
    # Ключевые настройки на месте
    for option in ("ascii_distro=", "ascii_colors=", "colors=(", "gpu_type="):
        assert option in text, f"нет настройки {option}"


def test_fastfetch_config_is_valid_jsonc() -> None:
    config = json.loads(strip_jsonc(FASTFETCH_CONF.read_text(encoding="utf-8")))
    assert isinstance(config, dict)
    assert isinstance(config["modules"], list)
    assert config["logo"]["source"] == "arch"
    assert config["logo"]["type"] == "builtin"


def test_fastfetch_module_names() -> None:
    config = json.loads(strip_jsonc(FASTFETCH_CONF.read_text(encoding="utf-8")))
    types = [
        module if isinstance(module, str) else module["type"]
        for module in config["modules"]
    ]
    assert types, "список модулей пуст"
    unknown = set(types) - KNOWN_MODULES
    assert not unknown, f"неизвестные модули: {unknown}"
    for expected in ("os", "kernel", "cpu", "gpu", "memory", "disk", "colors"):
        assert expected in types, f"модуль {expected} пропал из конфига"


def test_install_script_is_valid_bash() -> None:
    if not shutil.which("bash"):
        return
    result = subprocess.run(["bash", "-n", str(ROOT / "install.sh")], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


if __name__ == "__main__":
    failures = 0
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
            except Exception as error:  # noqa: BLE001
                failures += 1
                print(f"FAIL {name}: {error!r}")
            else:
                print(f"ok   {name}")
    print(f"\n{'FAILED' if failures else 'PASSED'} ({failures} ошибок)")
    sys.exit(1 if failures else 0)
