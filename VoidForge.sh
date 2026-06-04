#!/bin/bash
set -euo pipefail

# ============================================================
# Script de Post-Instalación Mínima para Ubuntu Server
# Gestor: Nala | Base: Wayland + Nautilus + Flatpak
# Objetivo: Configurar base, Plymouth (desde ZIP local) y Dank Linux
# ============================================================

if [[ $EUID -ne 0 ]]; then
    echo "❌ Este script debe ejecutarse como root (sudo)." >&2
    exit 1
fi

REAL_USER="${SUDO_USER:-$USER}"
HOME_DIR="/home/$REAL_USER"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo -e "\033[1;36m"
cat <<'ASCII'
 /$$    /$$          /$$       /$$ /$$$$$$$$                                                    /$$
| $$   | $$         |__/      | $$| $$_____/                                                   | $$
| $$   | $$ /$$$$$$  /$$  /$$$$$$$| $$     /$$$$$$   /$$$$$$   /$$$$$$   /$$$$$$       /$$$$$$$| $$$$$$$
|  $$ / $$//$$__  $$| $$ /$$__  $$| $$$$$ /$$__  $$ /$$__  $$ /$$__  $$ /$$__  $$     /$$_____/| $$__  $$
 \  $$ $$/| $$  \ $$| $$| $$  | $$| $$__/| $$  \ $$| $$  \__/| $$  \ $$| $$$$$$$$    |  $$$$$$ | $$  \ $$
  \  $$$/ | $$  | $$| $$| $$  | $$| $$   | $$  | $$| $$      | $$  | $$| $$_____/     \____  $$| $$  | $$
   \  $/  |  $$$$$$/| $$|  $$$$$$$| $$   |  $$$$$$/| $$      |  $$$$$$$|  $$$$$$$ /$$ /$$$$$$$/| $$  | $$
    \_/    \______/ |__/ \_______/|__/    \______/ |__/       \____  $$ \_______/|__/|_______/ |__/  |__/
                                                                  /$$  \ $$
                                                                 |  $$$$$$/
                                                                  \______/
ASCII
echo -e "\033[0m"
echo -e "\033[3;37m         Tu sistema. Tus reglas. Tu forja.\033[0m"
echo ""
echo "🔧 Configurando entorno mínimo para usuario: $REAL_USER"
echo "📂 Directorio del script detectado: $SCRIPT_DIR"

# --- CONFIGURACIÓN DEL TEMA PLYMOUTH ---
# El script buscará cualquier archivo .zip en la misma carpeta que este script
# Asegúrate de que solo haya UN zip del tema o cambia esto por el nombre exacto:
# PLYMOUTH_ZIP_NAME="mi_tema_plymouth.zip"
PLYMOUTH_ZIP_NAME="ubuntu-mac-style.zip" # Dejar vacío para detectar automáticamente el primer .zip

# 0. Instalar Nala y herramientas de descarga
echo "🥣 [0/13] Instalando Nala y utilidades..."
apt update && apt install -y nala wget tar unzip file zsh git curl ca-certificates

# 1. Agregar ButterRepo y Actualización base
echo "📦 [1/13] Agregando ButterRepo y actualizando sistema..."

if [ ! -f /etc/apt/sources.list.d/butterrepo.list ]; then
    curl -fsSL https://justaguylinux.codeberg.page/butterrepo/key.asc | gpg --dearmor -o /usr/share/keyrings/butterrepo.gpg
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/butterrepo.gpg] https://justaguylinux.codeberg.page/butterrepo stable main" | tee /etc/apt/sources.list.d/butterrepo.list
    echo "   ✅ ButterRepo agregado."
else
    echo "   ⏭️ ButterRepo ya existe, omitiendo."
fi

nala update && nala upgrade -y
usermod -aG video,render,audio,plugdev,netdev "$REAL_USER"

if [ "$(timedatectl show -p Timezone --value)" != "America/Mazatlan" ]; then
    timedatectl set-timezone America/Mazatlan
    echo "   ✅ Zona horaria configurada."
else
    echo "   ⏭️ Zona horaria ya configurada."
fi

nala install --no-install-recommends -y locales
if ! locale -a | grep -q "es_MX.utf8"; then
    sed -i 's/^# *es_MX\.UTF-8 UTF-8/es_MX.UTF-8 UTF-8/' /etc/locale.gen
    locale-gen
fi
if [ "$(cat /etc/default/locale | grep ^LANG= | cut -d= -f2)" != "es_MX.UTF-8" ]; then
    update-locale LANG=es_MX.UTF-8
fi

# 2. Stack Wayland y gráficos mínimos
echo "🖥️ [2/13] Instalando stack Wayland y drivers gráficos..."
nala install --no-install-recommends -y \
    wayland-protocols libwayland-dev libegl1 \
    libgl1-mesa-dri mesa-vulkan-drivers xwayland

# 3. Nautilus mínimo + automontaje
echo "📁 [3/13] Instalando Nautilus mínimo y backend de montaje..."
nala install --no-install-recommends -y \
    nautilus gvfs-backends gvfs-fuse udisks2 polkitd \
    ntfs-3g exfatprogs libglib2.0-bin

POLKIT_RULE="/etc/polkit-1/rules.d/90-udisks2-automount.rules"
if [ ! -f "$POLKIT_RULE" ]; then
    mkdir -p /etc/polkit-1/rules.d
    cat > "$POLKIT_RULE" <<'POLKIT'
polkit.addRule(function(action, subject) {
    if ((action.id == "org.freedesktop.udisks2.filesystem-mount" ||
         action.id == "org.freedesktop.udisks2.filesystem-mount-system") &&
        subject.isInGroup("plugdev")) {
        return polkit.Result.YES;
    }
});
POLKIT
    echo "   ✅ Regla polkit creada."
else
    echo "   ⏭️ Regla polkit ya existe."
fi

# 4. Paquetes adicionales (nala)
echo "📦 [4/13] Instalando paquetes adicionales..."

nala install --no-install-recommends -y \
    neovim zen-browser tmux fastfetch geany nwg-look \
    libheif-plugin-libde265 ufw gnome-sushi xdg-user-dirs

if [ ! -d "$HOME_DIR/Documentos" ] && [ ! -d "$HOME_DIR/Documents" ]; then
    sudo -u "$REAL_USER" xdg-user-dirs-update
fi

if ! ufw status | grep -q "Status: active"; then
    ufw default deny incoming
    ufw default allow outgoing
    echo "y" | ufw enable
    echo "   ✅ UFW habilitado."
else
    echo "   ⏭️ UFW ya está activo."
fi

# 5. Audio, Red (NetworkManager), Bluetooth y CORRECCIÓN DE TIEMPO DE ARRANQUE
echo "🔊 [5/13] Configurando audio, red, bluetooth y optimizando el inicio..."
nala install --no-install-recommends -y \
    pipewire wireplumber libpipewire-0.3-0 libwireplumber-0.5-0 \
    dbus-user-session network-manager libnm0 \
    xdg-desktop-portal-wlr xdg-dbus-proxy \
    bluez bluez-tools pipewire-pulse

systemctl enable --now bluetooth.service

echo "   🚀 Optimizando Netplan para evitar bloqueos de 5 minutos..."
if ! systemctl is-masked systemd-networkd-wait-online.service >/dev/null 2>&1; then
    systemctl disable systemd-networkd-wait-online.service
    systemctl mask systemd-networkd-wait-online.service
fi

NETPLAN_DIR="/etc/netplan"
NETPLAN_FILE="$NETPLAN_DIR/01-netcfg.yaml"
if [ ! -f "$NETPLAN_FILE" ] || ! grep -q "NetworkManager" "$NETPLAN_FILE"; then
    rm -f "$NETPLAN_DIR"/*.yaml.bak
    cat > "$NETPLAN_FILE" <<'NETPLAN'
network:
  version: 2
  renderer: NetworkManager
NETPLAN
    netplan apply
fi

# 6. Códecs multimedia completos
echo "🎬 [6/13] Instalando códecs multimedia y thumbnails..."
nala install --no-install-recommends -y \
    ubuntu-restricted-extras gstreamer1.0-plugins-bad \
    gstreamer1.0-libav ffmpegthumbnailer

# 7. Flatpak + portal de archivos para Nautilus
echo "📦 [7/13] Instalando y configurando Flatpak..."
nala install --no-install-recommends -y flatpak
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo

flatpak install --system -y flathub org.gnome.Papers net.nokyan.Resources org.gnome.Showtime

FLATPAK_OVERRIDE="/etc/flatpak/overrides/global"
if [ ! -f "$FLATPAK_OVERRIDE" ]; then
    mkdir -p /etc/flatpak/overrides
    cat > "$FLATPAK_OVERRIDE" <<'FLATPAK'
[Context]
filesystems=xdg-run/gvfs:host;host:ro;
FLATPAK
fi

# 8. Habilitar servicios y variables de entorno
echo "⚙️ [8/13] Habilitando servicios y configurando entorno Wayland..."
systemctl enable --now NetworkManager udisks2.service

loginctl enable-linger "$REAL_USER"

sudo -u "$REAL_USER" bash -c 'export XDG_RUNTIME_DIR="/run/user/$(id -u)"; systemctl --user enable pipewire.socket wireplumber.service'

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
fi

# 9. Optimización energética para laptops
echo "🔋 [9/13] Configurando optimización energética..."

nala install --no-install-recommends -y tlp tlp-rdw

TLP_CONF="/etc/tlp.d/01-voidforge.conf"
if [ ! -f "$TLP_CONF" ]; then
    cat > "$TLP_CONF" <<'TLP'
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
    echo "   ✅ Configuración TLP creada."
else
    echo "   ⏭️ Configuración TLP ya existe."
fi

systemctl enable tlp

LOGIND="/etc/systemd/logind.conf"
grep -q "^HandleLidSwitch=suspend$" "$LOGIND" || sed -i 's/^#HandleLidSwitch=.*/HandleLidSwitch=suspend/' "$LOGIND"
grep -q "^HandleLidSwitchExternalPower=suspend$" "$LOGIND" || sed -i 's/^#HandleLidSwitchExternalPower=.*/HandleLidSwitchExternalPower=suspend/' "$LOGIND"
grep -q "^HandleLidSwitchDocked=ignore$" "$LOGIND" || sed -i 's/^#HandleLidSwitchDocked=.*/HandleLidSwitchDocked=ignore/' "$LOGIND"
grep -q "^PowerKeyAction=poweroff$" "$LOGIND" || sed -i 's/^#PowerKeyAction=.*/PowerKeyAction=poweroff/' "$LOGIND"

# 10. Oh My Zsh + Nerd Fonts
echo "🐚 [10/13] Instalando Oh My Zsh, tema agnoster y Nerd Fonts..."

if [ "$(getent passwd "$REAL_USER" | cut -d: -f7)" != "$(which zsh)" ]; then
    chsh -s "$(which zsh)" "$REAL_USER"
fi

if [ ! -d "$HOME_DIR/.oh-my-zsh" ]; then
    sudo -u "$REAL_USER" bash -c '
        sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
        sed -i "s/^ZSH_THEME=.*/ZSH_THEME=\"agnoster\"/" "$HOME/.zshrc"
    '
else
    echo "   ⏭️ Oh My Zsh ya instalado."
    sudo -u "$REAL_USER" sed -i "s/^ZSH_THEME=.*/ZSH_THEME=\"agnoster\"/" "$HOME_DIR/.zshrc"
fi

nala install --no-install-recommends -y fonts-powerline

# 11. Tema de iconos Colloid
echo "📦 [11/13] Instalando tema de iconos Colloid..."

if [ ! -d /usr/share/icons/Colloid-catppuccin-green-dark ]; then
    ICON_TMP_DIR="$(mktemp --directory)"
    git clone --depth 1 https://github.com/vinceliuice/Colloid-icon-theme.git "$ICON_TMP_DIR"
    "$ICON_TMP_DIR/install.sh" -b -s catppuccin -t green
    rm -rf "$ICON_TMP_DIR"
else
    echo "   ⏭️ Tema Colloid ya instalado."
fi

# 12. INSTALAR TEMA PLYMOUTH DESDE ZIP LOCAL
echo "🎨 [12/13] Instalando tema Plymouth desde archivo local..."

nala install --no-install-recommends -y plymouth plymouth-themes
mkdir -p /usr/share/plymouth/themes

# Buscar el ZIP
if [ -z "$PLYMOUTH_ZIP_NAME" ]; then
    PLYMOUTH_ZIP_PATH=$(find "$SCRIPT_DIR" -maxdepth 1 -name "*.zip" | head -n 1)
else
    PLYMOUTH_ZIP_PATH="$SCRIPT_DIR/$PLYMOUTH_ZIP_NAME"
fi

if [ -z "$PLYMOUTH_ZIP_PATH" ] || [ ! -f "$PLYMOUTH_ZIP_PATH" ]; then
    echo "   ⚠️ No se encontró archivo .zip del tema en $SCRIPT_DIR. Omitiendo tema personalizado."
else
    echo "   📂 Tema encontrado: $(basename "$PLYMOUTH_ZIP_PATH")"

    TEMP_DIR=$(mktemp -d)
    unzip -q "$PLYMOUTH_ZIP_PATH" -d "$TEMP_DIR"

    THEME_FOLDER=$(find "$TEMP_DIR" -maxdepth 1 -type d ! -name "$TEMP_DIR" | head -n 1)

    if [ -n "$THEME_FOLDER" ]; then
        THEME_NAME=$(basename "$THEME_FOLDER")
        echo "   📦 Instalando tema: $THEME_NAME"

        mv "$THEME_FOLDER" "/usr/share/plymouth/themes/$THEME_NAME"

        PLYMOUTH_FILE="/usr/share/plymouth/themes/$THEME_NAME/$THEME_NAME.plymouth"
        if [ -f "$PLYMOUTH_FILE" ]; then
            update-alternatives --install /usr/share/plymouth/themes/default.plymouth default.plymouth "$PLYMOUTH_FILE" 100
            update-alternatives --set default.plymouth "$PLYMOUTH_FILE"
            echo "   ✅ Tema seleccionado correctamente."
        else
            echo "   ⚠️ No se encontró archivo .plymouth dentro de la carpeta extraída."
        fi
    else
        echo "   ❌ No se pudo extraer la carpeta del tema correctamente."
    fi

    rm -rf "$TEMP_DIR"
fi

# Instalar tema GRUB Vimix Very Dark Blue
GRUB_THEME_INSTALL_PATH=/usr/share/grub/themes/grub-theme-vimix-very-dark-blue
if [ ! -f "$GRUB_THEME_INSTALL_PATH/theme.txt" ]; then
    GRUB_THEME_REPO_URL=https://github.com/trueNAHO/grub2-theme-vimix-very-dark-blue.git
    GRUB_TMP_DIR="$(mktemp --directory)"
    git clone "$GRUB_THEME_REPO_URL" "$GRUB_TMP_DIR"
    install --directory --mode 755 "$GRUB_THEME_INSTALL_PATH"
    cp --no-preserve=ownership --recursive "$GRUB_TMP_DIR/src/." "$GRUB_THEME_INSTALL_PATH"
    rm --force --recursive "$GRUB_TMP_DIR"
fi

GRUB_CFG="/etc/default/grub"
grep -q "quiet splash" "$GRUB_CFG" || sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="quiet"/GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"/' "$GRUB_CFG"
grep -q "^GRUB_THEME=" "$GRUB_CFG" \
    && sed -i "s|^GRUB_THEME=.*|GRUB_THEME=\"$GRUB_THEME_INSTALL_PATH/theme.txt\"|" "$GRUB_CFG" \
    || echo "GRUB_THEME=\"$GRUB_THEME_INSTALL_PATH/theme.txt\"" >> "$GRUB_CFG"
grub-mkconfig -o /boot/grub/grub.cfg
update-initramfs -u

nala autoremove -y
nala clean

# 13. EJECUCIÓN DEL ASISTENTE DANK LINUX
echo ""
echo "🚀 [13/13] Iniciando asistente de instalación de Dank Material Linux..."
sudo -u "$REAL_USER" bash -c 'curl -fsSL https://install.danklinux.com | sh'

echo ""
echo "✅ PROCESO COMPLETADO."
echo "Reinicia el sistema para ver tu nuevo tema de arranque y entrar en Dank Linux:"
echo "   sudo reboot"
