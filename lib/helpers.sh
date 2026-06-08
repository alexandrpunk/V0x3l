# ============================================================
# VoidForge — Helper functions
# ============================================================

export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a

root() {
    if [ "$EUID" -eq 0 ]; then
        "$@"
    else
        sudo "$@"
    fi
}

log_to_file() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

run_cmd() {
    local desc="$1"
    shift
    log_to_file "CMD: $*"
    "$@" >>"$LOG_FILE" 2>&1
}

log_step() {
    local num=$1 total=$2 desc=$3
    CURRENT_STEP_NUM=$num
    log_to_file "=== Paso $num/$total: $desc ==="
    echo -e "\n${C_CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RESET}"
    echo -e "${C_CYAN}[$num/$total] $desc${C_RESET}"
    echo -e "${C_CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RESET}\n"
}

log_ok()   { log_to_file "OK: $1";   echo -e "${C_GREEN}   [OK] $1${C_RESET}"; }
log_skip() { log_to_file "SKIP: $1"; echo -e "${C_YELLOW}   [--] $1${C_RESET}"; }
log_warn() { log_to_file "WARN: $1"; echo -e "${C_YELLOW}   [!] $1${C_RESET}"; }
log_error(){ log_to_file "ERROR: $1";echo -e "${C_RED}   [ERR] $1${C_RESET}"; }
log_info() { log_to_file "INFO: $1"; echo -e "${C_GRAY}   [i] $1${C_RESET}"; }

SPINNER_PID=""
SPINNER_MSG=""

start_spinner() {
    SPINNER_MSG="${1:-Trabajando...}"
    local bar_width=20 pos=0
    tput civis 2>/dev/null || true
    while true; do
        local filled="" empty=""
        for ((j=0; j<pos; j++)); do filled+="="; done
        for ((j=pos; j<bar_width; j++)); do empty+="-"; done
        printf "\r   ${C_CYAN}[%s%s]${C_RESET} %s" "$filled" "$empty" "$SPINNER_MSG"
        pos=$(( (pos + 1) % (bar_width + 1) ))
        sleep 0.12
    done
}

stop_spinner() {
    if [ -n "$SPINNER_PID" ]; then
        kill "$SPINNER_PID" 2>/dev/null || true
        wait "$SPINNER_PID" 2>/dev/null || true
        SPINNER_PID=""
        printf "\r%*s\r" 70 ""
        tput cnorm 2>/dev/null || true
    fi
}

spin()   { start_spinner "$1" & SPINNER_PID=$!; }
nospin() { stop_spinner; }

error_handler() {
    local exit_code=$1 line_no=$2 command="$3"
    nospin 2>/dev/null || true
    log_error "Error en linea $line_no: $command (codigo $exit_code)"
    log_to_file "FATAL: linea $line_no, comando: $command, exit: $exit_code"
    log_to_file "Revisa el log completo: $LOG_FILE"
    echo -e "\n${C_RED}   Log de errores: $LOG_FILE${C_RESET}\n"
    exit "$exit_code"
}

trap 'nospin 2>/dev/null || true' EXIT
trap 'error_handler $? $LINENO "$BASH_COMMAND"' ERR

save_checkpoint()    { echo "$1" > "$CHECKPOINT_FILE"; }
load_checkpoint()    { [ -f "$CHECKPOINT_FILE" ] && cat "$CHECKPOINT_FILE"; }
clear_checkpoint()   { rm -f "$CHECKPOINT_FILE"; }

is_step_skipped() {
    local step=$1
    [[ "$SKIP_STEPS" =~ (^|,)$step(,|$) ]]
}

should_run_step() {
    local step=$1
    if is_step_skipped "$step"; then
        log_skip "Paso $step omitido por --skip"
        return 1
    fi
    return 0
}

run_step() {
    local step_num=$1
    local step_func="step_$step_num"
    if declare -f "$step_func" >/dev/null 2>&1; then
        "$step_func"
    else
        log_error "Paso $step_num no encontrado"
    fi
}

run_all_steps() {
    for i in $(seq 0 "$TOTAL_STEPS"); do
        run_step "$i"
    done
    clear_checkpoint
    print_summary
}

print_summary() {
    clear
    echo -e "\n${C_CYAN}╔════════════════════════════════════════════════════════════════╗${C_RESET}"
    echo -e "${C_CYAN}║${C_WHITE}                   ¡Instalación completada!                      ${C_CYAN}║${C_RESET}"
    echo -e "${C_CYAN}╚════════════════════════════════════════════════════════════════╝${C_RESET}\n"
    echo -e "${C_GREEN}[OK] Todos los pasos completados${C_RESET}\n"
    echo -e "${C_WHITE}Cambios realizados:${C_RESET}"
    echo -e "  + Kernel: XanMod Edge"
    echo -e "  + Wayland + Nautilus + PipeWire"
    echo -e "  + Flatpak con Flathub + Apps Papers, Resources, Showtime"
    echo -e "  + Oh My Zsh + tema agnoster"
    echo -e "  + Nerd Fonts: fonts-powerline"
    echo -e "  + Iconos: Colloid catppuccin green"
    echo -e "  + Temas: Plymouth + GRUB Vimix"
    echo -e "  + Firewall: UFW activo deny incoming"
    echo -e "  + TLP configurado para laptops"
    echo -e "  + DMS (Dank Linux)"
    if [ "$HAS_NVIDIA_GPU" -eq 1 ]; then
        echo -e "  + Drivers NVIDIA + parametros kernel DRM/KMS"
    fi
    echo -e "\n${C_YELLOW}[!] Importante:${C_RESET}"
    echo -e "  + Si se instalo XanMod Edge, ${C_RED}requiere reiniciar${C_RESET} para aplicar el nuevo kernel"
    echo -e "  + Si se instalaron drivers NVIDIA, ${C_RED}requiere reiniciar${C_RESET} para aplicar DRM/KMS"
    echo -e "\n${C_WHITE}Comandos utiles:${C_RESET}"
    echo -e "  ${C_GRAY}sudo reboot${C_RESET}              - Reiniciar para aplicar cambios"
    echo -e "  ${C_GRAY}prime-run <app>${C_RESET}         - Usar GPU NVIDIA en sistema hibrido"
    echo -e "  ${C_GRAY}tlp start${C_RESET}               - Iniciar TLP manualmente"
    echo -e "  ${C_GRAY}tlp-stat${C_RESET}                - Ver estado de ahorro de energia"
    echo -e "  ${C_GRAY}ufw status${C_RESET}               - Ver estado del firewall"
    echo -e "  ${C_GRAY}flatpak list${C_RESET}            - Ver aplicaciones Flatpak instaladas"
    echo -e "\n${C_GRAY}Log completo: $LOG_FILE${C_RESET}"
    echo -e "\n${C_GREEN}Tu sistema esta listo!${C_RESET}\n"
}

check_system() {
    local OS_ID="" OS_VERSION=""
    if [ -f /etc/os-release ]; then
        OS_ID=$(grep '^ID=' /etc/os-release | cut -d= -f2 | tr -d '"')
        OS_VERSION=$(grep '^VERSION_ID=' /etc/os-release | cut -d= -f2 | tr -d '"')
    fi
    if [ "$OS_ID" = "ubuntu" ]; then
        OS_MAJOR=$(echo "$OS_VERSION" | cut -d. -f1)
        if [ "$OS_MAJOR" -ge 24 ]; then
            log_info "Sistema detectado: Ubuntu $OS_VERSION"
            return 0
        else
            log_error "Ubuntu $OS_VERSION no es compatible. Se requiere Ubuntu 24.04 o superior"
            return 1
        fi
    elif [ -n "$OS_ID" ]; then
        log_error "Sistema no compatible: $OS_ID. Este script es solo para Ubuntu 24.04+"
        return 1
    else
        log_error "No se pudo detectar el sistema operativo"
        return 1
    fi
}

ensure_sudo() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "\n${C_YELLOW}VoidForge requiere permisos de administrador.${C_RESET}"
        echo -ne "${C_WHITE}Contraseña de sudo: ${C_RESET}"
        if ! sudo -v; then
            echo -e "${C_RED}No se pudo obtener permisos sudo${C_RESET}"
            exit 1
        fi
        echo ""
    fi
}
