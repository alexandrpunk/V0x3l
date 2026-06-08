step_15() {
    should_run_step 15 || return 0
    log_step 15 "$TOTAL_STEPS" "Instalando DMS (Dank Linux)"
    if run_cmd "DMS installer" sudo -u "$REAL_USER" bash -c "curl -fsSL https://install.danklinux.com | bash"; then
        log_ok "Instalacion DMS completada"
    else
        log_warn "El instalador DMS reporto un error (revisa /tmp/voidforge.log)"
    fi
    save_checkpoint 15
}
