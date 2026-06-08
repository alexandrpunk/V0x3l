#!/bin/bash
# ============================================================
# VoidForge — Boot entry point (curl URL | bash)
# Clona el repositorio y ejecuta voidforge.sh
# ============================================================
#
# Uso:
#   curl -fsSL https://raw.githubusercontent.com/alexandrpunk/VoidForge/main/install.sh | bash
# ============================================================

set -euo pipefail

REPO_URL="https://github.com/alexandrpunk/VoidForge.git"
INSTALL_DIR="${HOME}/.local/share/voidforge"

echo ""
echo "  ╔═══════════════════════════════════════════════════╗"
echo "  ║              VoidForge Installer                  ║"
echo "  ╚═══════════════════════════════════════════════════╝"
echo ""

# Verificar que es Ubuntu 24.04+
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "$ID" != "ubuntu" ] || [ "${VERSION_ID%%.*}" -lt 24 ]; then
        echo "❌ Se requiere Ubuntu 24.04 o superior."
        exit 1
    fi
fi

# Instalar git si no está
if ! command -v git &>/dev/null; then
    sudo apt-get update -qq
    sudo apt-get install -y -qq git
fi

# Clonar repositorio
echo "📦 Clonando VoidForge..."
rm -rf "$INSTALL_DIR"
git clone --depth 1 "$REPO_URL" "$INSTALL_DIR" 2>/dev/null

if [ ! -f "$INSTALL_DIR/voidforge.sh" ]; then
    echo "❌ Error al clonar el repositorio."
    exit 1
fi

echo "🚀 Iniciando VoidForge..."
cd "$INSTALL_DIR"
sudo bash voidforge.sh "$@"
