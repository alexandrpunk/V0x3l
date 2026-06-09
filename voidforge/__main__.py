#!/usr/bin/env python3
# VoidForge v2 - Entry point (interfaz ANSI)
# Funciona en TTY puro, SSH, terminal grafico

import sys
import os
import subprocess
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voidforge.config import LOG_FILE, VERSION, TOTAL_STEPS


# ── ANSI Colores (desde colores) ──

class C:
    green = "\033[1;32m"     # #74BF04
    dgreen = "\033[0;32m"    # #467302
    white = "\033[1;37m"     # #DCD2BF
    gray = "\033[2;37m"      # #534E48
    beige = "\033[1;33m"     # #D1C6B2
    red = "\033[1;31m"
    cyan = "\033[1;36m"
    reset = "\033[0m"
    bold = "\033[1m"


def cls():
    os.system("clear" if os.name == "posix" else "cls")


def header(title: str):
    cls()
    print(f"\n{C.green} VoidForge.sh : {title}{C.reset}")
    print(f"{C.gray}{'\u2500' * 60}{C.reset}")


def run_cmd(desc: str, *args: str, sudo: bool = False) -> bool:
    """Ejecuta comando con output en vivo."""
    display_desc = desc
    cmd = list(args)
    if sudo and os.geteuid() != 0:
        cmd = ["sudo"] + cmd
    print(f"   {C.gray}-> {display_desc}{C.reset}")
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1
        )
        for line in proc.stdout:
            line = line.rstrip()
            print(f"   {line}")
        proc.wait()
        return proc.returncode == 0
    except FileNotFoundError:
        print(f"   {C.red}[ERR] Comando no encontrado: {args[0]}{C.reset}")
        return False
    except Exception as e:
        print(f"   {C.red}[ERR] {e}{C.reset}")
        return False


def ok(msg: str):
    print(f"   {C.green}[OK]{C.reset} {msg}")


def warn(msg: str):
    print(f"   {C.beige}[!]{C.reset} {msg}")


def err(msg: str):
    print(f"   {C.red}[ERR]{C.reset} {msg}")


def info(msg: str):
    print(f"   {C.gray}[i]{C.reset} {msg}")


def check_system() -> bool:
    """Verifica que sea Ubuntu 24.04+."""
    try:
        with open("/etc/os-release") as f:
            data = f.read()
        os_id = ""
        version = ""
        for line in data.splitlines():
            if line.startswith("ID="):
                os_id = line.split("=", 1)[1].strip('"')
            elif line.startswith("VERSION_ID="):
                version = line.split("=", 1)[1].strip('"')
        if os_id != "ubuntu":
            err(f"Sistema no compatible: {os_id}")
            return False
        major = int(version.split(".")[0])
        if major < 24:
            err(f"Ubuntu {version} no compatible. Se requiere 24.04+")
            return False
        info(f"Sistema detectado: Ubuntu {version}")
        return True
    except Exception as e:
        err(f"No se pudo detectar el sistema: {e}")
        return False


def ensure_sudo() -> bool:
    """Verifica y cachea permisos sudo."""
    if os.geteuid() != 0:
        print(f"\n{C.beige}VoidForge requiere permisos de administrador.{C.reset}")
        ret = os.system("sudo -v")
        if ret != 0:
            err("No se pudieron obtener permisos sudo")
            return False
        print()
    return True


def show_menu():
    """Menu interactivo principal."""
    while True:
        header("Menu principal")
        print()
        print(f"   {C.white}(1){C.reset} Instalacion completa (pasos 0-{TOTAL_STEPS})")
        print(f"   {C.white}(2){C.reset} Reanudar desde ultimo checkpoint")
        print(f"   {C.white}(3){C.reset} Ejecutar paso especifico")
        print(f"   {C.white}(4){C.reset} Ejecutar rango de pasos")
        print(f"   {C.white}(5){C.reset} Ver estado actual")
        print(f"   {C.white}(6){C.reset} Salir")
        print(f"\n{C.gray} Selecciona una opcion [1-6]:{C.reset}")

        try:
            # Leer de /dev/tty para compatibilidad con pipes
            with open("/dev/tty", "r") as tty:
                choice = tty.readline().strip()
        except (IOError, OSError):
            try:
                choice = input().strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

        if choice == "1":
            from voidforge.runner import StepRunner
            # Ejecutar todos los pasos
            info("Iniciando instalacion completa...")
            # TODO: implementar runner con steps
            break
        elif choice == "2":
            info("Reanudando desde checkpoint...")
            break
        elif choice == "3":
            try:
                with open("/dev/tty") as t:
                    step = t.readline().strip()
            except (IOError, OSError):
                step = input("  Paso? ").strip()
            info(f"Ejecutando paso {step}...")
            break
        elif choice == "4":
            try:
                with open("/dev/tty") as t:
                    rng = t.readline().strip()
            except (IOError, OSError):
                rng = input("  Rango (ej: 5-10)? ").strip()
            info(f"Ejecutando rango {rng}...")
            break
        elif choice == "5":
            try:
                with open(CHECKPOINT_FILE) as f:
                    cp = f.read().strip()
                info(f"Ultimo paso completado: {cp}")
            except (IOError, OSError):
                info("No hay checkpoint guardado")
            try:
                with open("/dev/tty") as t:
                    t.readline()
            except (IOError, OSError):
                input("  Enter para continuar...")
        elif choice == "6":
            print(f"\n{C.green}Hasta luego!{C.reset}")
            break
        else:
            err("Opcion no valida")
            import time
            time.sleep(0.5)


def main():
    # Inicializar log
    os.makedirs(os.path.dirname(LOG_FILE) or ".", exist_ok=True)
    with open(LOG_FILE, "w") as f:
        f.write(f"=== VoidForge v{VERSION} - {__import__('datetime').datetime.now()} ===\n")

    cls()
    print(f"{C.cyan}")
    # Mostrar banner si existe
    from voidforge.config import ASCII_FILE
    try:
        subprocess.run(["bash", str(ASCII_FILE)], timeout=5)
    except Exception:
        pass
    print(f"{C.gray}                      v{VERSION}{C.reset}")
    print()

    if not check_system():
        sys.exit(1)

    if not ensure_sudo():
        sys.exit(1)

    show_menu()


if __name__ == "__main__":
    main()
