#!/bin/bash
# ============================================================
# VoidForge v2 — Bootstrap entry point (curl URL | bash)
# Instala dependencias Python y lanza VoidForge
# ============================================================
#
# Uso:
#   curl -fsSL https://raw.githubusercontent.com/alexandrpunk/VoidForge/python-urwid/install.sh | bash
# ============================================================

set -euo pipefail

REPO_URL="https://github.com/alexandrpunk/VoidForge.git"
INSTALL_DIR="${HOME}/.local/share/voidforge"
VOIDFORGE_BRANCH="${VOIDFORGE_BRANCH:-python-urwid}"

echo ""
echo "  ╔═══════════════════════════════════════════════════╗"
echo "  ║              VoidForge v2 Initializing            ║"
echo "  ╚═══════════════════════════════════════════════════╝"
echo ""

# ── Verificar sistema ──
echo "  [..] Verificando sistema"
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "$ID" != "ubuntu" ] || [ "${VERSION_ID%%.*}" -lt 24 ]; then
        echo -e "  [ERR] Se requiere Ubuntu 24.04 o superior."
        exit 1
    fi
fi
echo -e "  [OK]  Ubuntu ${VERSION_ID}"

# ── Instalar git ──
if ! command -v git &>/dev/null; then
    echo "  [..] Instalando git..."
    sudo apt-get update -qq > /dev/null 2>&1
    sudo apt-get install -y -qq git > /dev/null 2>&1
fi
echo -e "  [OK]  Git listo"

# ── Clonar repositorio ──
echo "  [..] Descargando VoidForge (rama: $VOIDFORGE_BRANCH)..."
rm -rf "$INSTALL_DIR" 2>/dev/null || true
if ! git clone --depth 1 --branch "$VOIDFORGE_BRANCH" "$REPO_URL" "$INSTALL_DIR" > /dev/null 2>&1; then
    echo -e "  [ERR] Error al descargar."
    echo "   Verifica tu conexion a internet."
    exit 1
fi
echo -e "  [OK]  Descarga completada"

# ── Instalar python3-urwid ──
if ! python3 -c "import urwid" 2>/dev/null; then
    echo "  [..] Instalando python3-urwid..."
    sudo apt-get install -y -qq python3-urwid > /dev/null 2>&1 || \
        pip3 install --break-system-packages urwid > /dev/null 2>&1 || true
fi
echo -e "  [OK]  Dependencias Python listas"

# ── Lanzar VoidForge ──
echo ""
echo -e "  Iniciando VoidForge..."
echo ""
cd "$INSTALL_DIR"
sudo python3 -m voidforge "$@"
