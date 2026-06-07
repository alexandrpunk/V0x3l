step_8() {
    should_run_step 8 || return 0
    log_step 8 "$TOTAL_STEPS" "Configurando Flatpak y aplicaciones"

    FLATHUB_OK=false
    if ! flatpak remotes 2>/dev/null | grep -q "flathub"; then
        spin "Agregando Flathub..."
        if run_cmd "flatpak remote-add" root flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo; then
            nospin; log_ok "Flathub agregado"; FLATHUB_OK=true
        else
            nospin; log_warn "No se pudo agregar Flathub, se omitiran las aplicaciones Flatpak"
        fi
    else
        log_skip "Flathub ya existe"; FLATHUB_OK=true
    fi

    if [ "$FLATHUB_OK" = true ]; then
        for app in org.gnome.Papers net.nokyan.Resources org.gnome.Showtime; do
            if flatpak list --app 2>/dev/null | grep -q "$app"; then
                log_skip "$app ya instalado"
            else
                spin "Instalando $app..."
                if run_cmd "flatpak install $app" root flatpak install --system -y flathub "$app"; then
                    nospin; log_ok "$app instalado"
                else
                    nospin; log_warn "$app no se pudo instalar"
                fi
            fi
        done
    fi

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
