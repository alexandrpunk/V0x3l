step_6() {
    should_run_step 6 || return 0
    log_step 6 "$TOTAL_STEPS" "Configurando xdg-user-dirs y UFW"

    if [ -d "$HOME_DIR/Documentos" ] || [ -d "$HOME_DIR/Documents" ]; then
        echo -e "${C_YELLOW}   Los directorios de usuario ya existen.${C_RESET}"
        echo -ne "${C_WHITE}   ¿Recrearlos? [s/N]: ${C_RESET}"
        read -r respuesta </dev/tty
        if [[ "$respuesta" =~ ^[Ss]$ ]]; then
            spin "Recreando directorios de usuario..."
            sudo -u "$REAL_USER" rm -rf "$HOME_DIR/Documentos" "$HOME_DIR/Documents" \
                "$HOME_DIR/Descargas" "$HOME_DIR/Downloads" \
                "$HOME_DIR/Escritorio" "$HOME_DIR/Desktop" \
                "$HOME_DIR/Imágenes" "$HOME_DIR/Pictures" \
                "$HOME_DIR/Música" "$HOME_DIR/Music" \
                "$HOME_DIR/Vídeos" "$HOME_DIR/Videos" \
                "$HOME_DIR/Plantillas" "$HOME_DIR/Templates" \
                "$HOME_DIR/Público" "$HOME_DIR/Public" 2>/dev/null || true
            sudo -u "$REAL_USER" xdg-user-dirs-update >>"$LOG_FILE" 2>&1 || log_warn "xdg-user-dirs-update fallo"
            nospin
            log_ok "Directorios de usuario recreados"
        else
            log_skip "Directorios de usuario conservados"
        fi
    else
        spin "Creando directorios de usuario..."
        sudo -u "$REAL_USER" xdg-user-dirs-update >>"$LOG_FILE" 2>&1 || log_warn "xdg-user-dirs-update fallo"
        nospin
        log_ok "Directorios de usuario creados"
    fi

    if ! ufw status 2>/dev/null | grep -q "Status: active"; then
        root ufw default deny incoming >>"$LOG_FILE" 2>&1 || true
        root ufw default allow outgoing >>"$LOG_FILE" 2>&1 || true
        echo "y" | root ufw enable >>"$LOG_FILE" 2>&1 || true
        root ufw allow ssh >>"$LOG_FILE" 2>&1 || true
        log_ok "UFW habilitado (deny incoming, allow outgoing, SSH permitido)"
    else
        if ! ufw status 2>/dev/null | grep -q "22/tcp"; then
            root ufw allow ssh >>"$LOG_FILE" 2>&1 || true
            log_ok "Regla SSH agregada a UFW"
        else
            log_skip "UFW ya esta activo con SSH"
        fi
    fi
    save_checkpoint 6
}
