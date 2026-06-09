#!/usr/bin/env python3
# VoidForge UI Demo — interfaz ANSI con colores
# Funciona en TTY puro, SSH, terminal grafico
# Uso: python3 demo_ui.py

import sys
import os
import time
import re as _re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["LOG_FILE"] = "/dev/null"

from voidforge.config import VERSION


# ── ANSI helpers ──

class C:
    """Colores ANSI mapeados desde colores."""
    # #74BF04 primary brilliant green
    green = "\033[1;32m"
    # #467302 tertiary dark green
    dgreen = "\033[0;32m"
    # #D1C6B2 secondary dark beige
    beige = "\033[1;33m"
    # #DCD2BF text light beige
    white = "\033[1;37m"
    # #534E48 background/text dark
    gray = "\033[2;37m"
    red = "\033[1;31m"
    cyan = "\033[1;36m"
    reset = "\033[0m"
    bold = "\033[1m"


# Datos para simulaciones
NALA_OUT = [
    ("downloading", 0.05,
     ["Leyendo listas de paquetes...",
      "Descargando libwayland-client0 (0.8 MB) [1%]",
      "Descargando libegl1 (0.2 MB) [5%]",
      "Descargando libgl1-mesa-dri (8.2 MB) [12%]",
      "Descargando xwayland (1.5 MB) [18%]",
      "Descargando nautilus (2.3 MB) [25%]",
      "Descargando pipewire (3.6 MB) [35%]",
      "Descargando flatpak (6.8 MB) [48%]",
      "Descargando neovim (4.2 MB) [58%]",
      "Descargando bluez (5.2 MB) [68%]",
      "Descargando ubuntu-restricted-extras (2.9 MB) [78%]",
      "Fetched 45.8 MB in 12s (3.8 MB/s)"]),
    ("extracting", 0.08,
     ["Extrayendo libwayland-client0 (1/30)...",
      "Extrayendo libgl1-mesa-dri (4/30)...",
      "Extrayendo xwayland (6/30)...",
      "Extrayendo nautilus (7/30)...",
      "Extrayendo pipewire (9/30)...",
      "Extrayendo wireplumber (10/30)...",
      "Extrayendo flatpak (11/30)...",
      "Extrayendo neovim (12/30)..."]),
    ("configuring", 0.1,
     ["Configurando libwayland-client0 (17/30)...",
      "Configurando libgl1-mesa-dri (20/30)...",
      "Configurando xwayland (22/30)...",
      "Configurando nautilus (23/30)...",
      "Configurando pipewire (24/30)...",
      "Configurando wireplumber (25/30)...",
      "Configurando flatpak (26/30)...",
      "Configurando neovim (28/30)...",
      "Procesando disparadores..."]),
]


def clear():
    os.system("clear" if os.name == "posix" else "cls")


def header(title="Menu"):
    clear()
    bar = C.green + "\u2500" * 60 + C.reset
    print(f"\n{C.green} VoidForge.sh : {title}{C.reset}")
    print(bar)


def progress_bar(pct, width=20):
    """Barra de progreso ANSI."""
    done = int(pct * width)
    bar = C.green + "\u2588" * done + C.gray + "\u2588" * (width - done) + C.reset
    return f"  [{bar}] {int(pct * 100)}%"


def simulate_packages():
    """Simula instalacion con barra de progreso."""
    header("Paso 4/15 - Instalando paquetes del sistema")

    total_lines = sum(len(lines) for _, _, lines in NALA_OUT)
    current = 0

    for phase, delay, lines in NALA_OUT:
        for line in lines:
            current += 1
            pct = current / total_lines

            clear()
            header("Paso 4/15 - Instalando paquetes del sistema")
            print()
            print(f"   {C.cyan}\u2B9C Instalando paquetes...{C.reset}")
            print()
            print(f"   {progress_bar(pct)}")
            if phase == "downloading":
                counter = f"{current}/{total_lines} paquetes"
            elif phase == "extracting":
                counter = f"Extrayendo {current}/{total_lines}"
            else:
                counter = f"Configurando {current}/{total_lines}"
            print(f"   {C.gray}{counter}{C.reset}")
            print()
            print(f"   {C.white}{line}{C.reset}")
            print(f"\n{C.gray} Ctrl+C cancelar | Log: /tmp/voidforge.log{C.reset}")
            time.sleep(delay)


def run_step(num, total, title, lines, delay=0.1):
    """Muestra un paso simple con lineas de progreso."""
    for line in lines:
        clear()
        header(f"Paso {num}/{total} - {title}")
        print(f"\n   {C.cyan}{line}{C.reset}")
        time.sleep(delay)
    print(f"\n   {C.green}[OK]{C.reset} Paso {num} completado")
    time.sleep(0.5)


def show_menu():
    while True:
        header("Demo VoidForge")
        print()
        print(f"   {C.white}(1){C.reset} Instalacion completa (pasos 0-15)")
        print(f"   {C.white}(2){C.reset} Reanudar desde ultimo checkpoint")
        print(f"   {C.white}(3){C.reset} Ejecutar paso especifico")
        print(f"   {C.white}(4){C.reset} Ejecutar rango de pasos")
        print(f"   {C.white}(5){C.reset} Ver estado actual")
        print(f"   {C.white}(6){C.reset} Salir")
        print(f"\n{C.gray} \u2191\u2193 navegar | Enter elegir | Ctrl+C salir{C.reset}")
        print()

        try:
            choice = input(f"  {C.white}Selecciona [1-6]: {C.reset}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n  {C.gray}Adios.{C.reset}")
            break

        if choice == "1":
            # Simular pasos
            run_step(0, 15, "Preparando entorno",
                    ["Instalando nala...", "Instalando git...", "Instalando curl, zsh...", "OK."])
            run_step(1, 15, "Configurando repositorios",
                    ["ButterRepo agregado.", "PPAs DMS agregados.", "Sistema actualizado."])
            run_step(2, 15, "Instalando Kernel XanMod",
                    ["Agregando repositorio XanMod...", "linux-xanmod-x64v3 instalado."])
            run_step(3, 15, "Detectando GPU NVIDIA",
                    ["Buscando GPU...", "Sin GPU NVIDIA detectada."])

            # Simular mega install con barra de progreso
            simulate_packages()

            # Pasos restantes rapidos
            for num, title, lines in [
                (5, "Configurando polkit automontaje", ["Regla polkit creada."]),
                (6, "Configurando xdg-user-dirs y UFW", ["Directorios creados.", "UFW habilitado."]),
                (7, "Configurando red", ["NetworkManager habilitado.", "Netplan configurado."]),
                (8, "Configurando Flatpak", ["Flathub agregado.", "Apps instaladas."]),
                (9, "Habilitando servicios", ["Servicios iniciados.", "Entorno Wayland configurado."]),
                (10, "Configurando TLP", ["TLP habilitado.", "logind configurado."]),
                (11, "Configurando Oh My Zsh", ["Zsh instalado.", "Tema: agnoster."]),
                (12, "Instalando LazyVim", ["LazyVim clonado."]),
                (13, "Instalando Colloid icons", ["Tema instalado."]),
                (14, "Configurando Plymouth y GRUB", ["Tema instalado.", "GRUB regenerado."]),
            ]:
                run_step(num, 15, title, lines, delay=0.08)

            # Resumen final
            header("Instalacion completada!")
            print()
            print(f"   {C.green}[OK]{C.reset} Todos los pasos completados\n")
            resumen = [
                "Kernel: XanMod Edge",
                "Wayland + Nautilus + PipeWire",
                "Flatpak + Oh My Zsh + LazyVim",
                "Plymouth + GRUB Vimix",
                "TLP + UFW configurados",
                "DMS (Dank Linux)",
            ]
            for r in resumen:
                print(f"     {C.white}+{C.reset} {r}")
            print(f"\n   {C.gray}Log: /tmp/voidforge.log{C.reset}")
            print(f"\n   {C.green}Tu sistema esta listo!{C.reset}")
            input(f"\n{C.gray}   Enter para continuar...{C.reset}")

        elif choice == "3":
            header("Ejecutar paso especifico")
            step = input(f"\n  {C.white}Numero de paso 0-15: {C.reset}")
            print(f"\n  {C.gray}Paso {step} ejecutado.{C.reset}")
            time.sleep(1)

        elif choice == "6":
            print(f"\n  {C.green}Hasta luego!{C.reset}")
            break

        else:
            print(f"\n  {C.red}[ERR] Opcion invalida{C.reset}")
            time.sleep(0.5)


if __name__ == "__main__":
    print(f"{C.green}VoidForge Demo - Interfaz ANSI{C.reset}")
    print(f"{C.gray}  Iniciando...{C.reset}")
    time.sleep(1)
    show_menu()
