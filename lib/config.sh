# ============================================================
# VoidForge — Configuración global
# ============================================================

VERSION="1.0.0"
REAL_USER="${SUDO_USER:-$USER}"
HOME_DIR="/home/$REAL_USER"
CHECKPOINT_FILE="/tmp/voidforge-progress"
LOG_FILE="/tmp/voidforge.log"
SKIP_STEPS="${SKIP_STEPS:-}"
RESUME="${RESUME:-false}"

TOTAL_STEPS=15

# Colores
C_RESET="\033[0m"
C_CYAN="\033[1;36m"
C_GREEN="\033[1;32m"
C_YELLOW="\033[1;33m"
C_RED="\033[1;31m"
C_GRAY="\033[3;37m"
C_WHITE="\033[1;37m"
C_BLUE="\033[1;34m"

CURRENT_STEP_NUM=0
HAS_NVIDIA_GPU=0
PLYMOUTH_THEME_NAME="voidforge-boot-theme"
PLYMOUTH_THEME_SRC="$SCRIPT_DIR/assets/themes/voidforge-boot-theme"
PLYMOUTH_ZIP_NAME="ubuntu-mac-style.zip"
PLYMOUTH_ZIP_URL="https://raw.githubusercontent.com/alexandrpunk/VoidForge/main/voidforge-boot-theme.zip"
