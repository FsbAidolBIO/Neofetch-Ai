#!/usr/bin/env bash
# Установщик Neofetch-Ai.
#
#   ./install.sh                  # консольные команды neofetch-ai / fastfetch-ai
#   ./install.sh --configs        # конфиги для настоящих neofetch и fastfetch
#   ./install.sh --as-neofetch    # + короткие имена neofetch и fastfetch
#   ./install.sh --prefix /dir    # каталог для команд, по умолчанию ~/.local/bin
#
# Флаги можно комбинировать: ./install.sh --configs --as-neofetch
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="${HOME}/.local/bin"
SHORT_NAMES=0
INSTALL_CONFIGS=0
INSTALL_WRAPPERS=1

while [ $# -gt 0 ]; do
    case "$1" in
        --as-neofetch) SHORT_NAMES=1 ;;
        --configs)     INSTALL_CONFIGS=1; INSTALL_WRAPPERS=0 ;;
        --prefix)      shift; PREFIX="$1" ;;
        -h|--help)
            sed -n '2,10p' "${BASH_SOURCE[0]}"
            exit 0
            ;;
        *) echo "неизвестный аргумент: $1" >&2; exit 2 ;;
    esac
    shift
done

# ── консольные команды ──────────────────────────────────────────────────────
make_wrapper() {
    local name="$1" script="$2"
    cat > "${PREFIX}/${name}" <<EOF
#!/usr/bin/env bash
exec "$(command -v python3)" "${REPO_DIR}/${script}" "\$@"
EOF
    chmod +x "${PREFIX}/${name}"
    echo "установлено: ${PREFIX}/${name}"
}

if [ "$INSTALL_WRAPPERS" = 1 ]; then
    mkdir -p "$PREFIX"
    make_wrapper neofetch-ai neofetch.py
    make_wrapper fastfetch-ai fastfetch.py

    if [ "$SHORT_NAMES" = 1 ]; then
        make_wrapper neofetch neofetch.py
        make_wrapper fastfetch fastfetch.py
        echo
        echo "Внимание: имена neofetch/fastfetch перекрывают одноимённые пакеты,"
        echo "если они установлены. Удалить: rm ${PREFIX}/neofetch ${PREFIX}/fastfetch"
    fi

    case ":${PATH}:" in
        *":${PREFIX}:"*) ;;
        *) echo; echo "Добавьте ${PREFIX} в PATH: export PATH=\"${PREFIX}:\$PATH\"" ;;
    esac
fi

# ── конфиги для настоящих neofetch и fastfetch ──────────────────────────────
if [ "$INSTALL_CONFIGS" = 1 ]; then
    CONFIG_HOME="${XDG_CONFIG_HOME:-${HOME}/.config}"
    STAMP="$(date +%Y%m%d-%H%M%S)"

    install_config() {
        local src="${REPO_DIR}/$1" dst="$2"
        mkdir -p "$(dirname "$dst")"
        if [ -e "$dst" ] && ! cmp -s "$src" "$dst"; then
            mv "$dst" "${dst}.bak.${STAMP}"
            echo "старый конфиг сохранён: ${dst}.bak.${STAMP}"
        fi
        cp "$src" "$dst"
        echo "установлено: $dst"
    }

    install_config neofetch/config.conf  "${CONFIG_HOME}/neofetch/config.conf"
    install_config fastfetch/config.jsonc "${CONFIG_HOME}/fastfetch/config.jsonc"

    echo
    echo "Проверить: neofetch   и   fastfetch"
fi
