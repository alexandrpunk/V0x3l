#!/bin/bash
# ============================================================
# VoidForge — Boot entry point (curl URL | bash)
# Clona el repositorio y ejecuta voidforge.sh
# ============================================================
#
# Uso:
#   curl -fsSL https://raw.githubusercontent.com/alexandrpunk/VoidForge/refactor/install.sh | bash
# ============================================================

REPO_URL="https://github.com/alexandrpunk/VoidForge.git"
INSTALL_DIR="${HOME}/.local/share/voidforge"
VOIDFORGE_BRANCH="${VOIDFORGE_BRANCH:-refactor}"
TEMP_LOG="/tmp/voidforge-bootstrap.log"

# ── Pantalla de inicialización ──
init_screen() {
    clear
    echo ""
    echo "  ╔═══════════════════════════════════════════════════╗"
    echo "  ║              VoidForge Initializing               ║"
    echo "  ╚═══════════════════════════════════════════════════╝"
    echo ""
}

step_ok()   { echo -e "  \033[1;32m[OK]\033[0m $1"; }
step_fail() { echo -e "  \033[1;31m[ERR]\033[0m $1"; }
step_doing(){ echo -e "  \033[1;36m[..]\033[0m $1"; }

# ── Paso 1: Verificar sistema ──
step_doing "Verificando sistema"
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "$ID" != "ubuntu" ] || [ "${VERSION_ID%%.*}" -lt 24 ]; then
        step_fail "Verificando sistema"
        echo -e "\n  \033[1;31mSe requiere Ubuntu 24.04 o superior.\033[0m"
        exit 1
    fi
fi
step_ok "Verificando sistema"

# ── Paso 2: Git ──
step_doing "Preparando entorno"
if ! command -v git &>/dev/null; then
    sudo apt-get update -qq > "$TEMP_LOG" 2>&1
    sudo apt-get install -y -qq git >> "$TEMP_LOG" 2>&1
fi
step_ok "Preparando entorno"

# ── Paso 3: Clonar repositorio ──
step_doing "Descargando VoidForge"
rm -rf "$INSTALL_DIR" 2>/dev/null || true
if ! git clone --depth 1 --branch "$VOIDFORGE_BRANCH" "$REPO_URL" "$INSTALL_DIR" > "$TEMP_LOG" 2>&1; then
    step_fail "Descargando VoidForge"
    echo -e "\n  \033[1;31mError al descargar.\033[0m"
    echo "  Verifica tu conexión."
    exit 1
fi
step_ok "Descargando VoidForge"

# ── Lanzar voidforge.sh ──
echo ""
echo -e "  \033[1;36mIniciando VoidForge...\033[0m"
echo ""
cd "$INSTALL_DIR"
sudo bash voidforge.sh "$@"
