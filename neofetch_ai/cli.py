"""Общий CLI для двух фронт-эндов: ``neofetch`` (подробно) и ``fastfetch`` (быстро).

Разница между ними ровно та же, что и у оригиналов:
  * neofetch собирает поля последовательно и показывает максимум информации;
  * fastfetch собирает то же самое в пуле потоков и печатает время сбора.
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Sequence

from . import info, logos, render

VERSION = "1.0.0"

EPILOG_FIELDS = (
    "поля (neofetch): "
    + ", ".join(field.label for field in info.NEOFETCH_FIELDS)
)


def build_parser(program: str, description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=program,
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "логотипы: "
            + ", ".join(sorted(set(logos.LOGOS) | {"auto", "none"}))
            + f"\n{EPILOG_FIELDS}"
        ),
    )
    parser.add_argument(
        "--logo",
        default=logos.DEFAULT_LOGO,
        metavar="NAME",
        help="логотип: auto, none или имя из списка ниже (по умолчанию: %(default)s)",
    )
    parser.add_argument("--no-logo", action="store_true", help="не печатать логотип")
    parser.add_argument(
        "--list-logos",
        action="store_true",
        help="показать список доступных логотипов и выйти",
    )
    parser.add_argument(
        "--color",
        default="",
        metavar="COLOR",
        help="цвет подписей: имя (cyan, arch, ...) или hex (#1793d1)",
    )
    parser.add_argument("--no-color", action="store_true", help="выключить все ANSI-цвета")
    parser.add_argument("--json", action="store_true", help="вывести данные в JSON")
    parser.add_argument(
        "--gap",
        type=int,
        default=2,
        metavar="N",
        help="отступ между логотипом и данными (по умолчанию: %(default)s)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=0,
        metavar="N",
        help="считать ширину терминала равной N (0 — определить автоматически)",
    )
    parser.add_argument(
        "--stat",
        action="store_true",
        help="допечатать время сбора информации",
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="собирать поля последовательно, без пула потоков",
    )
    parser.add_argument("--version", action="version", version=f"{program} {VERSION}")
    return parser


def _resolve_logo(name: str) -> str:
    if name == "auto":
        return logos.detect()
    canonical = logos.resolve(name)
    if canonical is None:
        # Неизвестное имя — молча откатываемся на автоопределение.
        return logos.detect()
    return canonical


def main(
    argv: Sequence[str] | None = None,
    *,
    program: str,
    description: str,
    fast: bool,
) -> int:
    parser = build_parser(program, description)
    args = parser.parse_args(argv)

    if args.list_logos:
        print(", ".join(sorted(logos.LOGOS)))
        return 0

    fields = info.FASTFETCH_FIELDS if fast else info.NEOFETCH_FIELDS

    started = time.perf_counter()
    if fast and not args.sequential:
        rows = info.collect_parallel(fields)
    else:
        rows = info.collect(fields)
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    if args.json:
        output = render.render_json(rows)
    else:
        logo = "none" if args.no_logo else _resolve_logo(args.logo)
        accent = args.color
        if not accent and logo != "none":
            accent = logos.colors_for(logo)[0]
        output = render.render(
            rows,
            logo=logo,
            use_color=not args.no_color,
            accent_color=accent,
            gap=max(0, args.gap),
            width=args.width or None,
        )
        if args.stat:
            output = output.rstrip("\n") + f"\nFetch time: {elapsed_ms:.1f} ms\n"

    try:
        sys.stdout.write(output if output.endswith("\n") else output + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        return 0
    return 0


def neofetch_main(argv: Sequence[str] | None = None) -> int:
    return main(
        argv,
        program="neofetch",
        description="Показывает информацию о системе рядом с ASCII-логотипом (neofetch-стиль).",
        fast=False,
    )


def fastfetch_main(argv: Sequence[str] | None = None) -> int:
    return main(
        argv,
        program="fastfetch",
        description=(
            "Показывает информацию о системе максимально быстро: "
            "параллельный сбор полей, минимум внешних вызовов."
        ),
        fast=True,
    )
