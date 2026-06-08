step_4() {
    should_run_step 4 || return 0
    log_step 4 "$TOTAL_STEPS" "Instalando paquetes del sistema (Wayland, Nautilus, Apps, Audio, Codecs, Flatpak, TLP, Fonts)"

    spin "Instalando todos los paquetes (esto puede tardar)..."
    run_cmd "mega-install" root nala install --no-install-recommends -y \
        wayland-protocols libwayland-dev libegl1 \
        libgl1-mesa-dri mesa-vulkan-drivers xwayland \
        nautilus gvfs-backends gvfs-fuse udisks2 polkitd \
        ntfs-3g exfatprogs libglib2.0-bin \
        neovim zen-browser tmux fastfetch geany nwg-look foot \
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
