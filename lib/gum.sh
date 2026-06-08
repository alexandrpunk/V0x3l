# ============================================================
# VoidForge — Gum integration
# ============================================================

GUM_VERSION="0.17.0"

install_gum() {
    if command -v gum &>/dev/null; then
        return 0
    fi

    log_info "Instalando Gum para interfaz mejorada..."
    local arch
    case "$(uname -m)" in
        x86_64)  arch="amd64" ;;
        aarch64) arch="arm64" ;;
        *) log_warn "Arquitectura no soportada por Gum, usando interfaz texto"; return 1 ;;
    esac

    (
        cd /tmp
        curl -fsSL --max-time 30 -o gum.deb "https://github.com/charmbracelet/gum/releases/download/v${GUM_VERSION}/gum_${GUM_VERSION}_${arch}.deb" 2>/dev/null
        if [ -f gum.deb ]; then
            root apt install -y --allow-downgrades ./gum.deb 2>/dev/null || true
            rm -f gum.deb
        fi
    ) || true

    if command -v gum &>/dev/null; then
        log_ok "Gum instalado correctamente"
    else
        log_warn "No se pudo instalar Gum, usando interfaz texto"
    fi
}

gum_spin() {
    local title="$1"; shift
    if command -v gum &>/dev/null; then
        gum spin --spinner dot --title "$title" -- "$@" || true
    else
        spin "$title"
        eval "$@"
        nospin
    fi
}

gum_confirm() {
    if command -v gum &>/dev/null; then
        gum confirm "$1" 2>/dev/null
    else
        echo -e -n "${C_WHITE}  ¿$1? [s/N]: ${C_RESET}"
        read -r respuesta </dev/tty
        [[ "$respuesta" =~ ^[sSyY] ]]
    fi
}

gum_style() {
    if command -v gum &>/dev/null; then
        gum style "$@"
    else
        local foreground=""
        local text=""
        while [[ $# -gt 0 ]]; do
            case $1 in
                --foreground) shift; foreground="$1" ;;
                *) text="$text $1" ;;
            esac
            shift
        done
        echo -e "$text"
    fi
}
