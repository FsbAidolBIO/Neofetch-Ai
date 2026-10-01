"""Сбор информации о системе.

Каждая функция возвращает уже готовую к показу строку (без ANSI-кодов —
раскраской занимается ``render.py``) или пустую строку, если данные получить
не удалось. Пустые поля просто не попадают в вывод.

Источники данных, по приоритету:
  Linux   — /proc, /sys, DMI, lspci, gsettings, xrandr
  macOS   — sysctl, system_profiler, sw_vers
  Windows — ctypes/win32 API, wmic
Никаких внешних зависимостей: только стандартная библиотека.
"""

from __future__ import annotations

import json
import os
import platform
import re
import socket
import time
from pathlib import Path
from typing import Callable, NamedTuple

from .util import (
    count_dirs,
    count_lines,
    first_number,
    grep_value,
    human_bytes,
    human_uptime,
    is_linux,
    is_macos,
    is_windows,
    out,
    parse_env_file,
    read,
    read_lines,
    unquote_gsettings,
    version_of,
    which,
)


class Field(NamedTuple):
    label: str
    func: Callable[[], str]


# --------------------------------------------------------------------------- #
# ОС, ядро, железо
# --------------------------------------------------------------------------- #


def _os_release() -> dict[str, str]:
    for path in ("/etc/os-release", "/usr/lib/os-release"):
        data = parse_env_file(path)
        if data:
            return data
    return {}


def operating_system() -> str:
    """Красивое имя ОС: ``Arch Linux``, ``Debian GNU/Linux 12 (bookworm)``."""
    if is_macos():
        product = grep_value(out(["sw_vers"]), r"^ProductName:\s*(.+)$")
        version = grep_value(out(["sw_vers"]), r"^ProductVersion:\s*(.+)$")
        return f"{product} {version}".strip() or f"macOS {platform.mac_ver()[0]}"
    if is_windows():
        return f"Windows {platform.release()} ({platform.version()})"
    release = _os_release()
    if release:
        pretty = release.get("PRETTY_NAME")
        if pretty:
            return pretty
        return f'{release.get("NAME", "")} {release.get("VERSION", "")}'.strip()
    return f"{platform.system()} {platform.release()}"


def host() -> str:
    """Модель компьютера/материнской платы из DMI (или аналога)."""
    if is_macos():
        return grep_value(out(["sysctl", "-n", "hw.model"]), r"^(.+)$")
    if is_windows():
        for line in out(["wmic", "computersystem", "get", "model"], timeout=2.0).splitlines():
            line = line.strip()
            if line and line.lower() != "model":
                return line
        return ""
    if not is_linux():
        return ""

    junk = {
        "to be filled by o.e.m.",
        "not applicable",
        "default string",
        "invalid",
        "none",
        "system manufacturer",
        "system product name",
        "unknown",
        "",
    }
    dmi = "/sys/class/dmi/id"
    sys_vendor = read(f"{dmi}/sys_vendor")
    product_name = read(f"{dmi}/product_name")
    product_version = read(f"{dmi}/product_version")
    product_family = read(f"{dmi}/product_family")
    board_name = read(f"{dmi}/board_name")
    board_vendor = read(f"{dmi}/board_vendor")

    name = product_name if product_name.lower() not in junk else ""
    if not name:
        name = board_name if board_name.lower() not in junk else ""
    if not name and product_family.lower() not in junk:
        name = product_family
    if not name:
        model = read("/proc/device-tree/model")
        if model:
            return model.replace("\x00", "").strip()
        return ""

    vendor = sys_vendor if sys_vendor.lower() not in junk else ""
    if not vendor and board_vendor.lower() not in junk:
        vendor = board_vendor
    if vendor and vendor.lower() in name.lower():
        vendor = ""

    version = product_version if product_version.lower() not in junk else ""
    if version and version.lower() in name.lower():
        version = ""

    parts = [part for part in (vendor, name) if part]
    result = " ".join(parts)
    if version:
        result += f" ({version})"
    return result


def kernel() -> str:
    """Версия ядра; ``fastfetch`` дополнительно показывает имя ядра."""
    return platform.release().strip()


def kernel_with_name() -> str:
    return f"{platform.system()} {platform.release()}".strip()


def uptime() -> str:
    """Аптайм в формате ``2 days, 3 hours, 15 mins``."""
    if is_linux():
        text = read("/proc/uptime")
        if text:
            try:
                return human_uptime(float(text.split()[0]))
            except (ValueError, IndexError):
                pass
    elif is_macos():
        text = out(["sysctl", "-n", "kern.boottime"])
        secs = grep_value(text, r"sec\s*=\s*(\d+)")
        if secs:
            return human_uptime(time.time() - int(secs))
    elif is_windows():
        try:
            import ctypes

            ticks = ctypes.windll.kernel32.GetTickCount64()  # type: ignore[attr-defined]
            return human_uptime(int(ticks) / 1000.0)
        except Exception:
            pass
    return ""


def packages() -> str:
    """Число установленных пакетов по пакетным менеджерам.

    Считаем только по локальным базам (быстро и без сети); то, что посчитать
    нельзя, просто пропускаем — как это делает настоящий fastfetch.
    """
    counts: list[tuple[int, str]] = []

    def add(number: int, name: str) -> None:
        if number > 0:
            counts.append((number, name))

    add(count_dirs("/var/lib/pacman/local"), "pacman")
    add(count_lines("/var/lib/dpkg/status", "Package:"), "dpkg")
    add(count_lines("/var/lib/apk/db/installed", "P:"), "apk")
    if which("rpm"):
        add(len(out(["rpm", "-qa"], timeout=2.0).splitlines()), "rpm")
    if which("xbps-query"):
        add(len(out(["xbps-query", "-l"], timeout=2.0).splitlines()), "xbps")
    if which("equo") or Path("/var/db/pkg").is_dir():
        total = 0
        try:
            for category in Path("/var/db/pkg").iterdir():
                if category.is_dir():
                    total += count_dirs(category)
        except OSError:
            total = 0
        add(total, "portage")
    for cellar in ("/opt/homebrew/Cellar", "/usr/local/Cellar", "/home/linuxbrew/.linuxbrew/Cellar"):
        add(count_dirs(cellar), "brew")
    if which("flatpak"):
        add(len(out(["flatpak", "list"], timeout=2.0).splitlines()), "flatpak")
    add(count_dirs("/snap"), "snap")
    if which("nix-env"):
        add(len(out(["nix-env", "-q"], timeout=3.0).splitlines()), "nix")

    if not counts:
        return ""
    counts.sort(key=lambda item: item[0], reverse=True)
    return ", ".join(f"{number} ({name})" for number, name in counts)


# --------------------------------------------------------------------------- #
# Оболочка, терминал, графика
# --------------------------------------------------------------------------- #


def _proc_info(pid: int) -> tuple[str, int] | None:
    """``(comm, ppid)`` процесса из /proc/<pid>/stat."""
    data = read(f"/proc/{pid}/stat")
    if not data:
        return None
    try:
        end = data.rindex(")")
        comm = data[data.index("(") + 1 : end]
        ppid = int(data[end + 2 :].split()[1])
    except (ValueError, IndexError):
        return None
    return comm, ppid


def _ancestors(limit: int = 12) -> list[str]:
    """Имена (comm) процессов от родителя текущего и вверх по дереву."""
    names: list[str] = []
    pid = os.getppid()
    for _ in range(limit):
        info = _proc_info(pid)
        if not info:
            break
        comm, ppid = info
        names.append(comm)
        if ppid <= 1:
            break
        pid = ppid
    return names


def _running_processes() -> set[str]:
    """Множество имён всех запущенных процессов (только Linux)."""
    names: set[str] = set()
    try:
        for entry in Path("/proc").iterdir():
            if entry.name.isdigit():
                comm = read(entry / "comm")
                if comm:
                    names.add(comm)
    except OSError:
        pass
    return names


def shell() -> str:
    """Текущая оболочка с версией: ``bash 5.2.21``."""
    name = ""
    if is_linux():
        for comm in _ancestors(limit=3):
            if not comm.startswith(("python", "neofetch", "fastfetch")):
                name = comm
                break
    if not name:
        name = os.path.basename(os.environ.get("SHELL", "").strip())
    if not name:
        return ""
    version = version_of(name)
    return f"{name} {version}".strip()


_TERMINALS: dict[str, str] = {
    "alacritty": "Alacritty",
    "kitty": "Kitty",
    "foot": "Foot",
    "wezterm": "WezTerm",
    "wezterm-gui": "WezTerm",
    "gnome-terminal-server": "GNOME Terminal",
    "gnome-terminal": "GNOME Terminal",
    "konsole": "Konsole",
    "xfce4-terminal": "Xfce4 Terminal",
    "lxterminal": "LXTerminal",
    "mate-terminal": "MATE Terminal",
    "tilix": "Tilix",
    "terminator": "Terminator",
    "termite": "Termite",
    "sakura": "Sakura",
    "st": "st",
    "xterm": "Xterm",
    "urxvt": "urxvt",
    "urxvtd": "urxvt",
    "terminology": "Terminology",
    "cool-retro-term": "cool-retro-term",
    "qterminal": "QTerminal",
    "deepin-terminal": "Deepin Terminal",
    "guake": "Guake",
    "yakuake": "Yakuake",
    "warp": "Warp",
    "hyper": "Hyper",
    "contour": "Contour",
    "rio": "Rio",
    "zed": "Zed",
    "vscode": "Visual Studio Code",
    "code": "Visual Studio Code",
}


def terminal() -> str:
    """Эмулятор терминала, в котором мы запущены."""
    terminal_program = os.environ.get("TERM_PROGRAM", "")
    if terminal_program:
        name = terminal_program.removesuffix(".app")
        return f"{name} {version_of(terminal_program)}".strip()

    if is_macos():
        term = os.environ.get("TERM", "")
        return "Apple Terminal" if term.startswith("xterm") else term
    if is_windows():
        return os.environ.get("TERM", "") or "Windows Console"

    for comm in _ancestors():
        if comm in _TERMINALS:
            name = _TERMINALS[comm]
            return f"{name} {version_of(comm)}".strip()
    return ""


def resolution() -> str:
    """Разрешение экрана: ``2560x1440``."""
    if is_linux():
        xrandr = out(["xrandr", "--nograb", "--current"], timeout=1.5)
        if xrandr:
            current = grep_value(xrandr, r"current\s+(\d+)\s*x\s+(\d+)")
            if current:
                width, height = current.split()
                return f"{width}x{height}"
            for line in xrandr.splitlines():
                if " connected" in line and "*" in line:
                    size = grep_value(line, r"(\d+)x(\d+)\+")
                    if size:
                        return size
        wlr = out(["wlr-randr"], timeout=1.5)
        if wlr:
            size = grep_value(wlr, r"(\d+)x(\d+)\s*px")
            if size:
                return size
        hypr = out(["hyprctl", "monitors", "-j"], timeout=1.5)
        if hypr:
            try:
                monitors = json.loads(hypr)
                if monitors:
                    monitor = monitors[0]
                    return f'{int(monitor.get("width", 0))}x{int(monitor.get("height", 0))}'
            except (ValueError, TypeError, KeyError):
                pass
        sway = out(["swaymsg", "-t", "get_outputs"], timeout=1.5)
        if sway:
            try:
                outputs = json.loads(sway)
                if outputs:
                    rect = outputs[0].get("rect", {})
                    return f'{int(rect.get("width", 0))}x{int(rect.get("height", 0))}'
            except (ValueError, TypeError, KeyError):
                pass
    elif is_macos():
        text = out(["system_profiler", "SPDisplaysDataType"], timeout=3.0)
        size = grep_value(text, r"(?:UI Looks like|Resolution):\s*(\d+)\s*x\s*(\d+)")
        if size:
            return size.replace(" ", "")
    elif is_windows():
        try:
            import ctypes

            user32 = ctypes.windll.user32  # type: ignore[attr-defined]
            return f"{user32.GetSystemMetrics(0)}x{user32.GetSystemMetrics(1)}"
        except Exception:
            pass
    return ""


_DE_VERSIONS: dict[str, tuple[str, tuple[str, ...]]] = {
    "kde": ("KDE Plasma", ("plasmashell", "kded5")),
    "plasma": ("KDE Plasma", ("plasmashell",)),
    "gnome": ("GNOME", ("gnome-shell",)),
    "ubuntu": ("GNOME", ("gnome-shell",)),
    "pop": ("COSMIC", ("cosmic-session",)),
    "cosmic": ("COSMIC", ("cosmic-session",)),
    "xfce": ("Xfce", ("xfce4-session",)),
    "lxqt": ("LXQt", ("lxqt-session",)),
    "lxde": ("LXDE", ("lxsession",)),
    "cinnamon": ("Cinnamon", ("cinnamon",)),
    "x-cinnamon": ("Cinnamon", ("cinnamon",)),
    "mate": ("MATE", ("mate-session",)),
    "budgie": ("Budgie", ("budgie-desktop",)),
    "deepin": ("Deepin", ("dde-desktop",)),
    "dde": ("Deepin", ("dde-desktop",)),
    "unity": ("Unity", ("unity",)),
    "pantheon": ("Pantheon", ("io.elementary.wingpanel",)),
}


def desktop_environment() -> str:
    """Окружение рабочего стола: ``KDE Plasma 6.1.4``."""
    if is_macos():
        return "Aqua"
    if is_windows():
        return ""

    raw = os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION") or ""
    if os.environ.get("KDE_FULL_SESSION") == "true":
        raw = raw or "KDE"
    for token in raw.lower().replace("-", " ").split(":"):
        token = token.strip()
        if token in _DE_VERSIONS:
            name, binaries = _DE_VERSIONS[token]
            for binary in binaries:
                version = first_number(out([binary, "--version"]))
                if version:
                    return f"{name} {version}"
            return name
    return ""


_KNOWN_WMS: dict[str, str] = {
    # Wayland-композиторы проверяем первыми
    "sway": "Sway",
    "Hyprland": "Hyprland",
    "niri": "niri",
    "river": "River",
    "wayfire": "Wayfire",
    "labwc": "labwc",
    "weston": "Weston",
    "cage": "Cage",
    "gamescope": "Gamescope",
    "mutter": "Mutter",
    "kwin_wayland": "KWin",
    # X11
    "kwin_x11": "KWin",
    "i3": "i3",
    "bspwm": "bspwm",
    "dwm": "dwm",
    "xmonad": "xmonad",
    "qtile": "Qtile",
    "awesome": "Awesome",
    "openbox": "Openbox",
    "fluxbox": "Fluxbox",
    "icewm": "IceWM",
    "IceWM": "IceWM",
    "jwm": "JWM",
    "fvwm": "FVWM",
    "sawfish": "Sawfish",
    "spectrwm": "spectrwm",
    "herbstluftwm": "herbstluftwm",
    "leftwm": "LeftWM",
    "ratpoison": "ratpoison",
    "stumpwm": "StumpWM",
    "wmii": "wmii",
    "xfwm4": "Xfwm4",
    "marco": "Marco",
    "metacity": "Metacity",
    "muffin": "Muffin",
    "compiz": "Compiz",
    "enlightenment": "Enlightenment",
}


def window_manager() -> str:
    """Оконный менеджер / композитор: ``Hyprland 0.41.2``."""
    if is_macos():
        return "Quartz Compositor"
    if is_windows():
        return "DWM"
    if not is_linux():
        return ""

    running = _running_processes()
    for comm, name in _KNOWN_WMS.items():
        if comm in running:
            version = first_number(out([comm, "--version"]))
            return f"{name} {version}".strip()

    # Ничего не нашли в процессах — спросим у X-сервера.
    if os.environ.get("DISPLAY") and which("xprop"):
        win_id = out(["xprop", "-root", "_NET_SUPPORTING_WM_CHECK"], timeout=1.0)
        wm_id = grep_value(win_id, r"#\s*(0x[0-9a-fA-F]+)")
        if wm_id:
            name = out(["xprop", "-id", wm_id, "_NET_WM_NAME"], timeout=1.0)
            name = grep_value(name, r'=\s*"?(.*?)"?$')
            if name:
                return name
    return ""


def _gsettings(schema: str, key: str) -> str:
    if not which("gsettings"):
        return ""
    value = out(["gsettings", "get", schema, key], timeout=0.8)
    return unquote_gsettings(value)


def _kreadconfig(file: str, group: str, key: str) -> str:
    for binary in ("kreadconfig6", "kreadconfig5"):
        if which(binary):
            return out([binary, "--file", file, "--group", group, "--key", key], timeout=0.8)
    return ""


def _gtk_theme() -> str:
    return _gsettings("org.gnome.desktop.interface", "gtk-theme")


def _qt_theme() -> str:
    if _kreadconfig("kdeglobals", "General", "ColorScheme"):
        return _kreadconfig("kdeglobals", "General", "ColorScheme")
    qt5ct = parse_env_file(Path.home() / ".config" / "qt5ct" / "qt5ct.conf").get("style", "")
    if qt5ct:
        return qt5ct
    qt6ct = parse_env_file(Path.home() / ".config" / "qt6ct" / "qt6ct.conf").get("style", "")
    return qt6ct


def wm_theme() -> str:
    """Тема оформления окон (заголовков) WM."""
    value = _gsettings("org.gnome.shell.extensions.user-theme", "name")
    if value:
        return value
    value = _gsettings("org.gnome.desktop.wm.preferences", "theme")
    if value:
        return value
    value = _kreadconfig("kwinrc", "org.kde.kdecoration2", "theme")
    if value:
        return value
    if which("xfconf-query"):
        value = out(["xfconf-query", "-c", "xfwm4", "-p", "/general/theme"], timeout=0.8)
        if value:
            return value
    return ""


def theme() -> str:
    """Тема виджетов: ``Breeze [Qt]`` / ``Adwaita-dark [GTK]``."""
    gtk = _gtk_theme()
    qt = _qt_theme()
    if gtk and qt:
        return f"{gtk} [GTK], {qt} [Qt]"
    if gtk:
        return f"{gtk} [GTK]"
    if qt:
        return f"{qt} [Qt]"
    return ""


def icons() -> str:
    """Тема иконок: ``Papirus-Dark``."""
    value = _gsettings("org.gnome.desktop.interface", "icon-theme")
    if value:
        return value
    return _kreadconfig("kdeglobals", "Icons", "Theme")


def font() -> str:
    """Шрифт интерфейса: ``Cantarell 11``."""
    return _gsettings("org.gnome.desktop.interface", "font-name")


def terminal_font() -> str:
    """Моноширинный шрифт терминала: ``JetBrains Mono 10``."""
    value = _gsettings("org.gnome.desktop.interface", "monospace-font-name")
    if value:
        return value
    if which("xrdb"):
        xrdb = out(["xrdb", "-query"], timeout=0.8)
        return grep_value(xrdb, r"^[^!]*\.?faceName:?\s*(.+)$")
    return ""


# --------------------------------------------------------------------------- #
# Процессор, видео, память, диски
# --------------------------------------------------------------------------- #


def _cpu_model() -> str:
    if is_linux():
        cpuinfo = read("/proc/cpuinfo")
        model = grep_value(cpuinfo, r"^model name\s*:\s*(.+)$")
        if not model:
            model = grep_value(cpuinfo, r"^(?:Hardware|Processor)\s*:\s*(.+)$")
        if not model and is_linux():
            for line in read_lines("/proc/cpuinfo"):
                if line.lower().startswith("cpu part"):
                    model = f"ARM ({line.split(':')[-1].strip()})"
                    break
        return model
    if is_macos():
        return out(["sysctl", "-n", "machdep.cpu.brand_string"])
    return os.environ.get("PROCESSOR_IDENTIFIER", "") or platform.processor()


def _cpu_count() -> int:
    if is_linux():
        cpuinfo = read("/proc/cpuinfo")
        count = cpuinfo.count("processor\t:")
        if count:
            return count
    if is_macos():
        text = out(["sysctl", "-n", "hw.ncpu"])
        if text.isdigit():
            return int(text)
    return os.cpu_count() or 1


def _cpu_freq_mhz() -> float:
    """Максимальная частота CPU в МГц (0, если узнать не удалось)."""
    if is_linux():
        best = 0.0
        for candidate in Path("/sys/devices/system/cpu").glob("cpu*/cpufreq/cpuinfo_max_freq"):
            value = read(candidate)
            if value.isdigit():
                best = max(best, int(value) / 1000.0)
        if best:
            return best
        lscpu = out(["lscpu"], timeout=1.0)
        text = grep_value(lscpu, r"CPU(?: max)? MHz:\s*([\d.]+)")
        if text:
            try:
                return float(text)
            except ValueError:
                pass
        text = grep_value(read("/proc/cpuinfo"), r"^cpu MHz\s*:\s*([\d.]+)$")
        if text:
            try:
                return float(text)
            except ValueError:
                pass
    elif is_macos():
        text = out(["sysctl", "-n", "hw.cpufrequency"])
        if text.isdigit():
            return int(text) / 1_000_000.0
    return 0.0


def cpu() -> str:
    """Процессор: ``AMD Ryzen 7 5800X (16) @ 3.80GHz``."""
    model = _cpu_model()
    if not model:
        return ""
    # Частоту из model name выкидываем: она добавляется ниже, из sysfs.
    model = re.sub(r"\s*@\s*[\d.]+\s*[GMk]?Hz", "", model, flags=re.IGNORECASE)
    for junk in ("(R)", "(TM)", "(C)", "Corporation", "Technologies", "Inc.", "Core", "CPU"):
        model = model.replace(junk, "")
    model = " ".join(model.split())
    result = f"{model} ({_cpu_count()})"
    freq = _cpu_freq_mhz()
    if freq > 0:
        result += f" @ {freq / 1000.0:.2f}GHz"
    return result


_GPU_VENDORS: dict[str, str] = {
    "nvidia": "NVIDIA",
    "advanced micro devices": "AMD",
    "amd/ati": "AMD",
    "ati technologies": "ATI",
    "intel": "Intel",
    "arm": "ARM",
    "qualcomm": "Qualcomm",
    "apple": "Apple",
    "via": "VIA",
    "matrox": "Matrox",
    "aspeed": "ASPEED",
}

_GPU_CLASSES = ("vga compatible controller", "3d controller", "display controller")


def _clean_gpu_name(vendor: str, device: str) -> str:
    vendor_key = vendor.lower()
    short_vendor = vendor
    for key, name in _GPU_VENDORS.items():
        if key in vendor_key:
            short_vendor = name
            break
    else:
        short_vendor = vendor.split()[0] if vendor else ""

    # "GP106 [GeForce GTX 1060 6GB]" -> "GeForce GTX 1060 6GB"
    brackets = re.findall(r"\[([^\]]+)\]", device)
    name = brackets[-1] if brackets else device
    name = " ".join(name.split())
    if short_vendor and short_vendor.lower() not in name.lower():
        name = f"{short_vendor} {name}"
    return name.strip()


def gpu() -> str:
    """Видеокарта(ы): ``NVIDIA GeForce RTX 3070``."""
    gpus: list[str] = []
    if is_linux() and which("lspci"):
        text = out(["lspci", "-mm"], timeout=1.5)
        for line in text.splitlines():
            parts = line.split('"')
            if len(parts) < 6:
                continue
            device_class = parts[1].lower()
            if not any(name in device_class for name in _GPU_CLASSES):
                continue
            vendor, device = parts[3], parts[5]
            gpus.append(_clean_gpu_name(vendor, device))
    if not gpus and is_linux():
        # Нет lspci — читаем sysfs drm.
        for card in sorted(Path("/sys/class/drm").glob("card[0-9]")):
            vendor = read(card / "device" / "vendor")
            device = read(card / "device" / "device")
            if vendor.startswith("0x"):
                code = vendor[2:]
                name = {"10de": "NVIDIA", "1002": "AMD", "8086": "Intel"}.get(
                    code, f"PCI:{code}"
                )
                gpus.append(f"{name} {device}".strip())
    if not gpus and is_macos():
        text = out(["system_profiler", "SPDisplaysDataType"], timeout=3.0)
        for line in text.splitlines():
            if "Chipset Model" in line:
                gpus.append(grep_value(line, r"Chipset Model:\s*(.+)$"))
    if not gpus and is_windows():
        text = out(["wmic", "path", "win32_VideoController", "get", "name"], timeout=2.0)
        for line in text.splitlines():
            line = line.strip()
            if line and not line.lower().startswith("name"):
                gpus.append(line)

    # Убираем дубликаты, сохраняя порядок.
    unique: list[str] = []
    for name in gpus:
        if name and name not in unique:
            unique.append(name)
    return ", ".join(unique)


def _meminfo() -> dict[str, int]:
    result: dict[str, int] = {}
    for line in read_lines("/proc/meminfo"):
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        digits = value.split()
        if digits and digits[0].isdigit():
            result[key] = int(digits[0])
    return result


def memory() -> str:
    """ОЗУ: ``3.21 GiB / 15.55 GiB (21%)``."""
    used = total = 0
    if is_linux():
        info = _meminfo()
        total = info.get("MemTotal", 0) * 1024
        # Как в neofetch/fastfetch: кэш и буферы не считаем занятыми.
        free = info.get("MemFree", 0)
        buffers = info.get("Buffers", 0)
        cached = info.get("Cached", 0)
        reclaimable = info.get("SReclaimable", 0)
        shmem = info.get("Shmem", 0)
        used = (total // 1024 - free - buffers - cached - reclaimable + shmem) * 1024
    elif is_macos():
        total_text = out(["sysctl", "-n", "hw.memsize"])
        if total_text.isdigit():
            total = int(total_text)
        vm = out(["vm_stat"])
        page = 4096
        pagesize = out(["sysctl", "-n", "hw.pagesize"])
        if pagesize.isdigit():
            page = int(pagesize)
        occupied = 0
        for key in (
            "Pages active:",
            "Pages wired down:",
            "Pages occupied by compressor:",
        ):
            value = grep_value(vm, rf"{re.escape(key)}\s*(\d+)")
            if value.isdigit():
                occupied += int(value)
        used = occupied * page
    elif is_windows():
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))  # type: ignore[attr-defined]
            total = status.ullTotalPhys
            used = total - status.ullAvailPhys
        except Exception:
            return ""

    if total <= 0:
        return ""
    percent = max(0, min(100, round(used * 100 / total)))
    return f"{human_bytes(used)} / {human_bytes(total)} ({percent}%)"


def swap() -> str:
    """Подкачка: ``0 B / 4.00 GiB (0%)``. Пусто, если swap выключен."""
    if not is_linux():
        return ""
    info = _meminfo()
    total = info.get("SwapTotal", 0) * 1024
    if total <= 0:
        return ""
    used = (info.get("SwapTotal", 0) - info.get("SwapFree", 0)) * 1024
    percent = max(0, min(100, round(used * 100 / total)))
    return f"{human_bytes(used)} / {human_bytes(total)} ({percent}%)"


def disk() -> str:
    """Занятое место на дисках: ``218G / 466G (47%)``."""
    mounts: list[str]
    if is_windows():
        drive = os.path.splitdrive(os.getcwd())[0] or "C:"
        mounts = [drive + os.sep]
    else:
        mounts = ["/"]
        home = str(Path.home())
        if home not in ("/", "/root"):
            mounts.append(home)

    parts: list[str] = []
    seen: set[int] = set()
    for mount in mounts:
        try:
            stat = os.statvfs(mount)
        except OSError:
            continue
        total = stat.f_blocks * stat.f_frsize
        free = stat.f_bfree * stat.f_frsize
        used = total - free
        if total <= 0:
            continue
        if stat.f_fsid in seen:
            continue
        seen.add(stat.f_fsid)
        percent = max(0, min(100, round(used * 100 / total)))
        line = f"{human_bytes(used)} / {human_bytes(total)} ({percent}%)"
        parts.append(f"{mount}: {line}" if len(mounts) > 1 else line)
    return ", ".join(parts)


def battery() -> str:
    """Батарея: ``87% [Charging]``."""
    if is_linux():
        base = Path("/sys/class/power_supply")
        if not base.is_dir():
            return ""
        reports: list[str] = []
        for entry in sorted(base.iterdir()):
            if not entry.name.startswith(("BAT", "CMB")):
                continue
            capacity = read(entry / "capacity")
            status = read(entry / "status")
            if not capacity.isdigit():
                continue
            reports.append(f"{capacity}% [{status.title()}]" if status else f"{capacity}%")
        return ", ".join(reports)
    if is_macos():
        text = out(["pmset", "-g", "batt"], timeout=1.0)
        percent = grep_value(text, r"(\d+)%")
        state = "Charging" if "charging" in text.lower() else "Discharging"
        return f"{percent}% [{state}]" if percent else ""
    return ""


def locale() -> str:
    """Локаль: ``ru_RU.UTF-8``."""
    return os.environ.get("LANG") or os.environ.get("LC_ALL") or ""


def _default_interface() -> str:
    if is_linux():
        for line in read_lines("/proc/net/route")[1:]:
            fields = line.split()
            if len(fields) >= 2 and fields[1] == "00000000":
                return fields[0]
        return grep_value(out(["ip", "route", "get", "8.8.8.8"]), r"dev\s+(\S+)")
    return ""


def local_ip() -> str:
    """Локальный IP: ``192.168.1.42/24`` (без внешних запросов)."""
    interface = _default_interface()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.3)
        sock.connect(("8.8.8.8", 80))
        address = sock.getsockname()[0]
        sock.close()
    except OSError:
        return ""
    return f"{address} ({interface})" if interface else address


# --------------------------------------------------------------------------- #
# Наборы полей
# --------------------------------------------------------------------------- #

#: Полный набор — как в neofetch: всё, что удалось выяснить.
NEOFETCH_FIELDS: tuple[Field, ...] = (
    Field("OS", operating_system),
    Field("Host", host),
    Field("Kernel", kernel),
    Field("Uptime", uptime),
    Field("Packages", packages),
    Field("Shell", shell),
    Field("Resolution", resolution),
    Field("DE", desktop_environment),
    Field("WM", window_manager),
    Field("WM Theme", wm_theme),
    Field("Theme", theme),
    Field("Icons", icons),
    Field("Terminal", terminal),
    Field("Terminal Font", terminal_font),
    Field("Font", font),
    Field("CPU", cpu),
    Field("GPU", gpu),
    Field("Memory", memory),
    Field("Swap", swap),
    Field("Disk", disk),
    Field("Battery", battery),
    Field("Local IP", local_ip),
    Field("Locale", locale),
)

#: То, что fastfetch собирает быстро: без тяжёлых внешних утилит.
FASTFETCH_FIELDS: tuple[Field, ...] = (
    Field("OS", operating_system),
    Field("Host", host),
    Field("Kernel", kernel_with_name),
    Field("Uptime", uptime),
    Field("Packages", packages),
    Field("Shell", shell),
    Field("Resolution", resolution),
    Field("DE", desktop_environment),
    Field("WM", window_manager),
    Field("Theme", theme),
    Field("Icons", icons),
    Field("Terminal", terminal),
    Field("CPU", cpu),
    Field("GPU", gpu),
    Field("Memory", memory),
    Field("Disk", disk),
    Field("Battery", battery),
    Field("Locale", locale),
)


def collect(
    fields: tuple[Field, ...] = NEOFETCH_FIELDS,
) -> list[tuple[str, str]]:
    """Последовательный сбор полей. Возвращает только непустые значения."""
    rows: list[tuple[str, str]] = []
    for field in fields:
        try:
            value = field.func()
        except Exception:
            value = ""
        value = " ".join(str(value).split()) if value else ""
        if value:
            rows.append((field.label, value))
    return rows


def collect_parallel(
    fields: tuple[Field, ...] = FASTFETCH_FIELDS,
    *,
    workers: int = 0,
) -> list[tuple[str, str]]:
    """Параллельный сбор полей (режим fastfetch). Порядок полей сохраняется."""
    from concurrent.futures import ThreadPoolExecutor

    if workers <= 0:
        workers = min(16, max(4, len(fields)))
    if len(fields) <= 1 or workers == 1:
        return collect(fields)

    results: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="fetch") as pool:
        futures = {pool.submit(field.func): field.label for field in fields}
        for future, label in futures.items():
            try:
                value = future.result()
            except Exception:
                value = ""
            value = " ".join(str(value).split()) if value else ""
            if value:
                results[label] = value

    return [(field.label, results[field.label]) for field in fields if field.label in results]
