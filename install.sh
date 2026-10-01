#!/usr/bin/env bash
# Устанавливает конфиги Neofetch-Ai для настоящих neofetch и fastfetch.
#
#   ./install.sh                        # оба конфига в ~/.config
#   ./install.sh --config-home /dir     # в свой каталог вместо ~/.config
#   ./install.sh --dry-run              # показать, что куда пойдёт
#
# Существующие конфиги не удаляются, а сохраняются как config.conf.bak.<дата>.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_HOME="${XDG_CONFIG_HOME:-${HOME}/.config}"
DRY_RUN=0

while [ $# -gt 0 ]; do
    case "$1" in
        --config-home) shift; CONFIG_HOME="$1" ;;
        --dry-run)     DRY_RUN=1 ;;
        -h|--help)
            sed -n '2,9p' "${BASH_SOURCE[0]}"
            exit 0
            ;;
        *) echo "неизвестный аргумент: $1" >&2; exit 2 ;;
    esac
    shift
done

STAMP="$(date +%Y%m%d-%H%M%S)"

install_config() {
    local src="${REPO_DIR}/$1" dst="${CONFIG_HOME}/$2"
    if [ "$DRY_RUN" = 1 ]; then
        echo "dry-run: ${src} -> ${dst}"
        return
    fi
    mkdir -p "$(dirname "$dst")"
    if [ -e "$dst" ] && ! cmp -s "$src" "$dst"; then
        mv "$dst" "${dst}.bak.${STAMP}"
        echo "старый конфиг сохранён: ${dst}.bak.${STAMP}"
    fi
    cp "$src" "$dst"
    echo "установлено: ${dst}"
}

install_config neofetch/config.conf   neofetch/config.conf
install_config fastfetch/config.jsonc fastfetch/config.jsonc

if [ "$DRY_RUN" = 0 ]; then
    echo
    echo "Проверить:  neofetch   и   fastfetch"
    echo "Без установки: neofetch --config neofetch/config.conf"
    echo "               fastfetch --config fastfetch/config.jsonc"
fi
