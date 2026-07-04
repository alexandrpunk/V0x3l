#!/bin/bash
# ============================================================
# V0x3l — Bootstrap entry point
# ============================================================
# Uso:
#   curl -fsSL https://raw.githubusercontent.com/alexandrpunk/V0x3l/development/install.sh | bash
# ============================================================

set -euo pipefail

REPO_URL="https://github.com/alexandrpunk/V0x3l.git"
INSTALL_DIR="${HOME}/.local/share/v0x3l"
V0X3L_BRANCH="${V0X3L_BRANCH:-development}"

# ── Spinner y mensajes ──
SPINNER_PID=""
MESSAGES=(
    "Forjando el vacío..."
    "Despertando V0x3l del abismo..."
    "Invocando entidades del sistema..."
    "Cargando la matriz oscura..."
    "Construyendo puentes al vacío..."
)
MSG_IDX=0

spinner() {
    local chars=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")
    local idx=0
    while true; do
        local msg="${MESSAGES[$((MSG_IDX % ${#MESSAGES[@]}))]}"
        printf "\r  \e[36m%s\e[0m \e[33m%s\e[0m\e[K" "${chars[$idx]}" "$msg"
        idx=$(( (idx + 1) % ${#chars[@]} ))
        sleep 0.1
    done
}

start_spinner() {
    spinner &
    SPINNER_PID=$!
}

stop_spinner() {
    if [ -n "$SPINNER_PID" ]; then
        kill "$SPINNER_PID" 2>/dev/null || true
        wait "$SPINNER_PID" 2>/dev/null || true
        SPINNER_PID=""
    fi
    printf "\r  \e[K" 2>/dev/null || true
    echo ""
}

rotate_msg() {
    MSG_IDX=$((MSG_IDX + 1))
}

cleanup_spinner() {
    stop_spinner
    printf "\r  \e[31m[ERR]\e[0m Instalacion interrumpida\n"
}
trap cleanup_spinner EXIT

echo ""
echo "  ╔═══════════════════════════════════════════════════╗"
echo "  ║              V0x3l Initializing                   ║"
echo "  ╚═══════════════════════════════════════════════════╝"
echo ""

# Verificar sistema
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "$ID" != "ubuntu" ] || [ "${VERSION_ID%%.*}" -lt 26 ]; then
        trap - EXIT
        stop_spinner
        echo -e "  [ERR] Se requiere Ubuntu 26.04 o superior."
        exit 1
    fi
    echo -e "  [OK]  Ubuntu ${VERSION_ID}"
fi

# Instalar git
if ! command -v git &>/dev/null; then
    rotate_msg
    start_spinner
    if sudo apt-get update -qq > /dev/null 2>&1 && sudo apt-get install -y -qq git > /dev/null 2>&1; then
        stop_spinner
        echo -e "  [OK]  Git listo"
        rotate_msg
    else
        stop_spinner
        echo -e "  [ERR] No se pudo instalar git."
        trap - EXIT
        exit 1
    fi
else
    echo -e "  [OK]  Git listo"
fi

# Clonar repositorio
echo "  [..] Clonando: $REPO_URL (rama: $V0X3L_BRANCH)"
echo "  [..] Destino: $INSTALL_DIR"
rotate_msg
start_spinner
sudo rm -rf "$INSTALL_DIR" 2>/dev/null
rm -rf "$INSTALL_DIR" 2>/dev/null
mkdir -p "$(dirname "$INSTALL_DIR")" 2>/dev/null || true
if git clone --depth 1 --branch "$V0X3L_BRANCH" "$REPO_URL" "$INSTALL_DIR"; then
    stop_spinner
    echo -e "  [OK]  Descarga completada"
    rotate_msg
else
    stop_spinner
    echo -e "  [ERR] Error al descargar desde $REPO_URL (rama: $V0X3L_BRANCH)."
    echo "  [ERR] Verifica tu conexion a internet y que la rama exista."
    trap - EXIT
    exit 1
fi

# Instalar python3-urwid
if ! python3 -c "import urwid" 2>/dev/null; then
    rotate_msg
    start_spinner
    if sudo apt-get install -y python3-urwid > /dev/null 2>&1; then
        if python3 -c "import urwid" 2>/dev/null; then
            stop_spinner
            echo -e "  [OK]  python3-urwid instalado"
            rotate_msg
        else
            stop_spinner
            echo -e "  [WARN] No se pudo instalar python3-urwid."
        fi
    else
        stop_spinner
        echo -e "  [WARN] No se pudo instalar python3-urwid."
    fi
else
    echo -e "  [OK]  python3-urwid"
fi

cleanup() {
    cd /tmp 2>/dev/null || true
    sudo rm -rf "${INSTALL_DIR}" 2>/dev/null || true
    trap - EXIT
    stop_spinner
}

echo ""
echo -e "  Iniciando V0x3l..."
echo ""
trap cleanup EXIT
cd "$INSTALL_DIR"
sudo python3 -m v0x3l "$@" < /dev/tty
