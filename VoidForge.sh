#!/bin/bash
# ============================================================
# VoidForge — Script de Post-Instalación para Ubuntu Server
# Gestor: Nala | Base: Wayland + Nautilus + Flatpak
# Objetivo: Configurar base, Plymouth, DMS y optimizar hardware
# ============================================================
#
# Instalación desde GitHub:
#   curl -fsSL URL -o /tmp/VoidForge.sh && sudo bash /tmp/VoidForge.sh
#
# O en una sola línea:
#   curl -fsSL URL | sudo bash
#
# ============================================================

set -euo pipefail

# ============================================================
# CONFIGURACIÓN Y VARIABLES GLOBALES
# ============================================================

VERSION="1.0.0"
REAL_USER="${SUDO_USER:-$USER}"
HOME_DIR="/home/$REAL_USER"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-.}")" 2>/dev/null && pwd)" || SCRIPT_DIR="$(pwd)"
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

# Número de paso actual (para progreso)
CURRENT_STEP_NUM=0

# Flag NVIDIA detectada
HAS_NVIDIA_GPU=0

# Configuración tema Plymouth
PLYMOUTH_ZIP_NAME="ubuntu-mac-style.zip"
PLYMOUTH_ZIP_URL="https://raw.githubusercontent.com/alexandrpunk/VoidForge/main/voidforge-boot-theme.zip"

# ============================================================
# FUNCIONES HELPER
# ============================================================

root() {
    if [ "$EUID" -eq 0 ]; then
        "$@"
    else
        sudo "$@"
    fi
}

print_banner() {
    clear
    echo -e "${C_CYAN}"
    cat <<'ASCII'
  ╔══════════════════════════════════════════════════════════════╗
  ║                                                              ║
  ║  __      __   _     _ ______                         _       ║
  ║  \ \    / /  (_)   | |  ____|                       | |      ║
  ║   \ \  / /__  _  __| | |__ ___  _ __ __ _  ___   ___| |__    ║
  ║    \ \/ / _ \| |/ _` |  __/ _ \| '__/ _` |/ _ \ / __| '_ \   ║
  ║     \  / (_) | | (_| | | | (_) | | | (_| |  __/_\__ \ | | |  ║
  ║      \/ \___/|_|\__,_|_|  \___/|_|  \__, |\___(_)___/_| |_|  ║
  ║                                      __/ |                   ║
  ║                                     |___/                    ║
  ║                                                              ║
  ║              Tu sistema. Tus reglas. Tu forja.               ║
  ║                                                              ║
  ╚══════════════════════════════════════════════════════════════╝
ASCII
    echo -e "${C_GRAY}                      v${VERSION}${C_RESET}"
    echo ""
}

log_step() {
    local num=$1
    local total=$2
    local desc=$3
    CURRENT_STEP_NUM=$num
    log_to_file "=== Paso $num/$total: $desc ==="
    echo -e "\n${C_CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RESET}"
    echo -e "${C_CYAN}[$num/$total] $desc${C_RESET}"
    echo -e "${C_CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RESET}\n"
}

log_ok() {
    log_to_file "OK: $1"
    echo -e "${C_GREEN}   ✅ $1${C_RESET}"
}

log_skip() {
    log_to_file "SKIP: $1"
    echo -e "${C_YELLOW}   ⏭️ $1${C_RESET}"
}

log_warn() {
    log_to_file "WARN: $1"
    echo -e "${C_YELLOW}   ⚠️ $1${C_RESET}"
}

log_error() {
    log_to_file "ERROR: $1"
    echo -e "${C_RED}   ❌ $1${C_RESET}"
}

log_info() {
    log_to_file "INFO: $1"
    echo -e "${C_GRAY}   ℹ️  $1${C_RESET}"
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

SPINNER_PID=""
SPINNER_MSG=""

start_spinner() {
    SPINNER_MSG="${1:-Trabajando...}"
    local bar_width=20
    local pos=0
    tput civis 2>/dev/null || true
    while true; do
        local filled=""
        local empty=""
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

spin() {
    start_spinner "$1" &
    SPINNER_PID=$!
}

nospin() {
    stop_spinner
}

error_handler() {
    local exit_code=$1
    local line_no=$2
    local command="$3"
    nospin 2>/dev/null || true
    log_error "Error en linea $line_no: $command (codigo $exit_code)"
    log_to_file "FATAL: linea $line_no, comando: $command, exit: $exit_code"
    log_to_file "Revisa el log completo: $LOG_FILE"
    echo -e "\n${C_RED}   Log de errores: $LOG_FILE${C_RESET}\n"
    exit "$exit_code"
}

trap 'nospin 2>/dev/null || true' EXIT
trap 'error_handler $? $LINENO "$BASH_COMMAND"' ERR

save_checkpoint() {
    echo "$1" > "$CHECKPOINT_FILE"
}

load_checkpoint() {
    if [ -f "$CHECKPOINT_FILE" ]; then
        cat "$CHECKPOINT_FILE"
    fi
}

clear_checkpoint() {
    rm -f "$CHECKPOINT_FILE"
}

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

# ============================================================
# FUNCIONES DE PASOS
# ============================================================

step_0() {
    echo "[DEBUG] step_0 entered" >&2
    should_run_step 0 || return 0
    log_step 0 "$TOTAL_STEPS" "Instalando herramientas base"

    spin "Instalando herramientas base..."
    run_cmd "apt update" root apt update || true
    run_cmd "apt install base" root apt install -y nala wget tar unzip file zsh git curl ca-certificates pciutils locales gnupg software-properties-common || true
    nospin
    log_ok "Herramientas base instaladas (nala, wget, git, curl, zsh, pciutils, locales)"
    save_checkpoint 0
}

step_1() {
    should_run_step 1 || return 0
    log_step 1 "$TOTAL_STEPS" "Configurando repositorios y sistema base"

    # ButterRepo
    if [ ! -f /etc/apt/sources.list.d/butterrepo.list ]; then
        spin "Agregando ButterRepo..."
        curl -fsSL https://justaguylinux.codeberg.page/butterrepo/key.asc | root gpg --dearmor -o /usr/share/keyrings/butterrepo.gpg >>"$LOG_FILE" 2>&1 || true
        echo "deb [arch=amd64 signed-by=/usr/share/keyrings/butterrepo.gpg] https://justaguylinux.codeberg.page/butterrepo stable main" | root tee /etc/apt/sources.list.d/butterrepo.list >>"$LOG_FILE" 2>&1 || true
        nospin
        log_ok "ButterRepo agregado"
    else
        log_skip "ButterRepo ya existe"
    fi

    # Update y upgrade
    spin "Actualizando sistema..."
    run_cmd "nala update" root nala update || true
    run_cmd "nala upgrade" root nala upgrade -y || true
    nospin
    log_ok "Sistema actualizado"

    # Grupos
    root usermod -aG video,render,audio,plugdev,netdev "$REAL_USER" >>"$LOG_FILE" 2>&1 || true
    log_ok "Usuario agregado a grupos"

    # Timezone
    if [ "$(timedatectl show -p Timezone --value)" != "America/Mazatlan" ]; then
        root timedatectl set-timezone America/Mazatlan || true
        log_ok "Zona horaria: America/Mazatlan"
    else
        log_skip "Zona horaria ya configurada"
    fi

    # Locale
    if ! locale -a 2>/dev/null | grep -q "es_MX.utf8"; then
        root sed -i 's/^# *es_MX\.UTF-8 UTF-8/es_MX.UTF-8 UTF-8/' /etc/locale.gen || true
        run_cmd "locale-gen" root locale-gen || true
    fi
    if [ "$(grep ^LANG= /etc/default/locale 2>/dev/null | cut -d= -f2)" != "es_MX.UTF-8" ]; then
        root update-locale LANG=es_MX.UTF-8 || true
        log_ok "Locale: es_MX.UTF-8"
    else
        log_skip "Locale ya configurado"
    fi

    save_checkpoint 1
}

step_2() {
    should_run_step 2 || return 0
    log_step 2 "$TOTAL_STEPS" "Instalando Kernel XanMod"

    # Agregar repo XanMod
    if [ ! -f /etc/apt/sources.list.d/xanmod-release.list ]; then
        spin "Agregando repositorio XanMod..."
        run_cmd "nala install lsb-release" root nala install --no-install-recommends -y lsb-release || true
        wget -qO - https://dl.xanmod.org/archive.key | root gpg --dearmor -vo /etc/apt/keyrings/xanmod-archive-keyring.gpg >>"$LOG_FILE" 2>&1 || true
        echo "deb [signed-by=/etc/apt/keyrings/xanmod-archive-keyring.gpg] https://deb.xanmod.org $(lsb_release -sc) main non-free" | root tee /etc/apt/sources.list.d/xanmod-release.list >>"$LOG_FILE" 2>&1 || true
        nospin
        log_ok "Repositorio XanMod agregado"
    fi

    if ! uname -r 2>/dev/null | grep -q "xanmod"; then
        spin "Instalando kernel XanMod x64v3..."
        run_cmd "nala update" root nala update || true
        run_cmd "nala install xanmod" root nala install -y linux-xanmod-x64v3 || true
        run_cmd "nala install dkms" root nala install --no-install-recommends -y dkms libelf-dev clang lld llvm || true
        nospin
        log_ok "Kernel XanMod x64v3 instalado (requiere reinicio para aplicar)"
    else
        log_skip "XanMod ya instalado"
    fi

    save_checkpoint 2
}

step_3() {
    should_run_step 3 || return 0
    log_step 3 "$TOTAL_STEPS" "Detectando GPU NVIDIA e instalando drivers"

    if command -v lspci >/dev/null 2>&1; then
        HAS_NVIDIA=0
        HAS_INTEL=0
        lspci -nn 2>/dev/null | grep -qi "nvidia" && HAS_NVIDIA=1
        lspci -nn 2>/dev/null | grep -qi "vga.*intel" && HAS_INTEL=1

        if [ "$HAS_NVIDIA" -eq 1 ]; then
            spin "Actualizando repositorios..."
            run_cmd "nala update" root nala update || true
            nospin

            if [ "$HAS_INTEL" -eq 1 ]; then
                log_info "Detectado sistema hibrido Intel + NVIDIA"
                spin "Instalando driver NVIDIA 595-open + prime..."
                run_cmd "nala install nvidia+prime" root nala install -y nvidia-driver-595-open nvidia-prime nvidia-settings || true
                nospin
                root prime-select on-demand >>"$LOG_FILE" 2>&1 || true
                HAS_NVIDIA_GPU=1
                log_ok "Driver NVIDIA 595-open + prime instalados (usa prime-run para GPU discreta)"
            else
                log_info "Detectada solo NVIDIA"
                spin "Instalando driver NVIDIA 595-open..."
                run_cmd "nala install nvidia" root nala install -y nvidia-driver-595-open nvidia-settings || true
                nospin
                HAS_NVIDIA_GPU=1
                log_ok "Driver NVIDIA 595-open instalado"
            fi

            for svc in nvidia-suspend nvidia-resume nvidia-hibernate; do
                root systemctl enable "$svc" >>"$LOG_FILE" 2>&1 || true
            done
            log_ok "Servicios suspend/resume NVIDIA habilitados"
        else
            log_skip "Sin GPU NVIDIA detectada"
        fi
    else
        log_warn "lspci no disponible, omitiendo deteccion"
    fi

    save_checkpoint 3
}

step_4() {
    should_run_step 4 || return 0
    log_step 4 "$TOTAL_STEPS" "Instalando paquetes del sistema (Wayland, Nautilus, Apps, Audio, Codecs, Flatpak, TLP, Fonts)"

    spin "Instalando todos los paquetes (esto puede tardar)..."
    run_cmd "mega-install" root nala install --no-install-recommends -y \
        wayland-protocols libwayland-dev libegl1 \
        libgl1-mesa-dri mesa-vulkan-drivers xwayland \
        nautilus gvfs-backends gvfs-fuse udisks2 polkitd \
        ntfs-3g exfatprogs libglib2.0-bin \
        neovim zen-browser tmux fastfetch geany nwg-look foot dialog apt-utils\
        libheif-plugin-libde265 ufw gnome-sushi xdg-user-dirs \
        pipewire wireplumber libpipewire-0.3-0 libwireplumber-0.5-0 \
        dbus-user-session network-manager libnm0 \
        xdg-desktop-portal-wlr xdg-dbus-proxy \
        bluez bluez-tools pipewire-pulse \
        ubuntu-restricted-extras gstreamer1.0-plugins-bad \
        gstreamer1.0-libav ffmpegthumbnailer \
        flatpak tlp tlp-rdw fonts-powerline || true
    nospin

    log_ok "Todos los paquetes instalados"
    save_checkpoint 4
}

step_5() {
    should_run_step 5 || return 0
    log_step 5 "$TOTAL_STEPS" "Configurando polkit automontaje"

    POLKIT_RULE="/etc/polkit-1/rules.d/90-udisks2-automount.rules"
    if [ ! -f "$POLKIT_RULE" ]; then
        root mkdir -p /etc/polkit-1/rules.d || true
        root tee "$POLKIT_RULE" > /dev/null <<'POLKIT' || true
polkit.addRule(function(action, subject) {
    if ((action.id == "org.freedesktop.udisks2.filesystem-mount" ||
         action.id == "org.freedesktop.udisks2.filesystem-mount-system") &&
        subject.isInGroup("plugdev")) {
        return polkit.Result.YES;
    }
});
POLKIT
        log_ok "Regla polkit automontaje creada"
    else
        log_skip "Regla polkit ya existe"
    fi

    save_checkpoint 5
}

step_6() {
    should_run_step 6 || return 0
    log_step 6 "$TOTAL_STEPS" "Configurando xdg-user-dirs y UFW"

    if [ -d "$HOME_DIR/Documentos" ] || [ -d "$HOME_DIR/Documents" ]; then
        echo -e "${C_YELLOW}   Los directorios de usuario ya existen.${C_RESET}"
        echo -ne "${C_WHITE}   ¿Recrearlos? [s/N]: ${C_RESET}"
        read -r respuesta
        if [[ "$respuesta" =~ ^[Ss]$ ]]; then
            spin "Recreando directorios de usuario..."
            sudo -u "$REAL_USER" rm -rf "$HOME_DIR/Documentos" "$HOME_DIR/Documents" \
                "$HOME_DIR/Descargas" "$HOME_DIR/Downloads" \
                "$HOME_DIR/Escritorio" "$HOME_DIR/Desktop" \
                "$HOME_DIR/Imágenes" "$HOME_DIR/Pictures" \
                "$HOME_DIR/Música" "$HOME_DIR/Music" \
                "$HOME_DIR/Vídeos" "$HOME_DIR/Videos" \
                "$HOME_DIR/Plantillas" "$HOME_DIR/Templates" \
                "$HOME_DIR/Público" "$HOME_DIR/Public" 2>/dev/null || true
            sudo -u "$REAL_USER" xdg-user-dirs-update >>"$LOG_FILE" 2>&1 || log_warn "xdg-user-dirs-update fallo"
            nospin
            log_ok "Directorios de usuario recreados"
        else
            log_skip "Directorios de usuario conservados"
        fi
    else
        spin "Creando directorios de usuario..."
        sudo -u "$REAL_USER" xdg-user-dirs-update >>"$LOG_FILE" 2>&1 || log_warn "xdg-user-dirs-update fallo"
        nospin
        log_ok "Directorios de usuario creados"
    fi

    if ! ufw status 2>/dev/null | grep -q "Status: active"; then
        root ufw default deny incoming >>"$LOG_FILE" 2>&1 || true
        root ufw default allow outgoing >>"$LOG_FILE" 2>&1 || true
        echo "y" | root ufw enable >>"$LOG_FILE" 2>&1 || true
        root ufw allow ssh >>"$LOG_FILE" 2>&1 || true
        log_ok "UFW habilitado (deny incoming, allow outgoing, SSH permitido)"
    else
        if ! ufw status 2>/dev/null | grep -q "22/tcp"; then
            root ufw allow ssh >>"$LOG_FILE" 2>&1 || true
            log_ok "Regla SSH agregada a UFW"
        else
            log_skip "UFW ya está activo con SSH"
        fi
    fi

    save_checkpoint 6
}

step_7() {
    should_run_step 7 || return 0
    log_step 7 "$TOTAL_STEPS" "Configurando red y optimizando boot"

    # systemd-networkd-wait-online
    if ! systemctl is-masked systemd-networkd-wait-online.service 2>/dev/null; then
        run_cmd "disable wait-online" root systemctl disable systemd-networkd-wait-online.service || true
        run_cmd "mask wait-online" root systemctl mask systemd-networkd-wait-online.service || true
        log_ok "systemd-networkd-wait-online desactivado (evita bloqueos de 5 min)"
    else
        log_skip "systemd-networkd-wait-online ya desactivado"
    fi

    # Detectar interfaz de red activa
    ACTIVE_IFACE=$(ip route show default 2>/dev/null | awk '{print $5}' | head -n 1)

    # Si no hay ruta default, buscar primera interfaz ethernet activa
    if [ -z "$ACTIVE_IFACE" ]; then
        ACTIVE_IFACE=$(ip -o link show 2>/dev/null | awk -F': ' '{print $2}' | grep -E '^en|^eth' | head -n 1)
    fi

    if [ -n "$ACTIVE_IFACE" ]; then
        log_info "Interfaz de red detectada: $ACTIVE_IFACE"
    else
        log_warn "No se pudo detectar la interfaz de red, usando configuracion generica"
    fi

    # Habilitar NetworkManager ANTES de cambiar netplan
    if ! systemctl is-active NetworkManager >/dev/null 2>&1; then
        run_cmd "enable NetworkManager" root systemctl enable --now NetworkManager || true
        log_ok "NetworkManager habilitado e iniciado"
    else
        log_skip "NetworkManager ya esta activo"
    fi

    # Netplan
    NETPLAN_DIR="/etc/netplan"
    NETPLAN_FILE="$NETPLAN_DIR/01-netcfg.yaml"

    if [ ! -f "$NETPLAN_FILE" ] || ! grep -q "NetworkManager" "$NETPLAN_FILE"; then
        # Backup del netplan original
        if [ -f "$NETPLAN_FILE" ]; then
            root cp "$NETPLAN_FILE" "${NETPLAN_FILE}.bak-$(date +%Y%m%d-%H%M%S)" 2>/dev/null || true
            log_info "Backup del netplan original creado"
        fi

        root rm -f "$NETPLAN_DIR"/*.yaml.bak 2>/dev/null || true

        # Escribir nuevo netplan con interfaz detectada
        root tee "$NETPLAN_FILE" > /dev/null <<NETPLAN || true
network:
  version: 2
  renderer: NetworkManager
NETPLAN

        if [ -n "$ACTIVE_IFACE" ]; then
            root tee -a "$NETPLAN_FILE" > /dev/null <<NETPLAN || true
  ethernets:
    $ACTIVE_IFACE:
      dhcp4: true
NETPLAN
        fi

        run_cmd "netplan apply" root netplan apply || true
        log_ok "Netplan configurado (renderer: NetworkManager)"

        # Verificar que NetworkManager tenga permisos de gestion
        if command -v nmcli >/dev/null 2>&1 && [ -n "$ACTIVE_IFACE" ]; then
            sleep 3
            if nmcli device status 2>/dev/null | grep -q "$ACTIVE_IFACE"; then
                log_info "NetworkManager gestionando $ACTIVE_IFACE"
            fi
        fi
    else
        log_skip "Netplan ya configurado"
    fi

    save_checkpoint 7
}

step_8() {
    should_run_step 8 || return 0
    log_step 8 "$TOTAL_STEPS" "Configurando Flatpak y aplicaciones"

    FLATHUB_OK=false
    if ! flatpak remotes 2>/dev/null | grep -q "flathub"; then
        spin "Agregando Flathub..."
        if run_cmd "flatpak remote-add" root flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo; then
            nospin
            log_ok "Flathub agregado"
            FLATHUB_OK=true
        else
            nospin
            log_warn "No se pudo agregar Flathub, se omitiran las aplicaciones Flatpak"
        fi
    else
        log_skip "Flathub ya existe"
        FLATHUB_OK=true
    fi

    if [ "$FLATHUB_OK" = true ]; then
        for app in org.gnome.Papers net.nokyan.Resources org.gnome.Showtime; do
            if flatpak list --app 2>/dev/null | grep -q "$app"; then
                log_skip "$app ya instalado"
            else
                spin "Instalando $app..."
                if run_cmd "flatpak install $app" root flatpak install --system -y flathub "$app"; then
                    nospin
                    log_ok "$app instalado"
                else
                    nospin
                    log_warn "$app no se pudo instalar"
                fi
            fi
        done
    fi
    log_ok "Paso Flatpak completado"

    # Override para Nautilus
    FLATPAK_OVERRIDE="/etc/flatpak/overrides/global"
    if [ ! -f "$FLATPAK_OVERRIDE" ]; then
        root mkdir -p /etc/flatpak/overrides || true
        root tee "$FLATPAK_OVERRIDE" > /dev/null <<'FLATPAK' || true
[Context]
filesystems=xdg-run/gvfs:host;host:ro;
FLATPAK
        log_ok "Override Flatpak para Nautilus creado"
    else
        log_skip "Override Flatpak ya existe"
    fi

    save_checkpoint 8
}

step_9() {
    should_run_step 9 || return 0
    log_step 9 "$TOTAL_STEPS" "Habilitando servicios y configurando entorno Wayland"

    run_cmd "enable services" root systemctl enable --now udisks2.service bluetooth.service || true
    if ! systemctl is-active NetworkManager >/dev/null 2>&1; then
        run_cmd "enable NetworkManager" root systemctl enable --now NetworkManager || true
    fi
    log_ok "Servicios habilitados: NetworkManager, udisks2, bluetooth"

    root loginctl enable-linger "$REAL_USER" >>"$LOG_FILE" 2>&1 || true
    sudo -u "$REAL_USER" bash -c 'export XDG_RUNTIME_DIR="/run/user/$(id -u)"; systemctl --user enable pipewire.socket wireplumber.service' >>"$LOG_FILE" 2>&1 || true
    log_ok "Servicios de usuario habilitados: pipewire, wireplumber"

    ENV_FILE="$HOME_DIR/.config/environment.d/wayland.conf"
    if [ ! -f "$ENV_FILE" ]; then
        sudo -u "$REAL_USER" mkdir -p "$HOME_DIR/.config/environment.d"
        sudo -u "$REAL_USER" tee "$ENV_FILE" > /dev/null <<'ENV'
GDK_BACKEND=wayland
QT_QPA_PLATFORM=wayland
SDL_VIDEODRIVER=wayland
MOZ_ENABLE_WAYLAND=1
XDG_CURRENT_DESKTOP=niri
XDG_SESSION_TYPE=wayland
ENV
        log_ok "Entorno Wayland configurado"
    else
        log_skip "Entorno Wayland ya existe"
    fi

    save_checkpoint 9
}

step_10() {
    should_run_step 10 || return 0
    log_step 10 "$TOTAL_STEPS" "Configurando optimización energética (TLP)"

    TLP_CONF="/etc/tlp.d/01-voidforge.conf"
    if [ ! -f "$TLP_CONF" ]; then
        root mkdir -p /etc/tlp.d || true
        root tee "$TLP_CONF" > /dev/null <<'TLP' || true
TLP_ENABLE=1
CPU_SCALING_GOVERNOR_ON_AC=powersave
CPU_SCALING_GOVERNOR_ON_BAT=powersave
CPU_ENERGY_PERF_POLICY_ON_AC=balance_performance
CPU_ENERGY_PERF_POLICY_ON_BAT=power
CPU_MIN_PERF_ON_AC=0
CPU_MAX_PERF_ON_AC=100
CPU_MIN_PERF_ON_BAT=0
CPU_MAX_PERF_ON_BAT=80
CPU_BOOST_ON_AC=1
CPU_BOOST_ON_BAT=0
INTEL_GPU_MIN_FREQ_ON_AC=0
INTEL_GPU_MIN_FREQ_ON_BAT=0
INTEL_GPU_MAX_FREQ_ON_AC=0
INTEL_GPU_MAX_FREQ_ON_BAT=0
INTEL_GPU_BOOST_ON_AC=1
INTEL_GPU_BOOST_ON_BAT=0
PCIE_ASPM_ON_AC=powersupersave
PCIE_ASPM_ON_BAT=powersupersave
RAID_DEVICE_POWER_MGMT_ON_AC=auto
RAID_DEVICE_POWER_MGMT_ON_BAT=auto
WIFI_PWR_ON_AC=off
WIFI_PWR_ON_BAT=on
SOUND_POWER_SAVE_ON_AC=1
SOUND_POWER_SAVE_ON_BAT=1
SOUND_POWER_SAVE_CONTROLLER=Y
USB_AUTOSUSPEND=1
USB_BLACKLIST_WWAN=1
RESTORE_THRESHOLDS_ON_BAT=1
NATACPI_ENABLE=1
TPACPI_ENABLE=1
TPSMAPI_ENABLE=1
TLP
        run_cmd "enable tlp" root systemctl enable tlp || true
        log_ok "TLP configurado y habilitado"
    else
        log_skip "TLP ya configurado"
    fi

    # logind.conf
    LOGIND="/etc/systemd/logind.conf"
    grep -q "^HandleLidSwitch=suspend$" "$LOGIND" || root sed -i 's/^#HandleLidSwitch=.*/HandleLidSwitch=suspend/' "$LOGIND" || true
    grep -q "^HandleLidSwitchExternalPower=suspend$" "$LOGIND" || root sed -i 's/^#HandleLidSwitchExternalPower=.*/HandleLidSwitchExternalPower=suspend/' "$LOGIND" || true
    grep -q "^HandleLidSwitchDocked=ignore$" "$LOGIND" || root sed -i 's/^#HandleLidSwitchDocked=.*/HandleLidSwitchDocked=ignore/' "$LOGIND" || true
    grep -q "^PowerKeyAction=poweroff$" "$LOGIND" || root sed -i 's/^#PowerKeyAction=.*/PowerKeyAction=poweroff/' "$LOGIND" || true
    log_ok "logind configurado (lid switch, power key)"

    save_checkpoint 10
}

step_11() {
    should_run_step 11 || return 0
    log_step 11 "$TOTAL_STEPS" "Configurando Oh My Zsh con tema agnoster"

    if [ "$(getent passwd "$REAL_USER" 2>/dev/null | cut -d: -f7)" != "$(which zsh)" ]; then
        root chsh -s "$(which zsh)" "$REAL_USER" >>"$LOG_FILE" 2>&1 || true
        log_ok "Shell por defecto: zsh"
    fi

    if [ ! -d "$HOME_DIR/.oh-my-zsh" ]; then
        spin "Instalando Oh My Zsh..."
        if sudo -u "$REAL_USER" bash -c '
            sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
            sed -i "s/^ZSH_THEME=.*/ZSH_THEME=\"agnoster\"/" "$HOME/.zshrc"
        ' >>"$LOG_FILE" 2>&1; then
            nospin
            log_ok "Oh My Zsh instalado, tema: agnoster"
        else
            nospin
            log_warn "Oh My Zsh no se pudo instalar (sin conexion o error de descarga)"
        fi
    else
        if [ -d "$HOME_DIR/.oh-my-zsh" ]; then
            echo -e "${C_YELLOW}   Oh My Zsh ya esta instalado.${C_RESET}"
            echo -ne "${C_WHITE}   ¿Reinstalar? [s/N]: ${C_RESET}"
            read -r respuesta
            if [[ "$respuesta" =~ ^[Ss]$ ]]; then
                spin "Reinstalando Oh My Zsh..."
                sudo -u "$REAL_USER" rm -rf "$HOME_DIR/.oh-my-zsh" 2>/dev/null || true
                if sudo -u "$REAL_USER" bash -c '
                    sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
                    sed -i "s/^ZSH_THEME=.*/ZSH_THEME=\"agnoster\"/" "$HOME/.zshrc"
                ' >>"$LOG_FILE" 2>&1; then
                    nospin
                    log_ok "Oh My Zsh reinstalado, tema: agnoster"
                else
                    nospin
                    log_warn "Oh My Zsh no se pudo reinstalar"
                fi
            else
                sudo -u "$REAL_USER" sed -i "s/^ZSH_THEME=.*/ZSH_THEME=\"agnoster\"/" "$HOME_DIR/.zshrc" >>"$LOG_FILE" 2>&1 || true
                log_skip "Oh My Zsh conservado"
            fi
        fi
    fi

    save_checkpoint 11
}

step_12() {
    should_run_step 12 || return 0
    log_step 12 "$TOTAL_STEPS" "Instalando LazyVim"

    LAZYVIM_DIR="$HOME_DIR/.config/nvim"
    LAZYVIM_INSTALLED=false
    if [ -f "$LAZYVIM_DIR/init.lua" ] && grep -q "LazyVim" "$LAZYVIM_DIR/init.lua" 2>/dev/null; then
        LAZYVIM_INSTALLED=true
    fi

    if [ "$LAZYVIM_INSTALLED" = true ]; then
        echo -e "${C_YELLOW}   LazyVim ya esta instalado.${C_RESET}"
        echo -ne "${C_WHITE}   ¿Reinstalar? [s/N]: ${C_RESET}"
        read -r respuesta
        if [[ "$respuesta" =~ ^[Ss]$ ]]; then
            LAZYVIM_INSTALLED=false
        fi
    fi

    if [ "$LAZYVIM_INSTALLED" = false ]; then
        spin "Instalando LazyVim..."

        sudo -u "$REAL_USER" bash -c "
            mv ~/.config/nvim ~/.config/nvim.bak 2>/dev/null || true
            mv ~/.local/share/nvim ~/.local/share/nvim.bak 2>/dev/null || true
            mv ~/.local/state/nvim ~/.local/state/nvim.bak 2>/dev/null || true
            mv ~/.cache/nvim ~/.cache/nvim.bak 2>/dev/null || true
            git clone https://github.com/LazyVim/starter ~/.config/nvim 2>/dev/null
            rm -rf ~/.config/nvim/.git 2>/dev/null || true
        " >>"$LOG_FILE" 2>&1

        nospin
        log_ok "LazyVim instalado (ejecuta 'nvim' para completar la configuracion)"
    else
        log_skip "LazyVim conservado"
    fi

    save_checkpoint 12
}

step_13() {
    should_run_step 13 || return 0
    log_step 13 "$TOTAL_STEPS" "Instalando tema de iconos Colloid"

    if [ ! -d /usr/share/icons/Colloid-catppuccin-green-dark ]; then
        ICON_TMP_DIR="$(mktemp --directory)"
        spin "Descargando tema de iconos Colloid..."
        run_cmd "git clone Colloid" git clone --depth 1 https://github.com/vinceliuice/Colloid-icon-theme.git "$ICON_TMP_DIR" || true
        nospin
        spin "Instalando tema Colloid..."
        run_cmd "Colloid install" root "$ICON_TMP_DIR/install.sh" -b -s catppuccin -t green || true
        nospin
        rm -rf "$ICON_TMP_DIR"
        log_ok "Tema Colloid (catppuccin green) instalado"
    else
        log_skip "Tema Colloid ya instalado"
    fi

    save_checkpoint 13
}

step_14() {
    should_run_step 14 || return 0
    log_step 14 "$TOTAL_STEPS" "Configurando Plymouth y GRUB"

    # Plymouth theme desde ZIP o URL
    spin "Instalando Plymouth..."
    run_cmd "nala install plymouth" root nala install -y plymouth plymouth-themes || true
    nospin
    root mkdir -p /usr/share/plymouth/themes || true

    PLYMOUTH_ZIP_PATH=""
    if [ -z "$PLYMOUTH_ZIP_NAME" ]; then
        PLYMOUTH_ZIP_PATH=$(find "$SCRIPT_DIR" -maxdepth 1 -name "*.zip" 2>/dev/null | head -n 1)
    else
        PLYMOUTH_ZIP_PATH="$SCRIPT_DIR/$PLYMOUTH_ZIP_NAME"
    fi

    # Descargar desde URL si no existe localmente
    if [ ! -f "$PLYMOUTH_ZIP_PATH" ] && [ -n "$PLYMOUTH_ZIP_URL" ]; then
        log_info "Descargando tema Plymouth..."
        if command -v curl &>/dev/null; then
            run_cmd "curl plymouth" curl -fsSL -o "/tmp/$PLYMOUTH_ZIP_NAME" "$PLYMOUTH_ZIP_URL" || true
        elif command -v wget &>/dev/null; then
            run_cmd "wget plymouth" wget -q -O "/tmp/$PLYMOUTH_ZIP_NAME" "$PLYMOUTH_ZIP_URL" || true
        fi
        if [ -f "/tmp/$PLYMOUTH_ZIP_NAME" ]; then
            PLYMOUTH_ZIP_PATH="/tmp/$PLYMOUTH_ZIP_NAME"
        fi
    fi

    PLYMOUTH_THEME_SET=false
    if [ -n "$PLYMOUTH_ZIP_PATH" ] && [ -f "$PLYMOUTH_ZIP_PATH" ]; then
        TEMP_DIR=$(mktemp -d)
        run_cmd "unzip plymouth" unzip -q "$PLYMOUTH_ZIP_PATH" -d "$TEMP_DIR" || true

        PLYMOUTH_FILE=$(find "$TEMP_DIR" -name "*.plymouth" -type f 2>/dev/null | head -n 1)

        if [ -n "$PLYMOUTH_FILE" ]; then
            THEME_NAME=$(basename "$PLYMOUTH_FILE" .plymouth)
            PLYMOUTH_THEME_DIR="/usr/share/plymouth/themes/$THEME_NAME"
            root mkdir -p "$PLYMOUTH_THEME_DIR" || true
            root cp -r "$(dirname "$PLYMOUTH_FILE")/." "$PLYMOUTH_THEME_DIR/" 2>/dev/null || true

            if [ -f "$PLYMOUTH_THEME_DIR/$THEME_NAME.plymouth" ]; then
                run_cmd "update-alternatives install" root update-alternatives --install /usr/share/plymouth/themes/default.plymouth default.plymouth "$PLYMOUTH_THEME_DIR/$THEME_NAME.plymouth" 100 || true
                run_cmd "update-alternatives set" root update-alternatives --set default.plymouth "$PLYMOUTH_THEME_DIR/$THEME_NAME.plymouth" || true

                if update-alternatives --query default.plymouth 2>/dev/null | grep -q "Value: $PLYMOUTH_THEME_DIR/$THEME_NAME.plymouth"; then
                    log_ok "Tema Plymouth: $THEME_NAME"
                    PLYMOUTH_THEME_SET=true
                else
                    log_warn "Tema Plymouth copiado pero update-alternatives fallo"
                fi
            else
                log_warn "Tema Plymouth: no se encontro $THEME_NAME.plymouth en el ZIP"
            fi
        else
            log_warn "No se encontro archivo .plymouth en el ZIP"
        fi

        rm -rf "$TEMP_DIR"
    else
        log_warn "No se encontro tema Plymouth en $SCRIPT_DIR ni en URL"
    fi

    if [ "$PLYMOUTH_THEME_SET" = false ]; then
        log_info "Plymouth usara tema por defecto del sistema"
    fi

    # GRUB theme
    GRUB_THEME_PATH="/usr/share/grub/themes/grub-theme-vimix-very-dark-blue"
    if [ ! -f "$GRUB_THEME_PATH/theme.txt" ]; then
        GRUB_TMP_DIR="$(mktemp --directory)"
        spin "Descargando tema GRUB Vimix..."
        run_cmd "git clone GRUB theme" git clone --depth 1 https://github.com/trueNAHO/grub2-theme-vimix-very-dark-blue.git "$GRUB_TMP_DIR" || true
        nospin
        root install --directory --mode 755 "$GRUB_THEME_PATH" || true
        root cp --no-preserve=ownership --recursive "$GRUB_TMP_DIR/src/." "$GRUB_THEME_PATH" || true
        rm -rf "$GRUB_TMP_DIR"
        log_ok "Tema GRUB: Vimix Very Dark Blue"
    else
        log_skip "Tema GRUB ya instalado"
    fi

    # Configuración GRUB
    GRUB_CFG="/etc/default/grub"

    # Agregar parámetros de kernel NVIDIA si hay GPU NVIDIA
    if [ "$HAS_NVIDIA_GPU" -eq 1 ]; then
        log_info "Agregando parámetros de kernel para NVIDIA..."
        grep -q "nvidia-drm.modeset=1" "$GRUB_CFG" || root sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="quiet"/GRUB_CMDLINE_LINUX_DEFAULT="quiet splash nvidia-drm.modeset=1 nvidia-drm.fbdev=1 nvidia.NVreg_PreserveVideoMemoryAllocations=1/' "$GRUB_CFG" || true
        grep -q "nvidia-drm.modeset=1" "$GRUB_CFG" || root sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="/GRUB_CMDLINE_LINUX_DEFAULT="quiet splash plymouth:force-recovery splash= nvidia-drm.modeset=1 nvidia-drm.fbdev=1 nvidia.NVreg_PreserveVideoMemoryAllocations=1"/' "$GRUB_CFG" || true
    else
        grep -q "GRUB_CMDLINE_LINUX_DEFAULT=.*splash" "$GRUB_CFG" || root sed -i 's/^GRUB_CMDLINE_LINUX_DEFAULT="/GRUB_CMDLINE_LINUX_DEFAULT="quiet splash plymouth:force-recovery splash=/' "$GRUB_CFG" || true
    fi

    grep -q "GRUB_GFXPAYLOAD_LINUX=keep" "$GRUB_CFG" || root sh -c "echo 'GRUB_GFXPAYLOAD_LINUX=keep' >> \"$GRUB_CFG\"" 2>/dev/null || true

    # GRUB_THEME
    { grep -q "^GRUB_THEME=" "$GRUB_CFG" \
        && root sed -i "s|^GRUB_THEME=.*|GRUB_THEME=\"$GRUB_THEME_PATH/theme.txt\"|" "$GRUB_CFG" \
        || root sh -c "echo \"GRUB_THEME=\\\"$GRUB_THEME_PATH/theme.txt\\\"\" >> \"$GRUB_CFG\""; } || true

    log_ok "Configuración GRUB actualizada"

    # Initramfs para Plymouth y NVIDIA
    root mkdir -p /etc/initramfs-tools/conf.d || true
    root sh -c "echo 'FRAMEBUFFER=y' > /etc/initramfs-tools/conf.d/splash" 2>/dev/null || true

    # Módulos NVIDIA en initramfs si hay GPU NVIDIA
    if [ "$HAS_NVIDIA_GPU" -eq 1 ]; then
        root sh -c "echo 'nvidia' >> /etc/initramfs-tools/modules" 2>/dev/null || true
        root sh -c "echo 'nvidia-drm' >> /etc/initramfs-tools/modules" 2>/dev/null || true
        root sh -c "echo 'nvidia-modeset' >> /etc/initramfs-tools/modules" 2>/dev/null || true
        root sh -c "echo 'nvidia-uvm' >> /etc/initramfs-tools/modules" 2>/dev/null || true
        log_info "Módulos NVIDIA agregados a initramfs"
    else
        root sh -c "echo 'drm' >> /etc/initramfs-tools/modules" 2>/dev/null || true
    fi

    spin "Regenerando GRUB e initramfs..."
    run_cmd "grub-mkconfig" root grub-mkconfig -o /boot/grub/grub.cfg || true
    run_cmd "update-initramfs" root update-initramfs -u || true
    nospin
    log_ok "GRUB e initramfs regenerados"

    # Limpieza de paquetes huérfanos
    spin "Limpiando paquetes huerfanos..."
    run_cmd "nala autoremove" root nala autoremove -y || true
    run_cmd "nala clean" root nala clean || true
    nospin
    log_ok "Paquetes huérfanos eliminados, caché limpiada"

    save_checkpoint 14
}

step_15() {
    should_run_step 15 || return 0
    log_step 15 "$TOTAL_STEPS" "Instalando DMS (Dank Linux)"

    log_info "Ejecutando asistente de instalación DMS..."
    run_cmd "DMS installer" sudo -u "$REAL_USER" sh -c "curl -fsSL https://install.danklinux.com | sh" || true

    save_checkpoint 15
}

run_step() {
    echo "[DEBUG] run_step arg='$1'" >&2
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

    echo -e "${C_GREEN}✅ Todos los pasos completados${C_RESET}\n"

    echo -e "${C_WHITE}Cambios realizados:${C_RESET}"
    echo -e "  • Kernel: XanMod Edge"
    echo -e "  • Wayland + Nautilus + PipeWire"
    echo -e "  • Flatpak con Flathub + Apps Papers, Resources, Showtime"
    echo -e "  • Oh My Zsh + tema agnoster"
    echo -e "  • Nerd Fonts: fonts-powerline"
    echo -e "  • Iconos: Colloid catppuccin green"
    echo -e "  • Temas: Plymouth + GRUB Vimix"
    echo -e "  • Firewall: UFW activo deny incoming"
    echo -e "  • TLP configurado para laptops"
    echo -e "  • DMS (Dank Linux)"

    if [ "$HAS_NVIDIA_GPU" -eq 1 ]; then
        echo -e "  • Drivers NVIDIA + parámetros kernel DRM/KMS"
    fi

    echo -e "\n${C_YELLOW}⚠️ Importante:${C_RESET}"
    echo -e "  • Si se instaló XanMod Edge, ${C_RED}requiere reiniciar${C_RESET} para aplicar el nuevo kernel"
    echo -e "  • Si se instalaron drivers NVIDIA, ${C_RED}requiere reiniciar${C_RESET} para aplicar DRM/KMS"
    echo -e "\n${C_WHITE}Comandos útiles:${C_RESET}"
    echo -e "  ${C_GRAY}sudo reboot${C_RESET}              — Reiniciar para aplicar cambios"
    echo -e "  ${C_GRAY}prime-run <app>${C_RESET}         — Usar GPU NVIDIA en sistema hibrido"
    echo -e "  ${C_GRAY}tlp start${C_RESET}               — Iniciar TLP manualmente"
    echo -e "  ${C_GRAY}tlp-stat${C_RESET}                — Ver estado de ahorro de energía"
    echo -e "  ${C_GRAY}ufw status${C_RESET}               — Ver estado del firewall"
    echo -e "  ${C_GRAY}flatpak list${C_RESET}            — Ver aplicaciones Flatpak instaladas"
    echo -e "\n${C_GRAY}Log completo: $LOG_FILE${C_RESET}"
    echo -e "\n${C_GREEN}¡Tu sistema está listo! 🚀${C_RESET}\n"
}

# ============================================================
# MENÚ INTERACTIVO
# ============================================================

show_menu() {
    clear
    print_banner

    echo -e "${C_WHITE}  ${C_CYAN}[1]${C_RESET}  Instalacion completa pasos 0-15"
    echo -e "${C_WHITE}  ${C_CYAN}[2]${C_RESET}  Reanudar desde último checkpoint"
    echo -e "${C_WHITE}  ${C_CYAN}[3]${C_RESET}  Ejecutar paso específico"
    echo -e "${C_WHITE}  ${C_CYAN}[4]${C_RESET}  Ejecutar rango de pasos"
    echo -e "${C_WHITE}  ${C_CYAN}[5]${C_RESET}  Ver estado actual"
    echo -e "${C_WHITE}  ${C_CYAN}[6]${C_RESET}  Salir"
    echo ""
    echo -ne "${C_WHITE}  Selecciona una opcion [1-6]: ${C_RESET}"
}

handle_menu_choice() {
    echo "[DEBUG] Entering handle_menu_choice" >&2
    read -r choice </dev/tty
    echo "[DEBUG] choice='$choice'" >&2
    case $choice in
        1)
            echo "[DEBUG] Branch 1: run_all_steps" >&2
            run_all_steps
            ;;
        2)
            last_step=$(load_checkpoint)
            if [ -n "$last_step" ]; then
                for i in $(seq $((last_step + 1)) "$TOTAL_STEPS"); do
                    run_step "$i"
                done
                print_summary
            else
                log_warn "No hay checkpoint. Ejecutando instalación completa..."
                run_all_steps
            fi
            ;;
        3)
            echo -ne "${C_WHITE}  Numero de paso 0-15: ${C_RESET}"
            read -r step </dev/tty
            run_step "$step"
            ;;
        4)
            echo -ne "${C_WHITE}  Rango ej: 5-10: ${C_RESET}"
            read -r range </dev/tty
            start=$(echo "$range" | cut -d- -f1)
            end=$(echo "$range" | cut -d- -f2)
            for i in $(seq "$start" "$end"); do
                run_step "$i"
            done
            ;;
        5)
            last_step=$(load_checkpoint)
            if [ -n "$last_step" ]; then
                log_info "Último paso completado: $last_step"
            else
                log_info "No hay checkpoint guardado"
            fi
            echo -ne "${C_WHITE}  Presiona Enter para continuar...${C_RESET}"
            read -r </dev/tty
            show_menu
            handle_menu_choice
            ;;
        6)
            clear
            exit 0
            ;;
        *)
            echo -e "${C_RED}  Opción no válida${C_RESET}"
            sleep 1
            show_menu
            handle_menu_choice
            ;;
    esac
}

# ============================================================
# PARSEO DE ARGUMENTOS CLI
# ============================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --resume)
                RESUME=true
                shift
                ;;
            --step)
                RESUME=false
                clear_checkpoint
                SKIP_STEPS=""
                run_step "$2"
                shift 2
                exit 0
                ;;
            --range)
                RESUME=false
                clear_checkpoint
                SKIP_STEPS=""
                start=$(echo "$2" | cut -d- -f1)
                end=$(echo "$2" | cut -d- -f2)
                for i in $(seq "$start" "$end"); do
                    run_step "$i"
                done
                shift 2
                exit 0
                ;;
            --skip)
                SKIP_STEPS="$2"
                shift 2
                ;;
            --all)
                run_all_steps
                shift
                exit 0
                ;;
            *)
                log_error "Opción desconocida: $1"
                echo "Uso: $0 [--resume] [--step N] [--range N-M] [--skip N,M,...] [--all]"
                exit 1
                ;;
        esac
    done
}

# ============================================================
# VERIFICACIÓN DEL SISTEMA
# ============================================================

check_system() {
    local OS_ID=""
    local OS_VERSION=""

    if [ -f /etc/os-release ]; then
        OS_ID=$(grep '^ID=' /etc/os-release | cut -d= -f2 | tr -d '"')
        OS_VERSION=$(grep '^VERSION_ID=' /etc/os-release | cut -d= -f2 | tr -d '"')
    fi

    if [ "$OS_ID" = "ubuntu" ]; then
        OS_MAJOR=$(echo "$OS_VERSION" | cut -d. -f1)
        if [ "$OS_MAJOR" -ge 26 ]; then
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

# ============================================================
# GESTIÓN DE SUDO
# ============================================================

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

# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

main() {
    # Inicializar log (lo antes posible)
    echo "=== VoidForge v${VERSION} - $(date) ===" > "$LOG_FILE"
    echo "Usuario: $REAL_USER | Home: $HOME_DIR | Script: $SCRIPT_DIR" >> "$LOG_FILE"

    # Verificar sistema
    if ! check_system; then
        exit 1
    fi

    # Cachear permisos sudo (pide contraseña una vez)
    ensure_sudo

    # Si hay args CLI, procesarlos
    if [[ $# -gt 0 ]]; then
        parse_args "$@"
        return
    fi

    # Modo interactivo (default)
    show_menu
    handle_menu_choice
}

main "$@"
