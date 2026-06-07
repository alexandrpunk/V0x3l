step_10() {
    should_run_step 10 || return 0
    log_step 10 "$TOTAL_STEPS" "Configurando optimización energética (TLP)"

    TLP_CONF="/etc/tlp.d/01-voidforge.conf"
    if [ ! -f "$TLP_CONF" ]; then
        root mkdir -p /etc/tlp.d || true
        root tee "$TLP_CONF" > /dev/null <<'TLP' || true
TLP_ENABLE=1
CPU_SCALING_GOVERNOR_ON_AC=powersave
CPU_SCALING_GOVERNOR_ON_BAT=powersave
CPU_ENERGY_PERF_POLICY_ON_AC=balance_performance
CPU_ENERGY_PERF_POLICY_ON_BAT=power
CPU_MIN_PERF_ON_AC=0
CPU_MAX_PERF_ON_AC=100
CPU_MIN_PERF_ON_BAT=0
CPU_MAX_PERF_ON_BAT=80
CPU_BOOST_ON_AC=1
CPU_BOOST_ON_BAT=0
INTEL_GPU_MIN_FREQ_ON_AC=0
INTEL_GPU_MIN_FREQ_ON_BAT=0
INTEL_GPU_MAX_FREQ_ON_AC=0
INTEL_GPU_MAX_FREQ_ON_BAT=0
INTEL_GPU_BOOST_ON_AC=1
INTEL_GPU_BOOST_ON_BAT=0
PCIE_ASPM_ON_AC=powersupersave
PCIE_ASPM_ON_BAT=powersupersave
RAID_DEVICE_POWER_MGMT_ON_AC=auto
RAID_DEVICE_POWER_MGMT_ON_BAT=auto
WIFI_PWR_ON_AC=off
WIFI_PWR_ON_BAT=on
SOUND_POWER_SAVE_ON_AC=1
SOUND_POWER_SAVE_ON_BAT=1
SOUND_POWER_SAVE_CONTROLLER=Y
USB_AUTOSUSPEND=1
USB_BLACKLIST_WWAN=1
RESTORE_THRESHOLDS_ON_BAT=1
NATACPI_ENABLE=1
TPACPI_ENABLE=1
TPSMAPI_ENABLE=1
TLP
        run_cmd "enable tlp" root systemctl enable tlp || true
        log_ok "TLP configurado y habilitado"
    else
        log_skip "TLP ya configurado"
    fi

    LOGIND="/etc/systemd/logind.conf"
    grep -q "^HandleLidSwitch=suspend$" "$LOGIND" || root sed -i 's/^#HandleLidSwitch=.*/HandleLidSwitch=suspend/' "$LOGIND" || true
    grep -q "^HandleLidSwitchExternalPower=suspend$" "$LOGIND" || root sed -i 's/^#HandleLidSwitchExternalPower=.*/HandleLidSwitchExternalPower=suspend/' "$LOGIND" || true
    grep -q "^HandleLidSwitchDocked=ignore$" "$LOGIND" || root sed -i 's/^#HandleLidSwitchDocked=.*/HandleLidSwitchDocked=ignore/' "$LOGIND" || true
    grep -q "^PowerKeyAction=poweroff$" "$LOGIND" || root sed -i 's/^#PowerKeyAction=.*/PowerKeyAction=poweroff/' "$LOGIND" || true
    log_ok "logind configurado (lid switch, power key)"
    save_checkpoint 10
}
