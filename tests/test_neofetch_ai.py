"""Тесты. Запуск: ``pytest`` либо ``python3 tests/test_neofetch_ai.py``."""

from __future__ import annotations

import io
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from neofetch_ai import cli, colors, info, logos, render, util  # noqa: E402


# --------------------------------------------------------------------------- #
# Утилиты
# --------------------------------------------------------------------------- #


def test_human_bytes() -> None:
    assert util.human_bytes(0) == "0 B"
    assert util.human_bytes(512) == "512 B"
    assert util.human_bytes(1024) == "1.0 KiB"
    assert util.human_bytes(1024**2) == "1.0 MiB"
    assert util.human_bytes(1536 * 1024**2) == "1.5 GiB"


def test_human_uptime() -> None:
    assert util.human_uptime(5) == "5 secs"
    assert util.human_uptime(60) == "1 min"
    assert util.human_uptime(90) == "1 min"
    assert util.human_uptime(3600) == "1 hour"
    assert "day" in util.human_uptime(60 * 60 * 25)


def test_run_never_raises() -> None:
    assert util.run(["этого-бинарника-нет"], timeout=0.1)[0] == 1
    assert util.out(["этого-бинарника-нет"]) == ""
    assert util.read("/точно/не/существует") == ""


def test_parse_env_file() -> None:
    data = util.parse_env_file("/etc/os-release")
    if data:  # на Windows файла нет — тогда проверяем на временном файле
        assert "NAME" in data or "PRETTY_NAME" in data
    tmp = Path(os.environ.get("TMPDIR", ".")) / "neofetch_ai_test.conf"
    tmp.write_text('KEY="значение"\n# комментарий\nBARE=1\n', encoding="utf-8")
    try:
        parsed = util.parse_env_file(tmp)
    finally:
        tmp.unlink(missing_ok=True)
    assert parsed["KEY"] == "значение"
    assert parsed["BARE"] == "1"


# --------------------------------------------------------------------------- #
# Логотипы и цвет
# --------------------------------------------------------------------------- #


def test_logo_aliases() -> None:
    assert logos.resolve("archlinux") == "arch"
    assert logos.resolve("MacOS") == "apple"
    assert logos.resolve("none") == "none"
    assert logos.resolve("off") == "none"
    assert logos.resolve("нет-такого-лого") is None


def test_logo_lines() -> None:
    for name in logos.LOGOS:
        lines = logos.logo_lines(name)
        assert lines and all(isinstance(line, str) for line in lines)
    assert logos.logo_lines("none") == []
    assert logos.logo_lines("нет-такого-лого") == []


def test_detect_returns_known_logo() -> None:
    assert logos.detect() in set(logos.LOGOS)


def test_gradient_keeps_text() -> None:
    lines = ["abc", "", "def"]
    painted = colors.gradient(lines, "#000000", "#ffffff", truecolor=True)
    assert len(painted) == len(lines)
    assert colors.strip_ansi(painted[0]) == "abc"
    assert painted[1] == ""  # пустые строки не красим


def test_visible_len_ignores_ansi() -> None:
    text = f"{colors.BOLD}OS:{colors.RESET} Arch"
    assert colors.visible_len(text) == len("OS: Arch")


# --------------------------------------------------------------------------- #
# Рендер
# --------------------------------------------------------------------------- #


def test_side_by_side_alignment() -> None:
    logo = ["AA", "BBBB"]
    info = ["OS: Arch", "Kernel: 6.9", "CPU: Ryzen"]
    lines = render.side_by_side(logo, info, gap=2)
    assert len(lines) == 3
    assert lines[0].startswith("AA    OS: Arch")
    assert lines[1].startswith("BBBB  Kernel: 6.9")
    assert lines[2].startswith("      CPU: Ryzen")


def test_side_by_side_with_empty_columns() -> None:
    assert render.side_by_side([], ["OS: Arch"]) == ["OS: Arch"]
    assert render.side_by_side(["AA"], []) == ["AA"]


def test_render_no_logo() -> None:
    rows = [("OS", "Arch Linux"), ("Kernel", "6.9.3")]
    text = render.render(rows, logo="none", use_color=False)
    assert text == "OS: Arch Linux\nKernel: 6.9.3\n"


def test_render_stacked_when_narrow() -> None:
    rows = [("OS", "Arch Linux")]
    text = render.render(rows, logo="arch", use_color=False, width=10)
    assert text.splitlines()[0].strip().startswith("-`")
    assert text.splitlines()[-1] == "OS: Arch Linux"


def test_render_json() -> None:
    rows = [("OS", "Arch Linux"), ("Kernel", "6.9.3")]
    assert json.loads(render.render_json(rows)) == {"OS": "Arch Linux", "Kernel": "6.9.3"}


# --------------------------------------------------------------------------- #
# Сбор информации
# --------------------------------------------------------------------------- #


def test_field_functions_never_raise() -> None:
    for field in info.NEOFETCH_FIELDS + info.FASTFETCH_FIELDS:
        value = field.func()
        assert isinstance(value, str)


def test_collect_returns_core_fields() -> None:
    labels = {label for label, _ in info.collect()}
    assert "OS" in labels
    assert "Kernel" in labels


def test_collect_drops_empty_values() -> None:
    for _, value in info.collect():
        assert value.strip()
        assert "\n" not in value


def test_collect_parallel_matches_sequential_labels() -> None:
    sequential = {label for label, _ in info.collect(info.FASTFETCH_FIELDS)}
    parallel = {label for label, _ in info.collect_parallel(info.FASTFETCH_FIELDS)}
    assert parallel  # что-то да собрали
    assert parallel <= sequential


def test_packages_format() -> None:
    value = info.packages()
    if value:
        assert "(" in value and ")" in value
        for chunk in value.split(", "):
            number, _, name = chunk.partition(" (")
            assert number.isdigit()
            assert name.endswith(")")


def test_memory_format() -> None:
    value = info.memory()
    if value:
        assert " / " in value and value.endswith("%)")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _run_cli(argv: list[str]) -> str:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = cli.main(argv, program="neofetch", description="", fast=False)
    assert exit_code == 0
    return buffer.getvalue()


def test_cli_json() -> None:
    output = _run_cli(["--json"])
    data = json.loads(output)
    assert isinstance(data, dict)
    assert "OS" in data


def test_cli_no_logo_has_no_ansi() -> None:
    output = _run_cli(["--no-logo", "--no-color"])
    assert "\x1b[" not in output
    assert "OS:" in output


def test_cli_logo_none_equals_no_logo() -> None:
    # Значения (память, аптайм) между запусками меняются — сравниваем только поля.
    labels = lambda argv: [line.split(":")[0] for line in _run_cli(argv).splitlines()]  # noqa: E731
    assert labels(["--logo", "none", "--no-color"]) == labels(["--no-logo", "--no-color"])


def test_cli_list_logos() -> None:
    output = _run_cli(["--list-logos"])
    assert "arch" in output


def test_cli_unknown_logo_falls_back() -> None:
    # Неизвестный логотип не должен ломать вывод.
    assert "OS:" in _run_cli(["--logo", "нет-такого", "--no-color"])


def test_fastfetch_cli_stat() -> None:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        assert cli.fastfetch_main(["--stat", "--no-color"]) == 0
    assert "Fetch time:" in buffer.getvalue()


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
