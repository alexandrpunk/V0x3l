step_12() {
    should_run_step 12 || return 0
    log_step 12 "$TOTAL_STEPS" "Instalando LazyVim"

    LAZYVIM_DIR="$HOME_DIR/.config/nvim"
    LAZYVIM_INSTALLED=false
    if [ -f "$LAZYVIM_DIR/init.lua" ] && grep -q "LazyVim" "$LAZYVIM_DIR/init.lua" 2>/dev/null; then
        LAZYVIM_INSTALLED=true
    fi

    if [ "$LAZYVIM_INSTALLED" = true ]; then
        echo -e "${C_YELLOW}   LazyVim ya esta instalado.${C_RESET}"
        echo -ne "${C_WHITE}   ¿Reinstalar? [s/N]: ${C_RESET}"
        read -r respuesta
        if [[ "$respuesta" =~ ^[Ss]$ ]]; then
            LAZYVIM_INSTALLED=false
        fi
    fi

    if [ "$LAZYVIM_INSTALLED" = false ]; then
        spin "Instalando LazyVim..."
        sudo -u "$REAL_USER" bash -c "
            mv ~/.config/nvim ~/.config/nvim.bak 2>/dev/null || true
            mv ~/.local/share/nvim ~/.local/share/nvim.bak 2>/dev/null || true
            mv ~/.local/state/nvim ~/.local/state/nvim.bak 2>/dev/null || true
            mv ~/.cache/nvim ~/.cache/nvim.bak 2>/dev/null || true
            git clone https://github.com/LazyVim/starter ~/.config/nvim 2>/dev/null
            rm -rf ~/.config/nvim/.git 2>/dev/null || true
        " >>"$LOG_FILE" 2>&1
        nospin
        log_ok "LazyVim instalado (ejecuta 'nvim' para completar la configuracion)"
    else
        log_skip "LazyVim conservado"
    fi
    save_checkpoint 12
}
