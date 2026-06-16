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

echo ""
echo "  ╔═══════════════════════════════════════════════════╗"
echo "  ║              V0x3l Initializing                   ║"
echo "  ╚═══════════════════════════════════════════════════╝"
echo ""

# Verificar sistema
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "$ID" != "ubuntu" ] || [ "${VERSION_ID%%.*}" -lt 26 ]; then
        echo -e "  [ERR] Se requiere Ubuntu 26.04 o superior."
        exit 1
    fi
fi
echo -e "  [OK]  Ubuntu ${VERSION_ID}"

# Instalar git
if ! command -v git &>/dev/null; then
    sudo apt-get update -qq > /dev/null 2>&1
    sudo apt-get install -y -qq git > /dev/null 2>&1
fi
echo -e "  [OK]  Git listo"

# Clonar repositorio
echo "  [..] Clonando: $REPO_URL (rama: $V0X3L_BRANCH)"
echo "  [..] Destino: $INSTALL_DIR"
sudo rm -rf "$INSTALL_DIR" 2>/dev/null
rm -rf "$INSTALL_DIR" 2>/dev/null
mkdir -p "$(dirname "$INSTALL_DIR")" 2>/dev/null || true
if ! git clone --depth 1 --branch "$V0X3L_BRANCH" "$REPO_URL" "$INSTALL_DIR"; then
    echo -e "  [ERR] Error al descargar desde $REPO_URL (rama: $V0X3L_BRANCH)."
    echo "  [ERR] Verifica tu conexion a internet y que la rama exista."
    exit 1
fi
echo -e "  [OK]  Descarga completada"

# Instalar python3-urwid
if ! python3 -c "import urwid" 2>/dev/null; then
    echo "  [..] Instalando python3-urwid..."
    sudo apt-get install -y python3-urwid > /dev/null 2>&1
    if python3 -c "import urwid" 2>/dev/null; then
        echo -e "  [OK]  python3-urwid instalado"
    else
        echo -e "  [WARN] No se pudo instalar python3-urwid."
    fi
else
    echo -e "  [OK]  python3-urwid"
fi

cleanup() {
    cd /tmp 2>/dev/null || true
    sudo rm -rf "${INSTALL_DIR}" 2>/dev/null || true
}
trap cleanup EXIT

echo ""
echo -e "  Iniciando V0x3l..."
echo ""
cd "$INSTALL_DIR"
sudo python3 -m v0x3l "$@" < /dev/tty
