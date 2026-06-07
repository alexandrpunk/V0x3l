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
