step_3() {
    should_run_step 3 || return 0
    log_step 3 "$TOTAL_STEPS" "Detectando GPU NVIDIA e instalando drivers"

    if command -v lspci >/dev/null 2>&1; then
        HAS_NVIDIA=0; HAS_INTEL=0
        lspci -nn 2>/dev/null | grep -qi "nvidia" && HAS_NVIDIA=1
        lspci -nn 2>/dev/null | grep -qi "vga.*intel" && HAS_INTEL=1

        if [ "$HAS_NVIDIA" -eq 1 ]; then
            spin "Actualizando repositorios..."
            run_cmd "nala update" root nala update || true
            nospin

            if [ "$HAS_INTEL" -eq 1 ]; then
                log_info "Detectado sistema hibrido Intel + NVIDIA"
                spin "Instalando driver NVIDIA 595-open + prime..."
                run_cmd "nala install nvidia+prime" root nala install -y nvidia-driver-595-open nvidia-prime nvidia-settings || true
                nospin
                root prime-select on-demand >>"$LOG_FILE" 2>&1 || true
                HAS_NVIDIA_GPU=1
                log_ok "Driver NVIDIA 595-open + prime instalados (usa prime-run para GPU discreta)"
            else
                log_info "Detectada solo NVIDIA"
                spin "Instalando driver NVIDIA 595-open..."
                run_cmd "nala install nvidia" root nala install -y nvidia-driver-595-open nvidia-settings || true
                nospin
                HAS_NVIDIA_GPU=1
                log_ok "Driver NVIDIA 595-open instalado"
            fi

            for svc in nvidia-suspend nvidia-resume nvidia-hibernate; do
                root systemctl enable "$svc" >>"$LOG_FILE" 2>&1 || true
            done
            log_ok "Servicios suspend/resume NVIDIA habilitados"
        else
            log_skip "Sin GPU NVIDIA detectada"
        fi
    else
        log_warn "lspci no disponible, omitiendo deteccion"
    fi

    save_checkpoint 3
}
