# Neofetch-Ai

Готовые конфиги для [neofetch](https://github.com/dylanaraps/neofetch) и
[fastfetch](https://github.com/fastfetch-cli/fastfetch): Arch ASCII-логотип, cyan,
привычный набор полей и одинаковый порядок строк в обеих утилитах.

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
     /ossssssss/        +ssssooo/-      Font: Cantarell 11
   `/ossssso+/:-        -:/+osssso+-    CPU: AMD Ryzen 7 5800X (16) @ 3.80GHz
  `+sso+:-`                 `.-/+oso:   GPU: NVIDIA GeForce RTX 3070
 `++:.                           `-/+/  Memory: 5214 MiB / 32018 MiB (16%)
 .`                                 `/  Swap: 0 B / 8192 MiB (0%)
                                        Disk: 218G / 466G (47%)
                                        Battery: 87% [Charging]
                                        Locale: ru_RU.UTF-8
```

## Установка

```bash
./install.sh                     # оба конфига в ~/.config, старые сохранит как *.bak
./install.sh --config-home /dir  # в свой каталог вместо ~/.config
./install.sh --dry-run           # показать, что куда пойдёт
```

Или вручную:

| Файл | Куда положить |
|---|---|
| `neofetch/config.conf` | `~/.config/neofetch/config.conf` |
| `fastfetch/config.jsonc` | `~/.config/fastfetch/config.jsonc` |

```bash
mkdir -p ~/.config/neofetch ~/.config/fastfetch
cp neofetch/config.conf    ~/.config/neofetch/config.conf
cp fastfetch/config.jsonc  ~/.config/fastfetch/config.jsonc
```

Проверить, не трогая `~/.config`:

```bash
neofetch  --config neofetch/config.conf
fastfetch --config fastfetch/config.jsonc
```

## Termux (Android)

```bash
pkg update && pkg upgrade -y
pkg install -y git neofetch fastfetch

git clone https://github.com/FsbAidolBIO/Neofetch-Ai.git ~/Neofetch-Ai
cd ~/Neofetch-Ai
./install.sh

neofetch      # или fastfetch
```

Если конфиги ещё не влиты в `main`, клонируйте ветку PR:

```bash
git clone -b arena/01a0f682-neofetch-ai https://github.com/FsbAidolBIO/Neofetch-Ai.git ~/Neofetch-Ai
```

Без git (просто распаковать архив):

```bash
mkdir -p ~/Neofetch-Ai
curl -sL https://github.com/FsbAidolBIO/Neofetch-Ai/archive/refs/heads/main.tar.gz \
  | tar xz --strip-components=1 -C ~/Neofetch-Ai
cd ~/Neofetch-Ai && ./install.sh
```

Показывать при каждом запуске терминала:

```bash
grep -q fastfetch ~/.bashrc || printf '\nif [[ $- == *i* ]]; then\n    fastfetch\nfi\n' >> ~/.bashrc
```

Замечания для Termux:

- `~` = `/data/data/com.termux/files/home`, `~/.config` работает как обычно, `install.sh`
  кладёт конфиги именно туда;
- neofetch считает «дистрибутивом» Android, но логотип в конфиге принудительно Arch —
  так и задумано;
- Battery, Host, Resolution на Android часто недоступны — обе утилиты просто пропустят
  эти строки, ничего страшного;
- если `neofetch` выдаёт ошибку про `tput`/`TERM`, сделайте `export TERM=xterm-256color`
  (или добавьте эту строку в `~/.bashrc`).

## Что внутри

| | neofetch (`config.conf`) | fastfetch (`config.jsonc`) |
|---|---|---|
| Логотип | `ascii_distro="arch"`, `ascii_colors=(6 ...)` | `logo.type: "builtin"`, `logo.source: "arch"` |
| Заголовок | `user@host` + подчёркивание `-` | модуль `title` + `separator` |
| Подписи | cyan (`colors=(6 6 8 6 8 7)`) | `display.color.keys: "cyan"` |
| Время сбора | — | `display.stat: true` |
| Цветные блоки | `color_blocks="on"`, `block_range=(0 7)` | модуль `colors` (`symbol: "block"`) |

Поля идут в одном порядке в обоих конфигах: OS, Host, Kernel, Uptime, Packages, Shell,
Resolution, DE, WM, WM Theme, Theme, Icons, Terminal, Terminal Font, Font, CPU, GPU,
Memory, Swap, Disk, Battery, Locale, Local IP.

Тонкие настройки, которые уже выставлены:

- `kernel_shorthand="on"`, `distro_shorthand="off"`, `os_arch="on"` — `6.9.3-arch1-1`,
  `Arch Linux x86_64`;
- `uptime_shorthand="on"` — `2 hours, 14 mins`;
- `memory_unit="mib"`, `memory_percent="on"` — `5214MiB / 32018MiB (16%)`;
- `cpu_cores="logical"`, `cpu_temp="off"`, `gpu_type="all"`, `refresh_rate="off"`;
- `shell_path="off"`, `shell_version="on"` — `bash 5.2.15`, а не `/usr/bin/bash`;
- `disk_show=('/')` — раскомментируйте `('/' '/home')`, если `/home` на отдельном разделе;
- `gap=3`, `color_blocks="on"`.

В fastfetch-конфиге у `cpu` включён `temp`, у `memory` — проценты (`percent.type: 1`);
многопоточный сбор в fastfetch включён по умолчанию, задавать его не нужно.

Полей, которых в системе нет (нет X — не будет Resolution, нет батареи — не будет
Battery), обе утилиты просто не печатают.

## Как менять под себя

Добавить/убрать строку в neofetch — правка `print_info()`:

```bash
info "Song" song        # включить
# info "Swap" swap      # выключить
```

В fastfetch то же самое — порядок модулей в массиве `modules`:

```jsonc
"modules": [
    "title",
    { "type": "separator", "string": "-", "times": 0 },
    "os",
    // "swap",   ← так модуль отключается
    "cpu"
]
```

Свой ASCII-арт вместо встроенного Arch:

- neofetch: `ascii_distro="auto"` (по дистрибутиву) или имя из `neofetch --ascii distro list`;
- fastfetch: `"logo": { "type": "file", "source": "~/ascii-art.txt" }`
  (`auto` — угадать по дистрибутиву, `null` — без логотипа).

Цвета: в neofetch — `colors=(заголовок @ подчёркивание подпись двоеточие значение)` и
`ascii_colors=(...)`, числа 0–15; в fastfetch — `display.color.keys` / `title` / `output`.

## Проверка

```bash
python3 tests/test_configs.py      # без зависимостей
```

Тест проверяет, что `config.conf` — синтаксически корректный bash с нужными настройками,
а `config.jsonc` — валидный JSONC с известными fastfetch именами модулей.

`neofetch/config.conf` прогнан с настоящим neofetch 7.1.0; `fastfetch/config.jsonc`
прошёл валидацию официальной JSON-схемой fastfetch (dev и стабильная 2.69.0).

## Лицензия

MIT — делайте что хотите.
