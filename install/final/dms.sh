step_15() {
    should_run_step 15 || return 0
    log_step 15 "$TOTAL_STEPS" "Instalando DMS (Dank Linux)"
    spin "Instalando DMS..."
    run_cmd "DMS installer" sudo -u "$REAL_USER" bash -c "curl -fsSL https://install.danklinux.com | bash" || true
    nospin
    log_ok "Instalacion DMS completada"
    save_checkpoint 15
}
