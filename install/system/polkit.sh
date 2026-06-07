step_5() {
    should_run_step 5 || return 0
    log_step 5 "$TOTAL_STEPS" "Configurando polkit automontaje"

    POLKIT_RULE="/etc/polkit-1/rules.d/90-udisks2-automount.rules"
    if [ ! -f "$POLKIT_RULE" ]; then
        root mkdir -p /etc/polkit-1/rules.d || true
        root tee "$POLKIT_RULE" > /dev/null <<'POLKIT' || true
polkit.addRule(function(action, subject) {
    if ((action.id == "org.freedesktop.udisks2.filesystem-mount" ||
         action.id == "org.freedesktop.udisks2.filesystem-mount-system") &&
        subject.isInGroup("plugdev")) {
        return polkit.Result.YES;
    }
});
POLKIT
        log_ok "Regla polkit automontaje creada"
    else
        log_skip "Regla polkit ya existe"
    fi
    save_checkpoint 5
}
