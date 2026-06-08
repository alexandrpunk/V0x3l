step_2() {
    should_run_step 2 || return 0
    log_step 2 "$TOTAL_STEPS" "Instalando Kernel XanMod"

    if [ ! -f /etc/apt/sources.list.d/xanmod-release.list ]; then
        run_cmd "nala install lsb-release" root nala install --no-install-recommends -y lsb-release || true
        wget -qO - https://dl.xanmod.org/archive.key | root gpg --dearmor -vo /etc/apt/keyrings/xanmod-archive-keyring.gpg >>"$LOG_FILE" 2>&1 || true
        echo "deb [signed-by=/etc/apt/keyrings/xanmod-archive-keyring.gpg] https://deb.xanmod.org $(lsb_release -sc) main non-free" | root tee /etc/apt/sources.list.d/xanmod-release.list >>"$LOG_FILE" 2>&1 || true
        log_ok "Repositorio XanMod agregado"
    fi

    if ! uname -r 2>/dev/null | grep -q "xanmod"; then
        run_cmd "nala update" root nala update || true
        run_cmd "nala install xanmod" root nala install -y linux-xanmod-x64v3 || true
        run_cmd "nala install dkms" root nala install --no-install-recommends -y dkms libelf-dev clang lld llvm || true
        log_ok "Kernel XanMod x64v3 instalado (requiere reinicio para aplicar)"
    else
        log_skip "XanMod ya instalado"
    fi

    save_checkpoint 2
}
