#!/bin/bash
# ============================================================
# VoidForge — Post-Instalación para Ubuntu Server
# Gestor: Nala | Base: Wayland + Nautilus + Flatpak
# Entry point principal (renombrado de voidforge.sh → install.sh)
# ============================================================
#
# Uso:
#   sudo bash voidforge.sh                # Menú interactivo
#   sudo bash voidforge.sh --step N       # Paso específico
#   sudo bash voidforge.sh --range N-M    # Rango de pasos
#   sudo bash voidforge.sh --resume       # Reanudar desde checkpoint
#   sudo bash voidforge.sh --all          # Todos los pasos
#
# Instalación rápida:
#   bash <(curl -fsSL https://raw.githubusercontent.com/alexandrpunk/VoidForge/main/boot.sh)
# ============================================================

set -euo pipefail

# Determinar directorio base (funciona tanto como archivo como pipe)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-.}")" 2>/dev/null && pwd || pwd)"

# ──────────────────────────────────────────
# Cargar configuración global
# ──────────────────────────────────────────
source "$SCRIPT_DIR/lib/config.sh"

# ──────────────────────────────────────────
# Cargar helpers
# ──────────────────────────────────────────
source "$SCRIPT_DIR/lib/helpers.sh"

# Ctrl+C: restaurar cursor y salir limpio
trap 'tput cnorm 2>/dev/null || true; echo ""; exit 130' SIGINT

# ──────────────────────────────────────────
# Cargar todos los step files desde install/
# ──────────────────────────────────────────
load_steps() {
    local step_dir="$SCRIPT_DIR/install"
    if [ ! -d "$step_dir" ]; then
        log_error "Directorio install/ no encontrado"
        exit 1
    fi
    while IFS= read -r -d '' file; do
        source "$file"
    done < <(find "$step_dir" -name "*.sh" -type f -print0 2>/dev/null | sort -z)
}
load_steps

# ──────────────────────────────────────────
# Cargar integración Gum
# ──────────────────────────────────────────
source "$SCRIPT_DIR/lib/gum.sh"

# ──────────────────────────────────────────
# Banner
# ──────────────────────────────────────────
print_banner() {
    clear
    echo -e "${C_CYAN}"
    bash "$SCRIPT_DIR/ascii.sh" 2>/dev/null || echo "VoidForge"
    echo -e "${C_GRAY}                      v${VERSION}${C_RESET}"
    echo ""
}

# ──────────────────────────────────────────
# Menú interactivo
# ──────────────────────────────────────────
show_menu() {
    print_banner

    if command -v gum &>/dev/null; then
        local options=(
            "Instalación completa (pasos 0-15)"
            "Reanudar desde último checkpoint"
            "Ejecutar paso específico"
            "Ejecutar rango de pasos"
            "Ver estado actual"
            "Salir"
        )
        choice=$(gum choose "${options[@]}" --height 10 --header "Selecciona una opción:" || echo "Salir")
        case "$choice" in
            "Instalación completa (pasos 0-15)") run_all_steps ;;
            "Reanudar desde último checkpoint") resume_from_checkpoint ;;
            "Ejecutar paso específico") run_specific_step ;;
            "Ejecutar rango de pasos") run_range ;;
            "Ver estado actual") show_status ;;
            *) clear; exit 0 ;;
        esac
    else
        echo -e "${C_WHITE}  ${C_CYAN}[1]${C_RESET}  Instalacion completa pasos 0-15"
        echo -e "${C_WHITE}  ${C_CYAN}[2]${C_RESET}  Reanudar desde último checkpoint"
        echo -e "${C_WHITE}  ${C_CYAN}[3]${C_RESET}  Ejecutar paso específico"
        echo -e "${C_WHITE}  ${C_CYAN}[4]${C_RESET}  Ejecutar rango de pasos"
        echo -e "${C_WHITE}  ${C_CYAN}[5]${C_RESET}  Ver estado actual"
        echo -e "${C_WHITE}  ${C_CYAN}[6]${C_RESET}  Salir"
        echo ""
        echo -ne "${C_WHITE}  Selecciona una opcion [1-6]: ${C_RESET}"
        handle_menu_choice
    fi
}

handle_menu_choice() {
    read -r choice </dev/tty
    case $choice in
        1) run_all_steps ;;
        2) resume_from_checkpoint ;;
        3) run_specific_step ;;
        4) run_range ;;
        5) show_status ;;
        6) clear; exit 0 ;;
        *)
            echo -e "${C_RED}  Opción no válida${C_RESET}"
            sleep 1
            show_menu
            ;;
    esac
}

resume_from_checkpoint() {
    last_step=$(load_checkpoint)
    if [ -n "$last_step" ]; then
        for i in $(seq $((last_step + 1)) "$TOTAL_STEPS"); do
            run_step "$i"
        done
        print_summary
    else
        log_warn "No hay checkpoint. Ejecutando instalación completa..."
        run_all_steps
    fi
}

run_specific_step() {
    if command -v gum &>/dev/null; then
        step=$(gum input --placeholder "Número de paso 0-15" --header "Paso específico")
    else
        echo -ne "${C_WHITE}  Numero de paso 0-15: ${C_RESET}"
        read -r step </dev/tty
    fi
    run_step "$step"
}

run_range() {
    if command -v gum &>/dev/null; then
        range=$(gum input --placeholder "ej: 5-10" --header "Rango de pasos")
    else
        echo -ne "${C_WHITE}  Rango ej: 5-10: ${C_RESET}"
        read -r range </dev/tty
    fi
    start=$(echo "$range" | cut -d- -f1)
    end=$(echo "$range" | cut -d- -f2)
    for i in $(seq "$start" "$end"); do
        run_step "$i"
    done
}

show_status() {
    last_step=$(load_checkpoint)
    if [ -n "$last_step" ]; then
        log_info "Último paso completado: $last_step"
    else
        log_info "No hay checkpoint guardado"
    fi
    if command -v gum &>/dev/null; then
        gum confirm "Presiona Enter para continuar" || true
    else
        echo -ne "${C_WHITE}  Presiona Enter para continuar...${C_RESET}"
        read -r </dev/tty
    fi
    show_menu
}

# ──────────────────────────────────────────
# CLI argument parser
# ──────────────────────────────────────────
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --resume)
                RESUME=true; shift ;;
            --step)
                RESUME=false; clear_checkpoint; SKIP_STEPS=""
                run_step "$2"; shift 2; exit 0 ;;
            --range)
                RESUME=false; clear_checkpoint; SKIP_STEPS=""
                start=$(echo "$2" | cut -d- -f1); end=$(echo "$2" | cut -d- -f2)
                for i in $(seq "$start" "$end"); do run_step "$i"; done
                shift 2; exit 0 ;;
            --skip)
                SKIP_STEPS="$2"; shift 2 ;;
            --all)
                run_all_steps; shift; exit 0 ;;
            *)
                log_error "Opción desconocida: $1"
                echo "Uso: $0 [--resume] [--step N] [--range N-M] [--skip N,M,...] [--all]"
                exit 1 ;;
        esac
    done
}

# ──────────────────────────────────────────
# Función principal
# ──────────────────────────────────────────
main() {
    echo "=== VoidForge v${VERSION} - $(date) ===" > "$LOG_FILE"
    echo "Usuario: $REAL_USER | Home: $HOME_DIR | Script: $SCRIPT_DIR" >> "$LOG_FILE"

    # ── Pantalla de inicio ──
    clear
    echo -e "${C_CYAN}"
    bash "$SCRIPT_DIR/ascii.sh" 2>/dev/null || echo "VoidForge"
    echo -e "${C_GRAY}                      v${VERSION}${C_RESET}"
    echo ""

    # ── Inicialización silenciosa ──
    if ! check_system; then
        echo -e "\n${C_RED}  ❌ Sistema no compatible${C_RESET}"
        exit 1
    fi

    ensure_sudo

    if ! command -v gum &>/dev/null; then
        gum_spin "Preparando interfaz..." install_gum
    fi

    # ── Modo CLI o menú interactivo ──
    if [[ $# -gt 0 ]]; then
        parse_args "$@"
        return
    fi

    show_menu
}

main "$@"

main "$@"
