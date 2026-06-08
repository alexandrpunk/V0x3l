step_14() {
    should_run_step 14 || return 0
    log_step 14 "$TOTAL_STEPS" "Configurando Plymouth y GRUB"

    # ── Plymouth theme ──
    run_cmd "nala install plymouth" root nala install -y plymouth plymouth-themes || true
    root mkdir -p /usr/share/plymouth/themes || true

    PLYMOUTH_THEME_SET=false
    PLYMOUTH_THEME_DIR="/usr/share/plymouth/themes/$PLYMOUTH_THEME_NAME"

    # Prioridad 1: assets/ (tema pre-extraído en el repo)
    if [ -d "$PLYMOUTH_THEME_SRC" ] && [ -f "$PLYMOUTH_THEME_SRC/$PLYMOUTH_THEME_NAME.plymouth" ]; then
        if [ ! -d "$PLYMOUTH_THEME_DIR" ] || [ ! -f "$PLYMOUTH_THEME_DIR/$PLYMOUTH_THEME_NAME.plymouth" ]; then
            root cp -r "$PLYMOUTH_THEME_SRC/" "$PLYMOUTH_THEME_DIR/" 2>/dev/null || true
        fi
        if [ -f "$PLYMOUTH_THEME_DIR/$PLYMOUTH_THEME_NAME.plymouth" ]; then
            run_cmd "update-alternatives install" root update-alternatives --install /usr/share/plymouth/themes/default.plymouth default.plymouth "$PLYMOUTH_THEME_DIR/$PLYMOUTH_THEME_NAME.plymouth" 100 || true
            run_cmd "update-alternatives set" root update-alternatives --set default.plymouth "$PLYMOUTH_THEME_DIR/$PLYMOUTH_THEME_NAME.plymouth" || true
            if update-alternatives --query default.plymouth 2>/dev/null | grep -q "Value: $PLYMOUTH_THEME_DIR/$PLYMOUTH_THEME_NAME.plymouth"; then
                log_ok "Tema Plymouth: $PLYMOUTH_THEME_NAME"
                PLYMOUTH_THEME_SET=true
            else
                log_warn "Tema Plymouth copiado pero update-alternatives fallo"
            fi
        fi
    fi

    # Prioridad 2: fallback a ZIP local o descarga por URL
    if [ "$PLYMOUTH_THEME_SET" = false ]; then
        PLYMOUTH_ZIP_PATH="$SCRIPT_DIR/$PLYMOUTH_ZIP_NAME"
        if [ ! -f "$PLYMOUTH_ZIP_PATH" ] && [ -n "$PLYMOUTH_ZIP_URL" ]; then
            log_info "Descargando tema Plymouth..."
            if command -v curl &>/dev/null; then
                run_cmd "curl plymouth" curl -fsSL -o "/tmp/$PLYMOUTH_ZIP_NAME" "$PLYMOUTH_ZIP_URL" || true
            elif command -v wget &>/dev/null; then
                run_cmd "wget plymouth" wget -q -O "/tmp/$PLYMOUTH_ZIP_NAME" "$PLYMOUTH_ZIP_URL" || true
            fi
            [ -f "/tmp/$PLYMOUTH_ZIP_NAME" ] && PLYMOUTH_ZIP_PATH="/tmp/$PLYMOUTH_ZIP_NAME"
        fi
        if [ -f "$PLYMOUTH_ZIP_PATH" ]; then
            TEMP_DIR=$(mktemp -d)
            run_cmd "unzip plymouth" unzip -q "$PLYMOUTH_ZIP_PATH" -d "$TEMP_DIR" || true
            PLYMOUTH_FILE=$(find "$TEMP_DIR" -name "*.plymouth" -type f 2>/dev/null | head -n 1)
            if [ -n "$PLYMOUTH_FILE" ]; then
                THEME_NAME=$(basename "$PLYMOUTH_FILE" .plymouth)
                DEST_DIR="/usr/share/plymouth/themes/$THEME_NAME"
                root mkdir -p "$DEST_DIR" || true
                root cp -r "$(dirname "$PLYMOUTH_FILE")/." "$DEST_DIR/" 2>/dev/null || true
                if [ -f "$DEST_DIR/$THEME_NAME.plymouth" ]; then
                    run_cmd "update-alternatives install" root update-alternatives --install /usr/share/plymouth/themes/default.plymouth default.plymouth "$DEST_DIR/$THEME_NAME.plymouth" 100 || true
                    run_cmd "update-alternatives set" root update-alternatives --set default.plymouth "$DEST_DIR/$THEME_NAME.plymouth" || true
                    log_ok "Tema Plymouth: $THEME_NAME"
                    PLYMOUTH_THEME_SET=true
                else
                    log_warn "Tema Plymouth: no se encontro .plymouth en el ZIP"
                fi
            else
                log_warn "No se encontro archivo .plymouth en el ZIP"
            fi
            rm -rf "$TEMP_DIR"
        else
            log_warn "No se encontro tema Plymouth en assets, local ni URL"
        fi
    fi

    if [ "$PLYMOUTH_THEME_SET" = false ]; then
        log_info "Plymouth usara tema por defecto del sistema"
    fi

    GRUB_THEME_PATH="/usr/share/grub/themes/grub-theme-vimix-very-dark-blue"
    if [ ! -f "$GRUB_THEME_PATH/theme.txt" ]; then
        GRUB_TMP_DIR="$(mktemp --directory)"
        run_cmd "git clone GRUB theme" git clone --depth 1 https://github.com/trueNAHO/grub2-theme-vimix-very-dark-blue.git "$GRUB_TMP_DIR" || true
        root install --directory --mode 755 "$GRUB_THEME_PATH" || true
        root cp --no-preserve=ownership --recursive "$GRUB_TMP_DIR/src/." "$GRUB_THEME_PATH" || true
        rm -rf "$GRUB_TMP_DIR"
        log_ok "Tema GRUB: Vimix Very Dark Blue"
    else
        log_skip "Tema GRUB ya instalado"
    fi

    GRUB_CFG="/etc/default/grub"
    if [ "$HAS_NVIDIA_GPU" -eq 1 ]; then
        log_info "Agregando parámetros de kernel para NVIDIA..."
        grep -q "nvidia-drm.modeset=1" "$GRUB_CFG" || root sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="quiet"/GRUB_CMDLINE_LINUX_DEFAULT="quiet splash nvidia-drm.modeset=1 nvidia-drm.fbdev=1 nvidia.NVreg_PreserveVideoMemoryAllocations=1/' "$GRUB_CFG" || true
    else
        grep -q "GRUB_CMDLINE_LINUX_DEFAULT=.*splash" "$GRUB_CFG" || root sed -i 's/^GRUB_CMDLINE_LINUX_DEFAULT="/GRUB_CMDLINE_LINUX_DEFAULT="quiet splash plymouth:force-recovery splash=/' "$GRUB_CFG" || true
    fi
    grep -q "GRUB_GFXPAYLOAD_LINUX=keep" "$GRUB_CFG" || root sh -c "echo 'GRUB_GFXPAYLOAD_LINUX=keep' >> \"$GRUB_CFG\"" 2>/dev/null || true
    { grep -q "^GRUB_THEME=" "$GRUB_CFG" \
        && root sed -i "s|^GRUB_THEME=.*|GRUB_THEME=\"$GRUB_THEME_PATH/theme.txt\"|" "$GRUB_CFG" \
        || root sh -c "echo \"GRUB_THEME=\\\"$GRUB_THEME_PATH/theme.txt\\\"\" >> \"$GRUB_CFG\""; } || true
    log_ok "Configuración GRUB actualizada"

    root mkdir -p /etc/initramfs-tools/conf.d || true
    root sh -c "echo 'FRAMEBUFFER=y' > /etc/initramfs-tools/conf.d/splash" 2>/dev/null || true
    if [ "$HAS_NVIDIA_GPU" -eq 1 ]; then
        for mod in nvidia nvidia-drm nvidia-modeset nvidia-uvm; do
            root sh -c "echo '$mod' >> /etc/initramfs-tools/modules" 2>/dev/null || true
        done
        log_info "Módulos NVIDIA agregados a initramfs"
    else
        root sh -c "echo 'drm' >> /etc/initramfs-tools/modules" 2>/dev/null || true
    fi

    run_cmd "grub-mkconfig" root grub-mkconfig -o /boot/grub/grub.cfg || true
    run_cmd "update-initramfs" root update-initramfs -u || true
    log_ok "GRUB e initramfs regenerados"

    run_cmd "nala autoremove" root nala autoremove -y || true
    run_cmd "nala clean" root nala clean || true
    log_ok "Paquetes huérfanos eliminados, caché limpiada"
    save_checkpoint 14
}
