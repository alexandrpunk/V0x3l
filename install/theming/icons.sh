step_13() {
    should_run_step 13 || return 0
    log_step 13 "$TOTAL_STEPS" "Instalando tema de iconos Colloid"

    if [ ! -d /usr/share/icons/Colloid-catppuccin-green-dark ]; then
        ICON_TMP_DIR="$(mktemp --directory)"
        run_cmd "git clone Colloid" git clone --depth 1 https://github.com/vinceliuice/Colloid-icon-theme.git "$ICON_TMP_DIR" || true
        run_cmd "Colloid install" root "$ICON_TMP_DIR/install.sh" -b -s catppuccin -t green || true
        rm -rf "$ICON_TMP_DIR"
        log_ok "Tema Colloid (catppuccin green) instalado"
    else
        log_skip "Tema Colloid ya instalado"
    fi
    save_checkpoint 13
}
