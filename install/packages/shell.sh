step_11() {
    should_run_step 11 || return 0
    log_step 11 "$TOTAL_STEPS" "Configurando Oh My Zsh con tema agnoster"

    if [ "$(getent passwd "$REAL_USER" 2>/dev/null | cut -d: -f7)" != "$(which zsh)" ]; then
        root chsh -s "$(which zsh)" "$REAL_USER" >>"$LOG_FILE" 2>&1 || true
        log_ok "Shell por defecto: zsh"
    fi

    if [ ! -d "$HOME_DIR/.oh-my-zsh" ]; then
        if sudo -u "$REAL_USER" bash -c '
            sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
            sed -i "s/^ZSH_THEME=.*/ZSH_THEME=\"agnoster\"/" "$HOME/.zshrc"
        ' >>"$LOG_FILE" 2>&1; then
 log_ok "Oh My Zsh instalado, tema: agnoster"
        else
 log_warn "Oh My Zsh no se pudo instalar (sin conexion o error de descarga)"
        fi
    else
        echo -e "${C_YELLOW}   Oh My Zsh ya esta instalado.${C_RESET}"
        echo -ne "${C_WHITE}   ¿Reinstalar? [s/N]: ${C_RESET}"
        read -r respuesta </dev/tty
        if [[ "$respuesta" =~ ^[Ss]$ ]]; then
            sudo -u "$REAL_USER" rm -rf "$HOME_DIR/.oh-my-zsh" 2>/dev/null || true
            if sudo -u "$REAL_USER" bash -c '
                sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
                sed -i "s/^ZSH_THEME=.*/ZSH_THEME=\"agnoster\"/" "$HOME/.zshrc"
            ' >>"$LOG_FILE" 2>&1; then
 log_ok "Oh My Zsh reinstalado, tema: agnoster"
            else
 log_warn "Oh My Zsh no se pudo reinstalar"
            fi
        else
            sudo -u "$REAL_USER" sed -i "s/^ZSH_THEME=.*/ZSH_THEME=\"agnoster\"/" "$HOME_DIR/.zshrc" >>"$LOG_FILE" 2>&1 || true
            log_skip "Oh My Zsh conservado"
        fi
    fi
    save_checkpoint 11
}
