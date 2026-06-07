step_7() {
    should_run_step 7 || return 0
    log_step 7 "$TOTAL_STEPS" "Configurando red y optimizando boot"

    if ! systemctl is-masked systemd-networkd-wait-online.service 2>/dev/null; then
        run_cmd "disable wait-online" root systemctl disable systemd-networkd-wait-online.service || true
        run_cmd "mask wait-online" root systemctl mask systemd-networkd-wait-online.service || true
        log_ok "systemd-networkd-wait-online desactivado (evita bloqueos de 5 min)"
    else
        log_skip "systemd-networkd-wait-online ya desactivado"
    fi

    ACTIVE_IFACE=$(ip route show default 2>/dev/null | awk '{print $5}' | head -n 1)
    if [ -z "$ACTIVE_IFACE" ]; then
        ACTIVE_IFACE=$(ip -o link show 2>/dev/null | awk -F': ' '{print $2}' | grep -E '^en|^eth' | head -n 1)
    fi
    if [ -n "$ACTIVE_IFACE" ]; then
        log_info "Interfaz de red detectada: $ACTIVE_IFACE"
    else
        log_warn "No se pudo detectar la interfaz de red, usando configuracion generica"
    fi

    if ! systemctl is-active NetworkManager >/dev/null 2>&1; then
        run_cmd "enable NetworkManager" root systemctl enable --now NetworkManager || true
        log_ok "NetworkManager habilitado e iniciado"
    else
        log_skip "NetworkManager ya esta activo"
    fi

    NETPLAN_DIR="/etc/netplan"
    NETPLAN_FILE="$NETPLAN_DIR/01-netcfg.yaml"
    if [ ! -f "$NETPLAN_FILE" ] || ! grep -q "NetworkManager" "$NETPLAN_FILE"; then
        if [ -f "$NETPLAN_FILE" ]; then
            root cp "$NETPLAN_FILE" "${NETPLAN_FILE}.bak-$(date +%Y%m%d-%H%M%S)" 2>/dev/null || true
            log_info "Backup del netplan original creado"
        fi
        root rm -f "$NETPLAN_DIR"/*.yaml.bak 2>/dev/null || true
        root tee "$NETPLAN_FILE" > /dev/null <<NETPLAN || true
network:
  version: 2
  renderer: NetworkManager
NETPLAN
        if [ -n "$ACTIVE_IFACE" ]; then
            root tee -a "$NETPLAN_FILE" > /dev/null <<NETPLAN || true
  ethernets:
    $ACTIVE_IFACE:
      dhcp4: true
NETPLAN
        fi
        run_cmd "netplan apply" root netplan apply || true
        log_ok "Netplan configurado (renderer: NetworkManager)"
        if command -v nmcli >/dev/null 2>&1 && [ -n "$ACTIVE_IFACE" ]; then
            sleep 3
            if nmcli device status 2>/dev/null | grep -q "$ACTIVE_IFACE"; then
                log_info "NetworkManager gestionando $ACTIVE_IFACE"
            fi
        fi
    else
        log_skip "Netplan ya configurado"
    fi
    save_checkpoint 7
}
