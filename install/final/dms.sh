step_15() {
    should_run_step 15 || return 0
    log_step 15 "$TOTAL_STEPS" "Instalando DMS (Dank Linux)"
    spin "Instalando DMS..."
    if run_cmd "DMS installer" sudo -u "$REAL_USER" bash -c "curl -fsSL https://install.danklinux.com | bash"; then
        nospin
        log_ok "Instalacion DMS completada"
    else
        nospin
        log_warn "El instalador DMS reporto un error (revisa /tmp/voidforge.log)"
    fi
    save_checkpoint 15
}
