step_0() {
    should_run_step 0 || return 0
    log_step 0 "$TOTAL_STEPS" "Instalando herramientas base"
    spin "Instalando herramientas base..."
    run_cmd "apt update" root apt update || true
    run_cmd "apt install base" root apt install -y nala wget tar unzip file zsh git curl ca-certificates pciutils locales gnupg software-properties-common || true
    nospin
    log_ok "Herramientas base instaladas (nala, wget, git, curl, zsh, pciutils, locales)"
    save_checkpoint 0
}
