# Neofetch-Ai

`neofetch` и `fastfetch` на чистом Python 3 — без внешних зависимостей, с ASCII-логотипом
Arch и кроссплатформенным сбором информации (Linux, macOS, Windows, BSD).

Две точки входа с тем же разделением, что у оригиналов:

| | `neofetch.py` | `fastfetch.py` |
|---|---|---|
| Сбор полей | последовательно, максимально подробно | параллельно, в пуле потоков |
| Поля | 23 (включая WM Theme, Icons, Font, Swap, Local IP) | 18 самых ходовых |
| Время | дольше (больше внешних утилит) | быстрее, печатает `Fetch time` по `--stat` |

```
                   -`                   OS: Arch Linux x86_64
                  .o+`                  Host: Lenovo ThinkPad X1 Carbon (20KH0063RT)
                 `ooo/                  Kernel: 6.9.3-arch1-1
                `+oooo:                 Uptime: 2 hours, 14 mins
               `+oooooo:                Packages: 1421 (pacman), 12 (flatpak)
               -+oooooo+:               Shell: zsh 5.9
             `/:-:++oooo+:              Resolution: 2560x1440
            `/++++/+++++++:             DE: KDE Plasma 6.1.4
           `/++++++++++++++:            WM: Hyprland 0.41.2
          `/+++ooooooooooooo/`          WM Theme: Breeze
         ./ooosssso++osssssso+`         Theme: Breeze [GTK], Breeze [Qt]
        .oossssso-````/ossssss+`        Icons: breeze-dark [GTK]
       -osssssso.      :ssssssso.       Terminal: kitty 0.36.4
      :osssssss/        osssso+++.      Terminal Font: JetBrains Mono 10
     /ossssssss/        +ssssooo/-      CPU: AMD Ryzen 7 5800X (16) @ 3.80GHz
   `/ossssso+/:-        -:/+osssso+-    GPU: NVIDIA GeForce RTX 3070
  `+sso+:-`                 `.-/+oso:   Memory: 5214 MiB / 32018 MiB (16%)
 `++:.                           `-/+/  Swap: 0 B / 8192 MiB (0%)
 .`                                 `/  Disk: 218G / 466G (47%)
                                        Battery: 87% [Charging]
                                        Locale: ru_RU.UTF-8
```

## Запуск

Ничего устанавливать не обязательно — работает прямо из репозитория:

```bash
./neofetch.py                 # полный вывод
./fastfetch.py --stat         # быстрый вывод + время сбора
python3 neofetch.py --json    # машинный вывод
python3 -m neofetch_ai        # то же, что ./neofetch.py
```

Установка как обычных команд (в `~/.local/bin`):

```bash
./install.sh                  # neofetch-ai и fastfetch-ai
./install.sh --as-neofetch    # + короткие имена neofetch и fastfetch
./install.sh --prefix /usr/local/bin
```

Или через pip (появятся команды `neofetch-ai` и `fastfetch-ai`):

```bash
pip install .
```

Имена `neofetch-ai` / `fastfetch-ai` намеренно не совпадают с системными `neofetch`
и `fastfetch`, чтобы не перекрывать их. Короткие имена ставятся только по
`./install.sh --as-neofetch`.

## Опции

| Опция | Что делает |
|---|---|
| `--logo NAME` | логотип: `arch`, `tux`, `apple`, `windows`, `auto` (угадать по ОС), `none` |
| `--no-logo` | печатать только текст |
| `--list-logos` | список доступных логотипов |
| `--color COLOR` | цвет подписей: имя (`cyan`, `arch`, …) или hex (`#1793d1`) |
| `--no-color` | выключить ANSI-цвета (уважается и переменная `NO_COLOR`) |
| `--json` | вывести данные в JSON |
| `--gap N` | отступ между логотипом и колонкой данных (по умолчанию 2) |
| `--width N` | считать ширину терминала равной N (0 — определить автоматически) |
| `--stat` | допечатать время сбора |
| `--sequential` | собрать поля последовательно, без потоков (для `fastfetch.py`) |
| `--version`, `-h` | версия и справка |

Примеры:

```bash
./neofetch.py --logo tux --color '#ff9900'
./fastfetch.py --no-logo --json | jq .CPU
./neofetch.py --logo auto
```

## Откуда берутся данные

Никаких зависимостей вне стандартной библиотеки; всё, что не удалось узнать,
просто не печатается (а не выводится как `unknown`).

| Поле | Linux | macOS | Windows |
|---|---|---|---|
| OS, Kernel | `/etc/os-release`, `platform` | `sw_vers`, `sysctl` | `platform`, `wmic` |
| Host | DMI (`/sys/class/dmi/id/*`) | `sysctl hw.model` | `wmic computersystem` |
| Uptime | `/proc/uptime` | `sysctl kern.boottime` | `GetTickCount64` |
| Packages | локальные БД pacman / dpkg / rpm / apk / xbps / portage / brew / flatpak / snap / nix | brew | — |
| Shell, Terminal | дерево процессов в `/proc` | `$TERM_PROGRAM` | — |
| Resolution | `xrandr`, `wlr-randr`, `hyprctl`, `swaymsg` | `system_profiler` | `GetSystemMetrics` |
| DE / WM | `$XDG_CURRENT_DESKTOP`, процессы, `xprop` | Aqua / Quartz | DWM |
| Тема, иконки, шрифты | `gsettings`, `kreadconfig*`, `xfconf-query` | — | — |
| CPU | `/proc/cpuinfo`, `/sys/.../cpufreq` | `sysctl` | `$PROCESSOR_IDENTIFIER` |
| GPU | `lspci`, `/sys/class/drm` | `system_profiler` | `wmic` |
| Memory, Swap | `/proc/meminfo` | `vm_stat` | `GlobalMemoryStatusEx` |
| Disk | `os.statvfs` | `os.statvfs` | `os.statvfs` |
| Battery | `/sys/class/power_supply` | `pmset` | — |
| Local IP | `/proc/net/route` + UDP-сокет | UDP-сокет | UDP-сокет |

Каждый вызов внешней команды идёт с таймаутом (0.3–3 с), поэтому отсутствующий
`lspci` или подвисший X-сервер не могут затормозить вывод.

## Как использовать как библиотеку

```python
from neofetch_ai import info, render

rows = info.collect()              # как neofetch (последовательно)
rows = info.collect_parallel()     # как fastfetch (в пуле потоков)
print(render.render(rows, logo="arch", accent_color="#1793d1"))
```

Добавить своё поле — одна строка в `info.NEOFETCH_FIELDS`:

```python
from neofetch_ai import info

def song() -> str:
    from neofetch_ai.util import out
    return out(["playerctl", "metadata", "--format", "{{ artist }} - {{ title }}"])

info.NEOFETCH_FIELDS += (info.Field("Song", song),)
```

Добавить свой логотип — кортеж строк в `neofetch_ai/logos.py`:

```python
LOGOS["my-distro"] = Logo("my-distro", ("  ___", " /   \\", " \\___/"), ("#ff0000", "#00ff00"))
```

## Тесты

```bash
python3 tests/test_neofetch_ai.py   # без pytest
pytest -q                           # или так
```

Тесты проверяют форматирование, выравнивание колонок, JSON-вывод, CLI и то,
что ни одна функция сбора не бросает исключений на текущей системе.

## Структура

```
neofetch.py            # точка входа neofetch
fastfetch.py           # точка входа fastfetch
install.sh             # установка обёрток в ~/.local/bin
neofetch_ai/
    cli.py             # общий argparse-фронт-энд и два main()
    info.py            # сбор информации + наборы полей
    logos.py           # ASCII-логотипы и автоопределение
    render.py          # склейка логотипа и данных, JSON
    colors.py          # ANSI-цвета и градиенты
    util.py            # запуск процессов, чтение /proc и /sys, форматирование
tests/                 # тесты (pytest или прямой запуск)
```

## Лицензия

MIT — делайте что хотите.
