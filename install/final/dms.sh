step_15() {
    should_run_step 15 || return 0
    log_step 15 "$TOTAL_STEPS" "Instalando DMS (Dank Linux)"
    log_info "Ejecutando asistente de instalación DMS..."
    run_cmd "DMS installer" sudo -u "$REAL_USER" bash -c "curl -fsSL https://install.danklinux.com | sh" || true
    save_checkpoint 15
}
