#!/bin/bash
# ============================================================
# VoidForge — Boot entry point (curl URL | bash)
# Clona el repositorio y ejecuta voidforge.sh
# ============================================================
#
# Uso:
#   curl -fsSL https://raw.githubusercontent.com/alexandrpunk/VoidForge/refactor/install.sh | bash
# ============================================================

set -euo pipefail

REPO_URL="https://github.com/alexandrpunk/VoidForge.git"
INSTALL_DIR="${HOME}/.local/share/voidforge"
VOIDFORGE_BRANCH="${VOIDFORGE_BRANCH:-refactor}"

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
echo "📦 Clonando VoidForge (rama: $VOIDFORGE_BRANCH)..."
rm -rf "$INSTALL_DIR" 2>/dev/null || true
if ! git clone --depth 1 --branch "$VOIDFORGE_BRANCH" "$REPO_URL" "$INSTALL_DIR" 2>&1; then
    echo "❌ Error al clonar el repositorio desde $REPO_URL (rama: $VOIDFORGE_BRANCH)."
    echo "   Verifica tu conexión a internet e intenta de nuevo."
    echo ""
    echo "   También puedes clonar manualmente:"
    echo "   git clone --branch $VOIDFORGE_BRANCH $REPO_URL && cd VoidForge && sudo bash voidforge.sh"
    exit 1
fi

echo "🚀 Iniciando VoidForge..."
cd "$INSTALL_DIR"
sudo bash voidforge.sh "$@"
