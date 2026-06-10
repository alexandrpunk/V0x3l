#!/bin/bash
# ============================================================
# VoidForge v2 — Bootstrap entry point
# Instala dependencias y lanza VoidForge
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
echo "  ║              VoidForge v2 Initializing            ║"
echo "  ╚═══════════════════════════════════════════════════╝"
echo ""

# Verificar sistema
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "$ID" != "ubuntu" ] || [ "${VERSION_ID%%.*}" -lt 24 ]; then
        echo -e "  [ERR] Se requiere Ubuntu 24.04 o superior."
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
echo "  [..] Clonando: $REPO_URL (rama: $VOIDFORGE_BRANCH)"
echo "  [..] Destino: $INSTALL_DIR"
rm -rf "$INSTALL_DIR" 2>/dev/null || true
if ! git clone --depth 1 --branch "$VOIDFORGE_BRANCH" "$REPO_URL" "$INSTALL_DIR"; then
    echo -e "  [ERR] Error al descargar desde $REPO_URL (rama: $VOIDFORGE_BRANCH)."
    echo "  [ERR] Comando: git clone --depth 1 --branch $VOIDFORGE_BRANCH $REPO_URL $INSTALL_DIR"
    echo "  [ERR] Verifica tu conexion a internet y que la rama exista."
    exit 1
fi
echo -e "  [OK]  Descarga completada"

# Lanzar VoidForge
echo ""
echo -e "  Iniciando VoidForge..."
echo ""
cd "$INSTALL_DIR"
sudo python3 -m voidforge "$@"
