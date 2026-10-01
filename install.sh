#!/usr/bin/env bash
# Устанавливает neofetch и fastfetch из этого репозитория в ~/.local/bin.
#
#   ./install.sh                  # команды neofetch-ai и fastfetch-ai
#   ./install.sh --as-neofetch    # + короткие имена neofetch и fastfetch
#   ./install.sh --prefix /dir    # каталог по умолчанию ~/.local/bin
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="${HOME}/.local/bin"
SHORT_NAMES=0

while [ $# -gt 0 ]; do
    case "$1" in
        --as-neofetch) SHORT_NAMES=1 ;;
        --prefix)      shift; PREFIX="$1" ;;
        -h|--help)
            sed -n '2,7p' "${BASH_SOURCE[0]}"
            exit 0
            ;;
        *) echo "неизвестный аргумент: $1" >&2; exit 2 ;;
    esac
    shift
done

mkdir -p "$PREFIX"
PYTHON="$(command -v python3)"

make_wrapper() {
    local name="$1" script="$2"
    cat > "${PREFIX}/${name}" <<EOF
#!/usr/bin/env bash
exec "${PYTHON}" "${REPO_DIR}/${script}" "\$@"
EOF
    chmod +x "${PREFIX}/${name}"
    echo "установлено: ${PREFIX}/${name}"
}

make_wrapper neofetch-ai neofetch.py
make_wrapper fastfetch-ai fastfetch.py

if [ "$SHORT_NAMES" = 1 ]; then
    make_wrapper neofetch neofetch.py
    make_wrapper fastfetch fastfetch.py
    echo
    echo "Внимание: имена neofetch/fastfetch перекрывают одноимённые пакеты,"
    echo "если они установлены. Удалить можно так: rm ${PREFIX}/neofetch ${PREFIX}/fastfetch"
fi

case ":${PATH}:" in
    *":${PREFIX}:"*) ;;
    *) echo; echo "Добавьте ${PREFIX} в PATH: export PATH=\"${PREFIX}:\$PATH\"" ;;
esac
