step_1() {
    should_run_step 1 || return 0
    log_step 1 "$TOTAL_STEPS" "Configurando repositorios y sistema base"

    if [ ! -f /etc/apt/sources.list.d/butterrepo.list ]; then
        spin "Agregando ButterRepo..."
        curl -fsSL https://justaguylinux.codeberg.page/butterrepo/key.asc | root gpg --dearmor -o /usr/share/keyrings/butterrepo.gpg >>"$LOG_FILE" 2>&1 || true
        echo "deb [arch=amd64 signed-by=/usr/share/keyrings/butterrepo.gpg] https://justaguylinux.codeberg.page/butterrepo stable main" | root tee /etc/apt/sources.list.d/butterrepo.list >>"$LOG_FILE" 2>&1 || true
        nospin
        log_ok "ButterRepo agregado"
    else
        log_skip "ButterRepo ya existe"
    fi

    NALA_AVAILABLE=false; command -v nala >/dev/null 2>&1 && NALA_AVAILABLE=true
    PKG_MGR="apt"
    if [ "$NALA_AVAILABLE" = true ]; then
        PKG_MGR="nala"
    fi
    spin "Actualizando sistema..."
    run_cmd "update" root $PKG_MGR update || true
    run_cmd "upgrade" root $PKG_MGR upgrade -y || true
    nospin
    log_ok "Sistema actualizado"

    root usermod -aG video,render,audio,plugdev,netdev "$REAL_USER" >>"$LOG_FILE" 2>&1 || true
    log_ok "Usuario agregado a grupos"

    if [ "$(timedatectl show -p Timezone --value)" != "America/Mazatlan" ]; then
        root timedatectl set-timezone America/Mazatlan || true
        log_ok "Zona horaria: America/Mazatlan"
    else
        log_skip "Zona horaria ya configurada"
    fi

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
