#!/usr/bin/env python3
# VoidForge v2 - Entry point

import sys
import os
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voidforge.config import LOG_FILE, VERSION
from voidforge.shell import log


def ensure_urwid() -> bool:
    """Verifica que urwid este instalado, si no lo instala via apt."""
    try:
        import urwid  # noqa: F401
        return True
    except ImportError:
        pass

    print("  [..] Instalando python3-urwid...")
    try:
        subprocess.run(
            ["apt", "install", "-y", "python3-urwid"],
            check=True, capture_output=True, text=True
        )
        import urwid  # noqa: F401
        print("  [OK]  python3-urwid instalado")
        return True
    except Exception:
        pass

    print("  [ERR] No se pudo instalar python3-urwid.")
    print("  [ERR] Ejecuta manualmente: sudo apt install python3-urwid")
    return False


def main():
    os.makedirs(os.path.dirname(LOG_FILE) or ".", exist_ok=True)
    with open(LOG_FILE, "w") as f:
        f.write(f"=== VoidForge v{VERSION} - $(date) ===\n")

    log(f"Iniciando VoidForge v{VERSION}")

    if os.geteuid() != 0:
        print("VoidForge requiere permisos de administrador (sudo).")
        sys.exit(1)

    if not _check_system():
        sys.exit(1)

    if not ensure_urwid():
        sys.exit(1)

    print("  [OK]  Iniciando interfaz grafica...")
    from voidforge.app import VoidForgeApp
    app = VoidForgeApp()
    try:
        app.run()
    except Exception as e:
        print(f"\n  [ERR] Error al iniciar la interfaz: {e}")
        print("  [ERR] Ejecuta el demo para probar: python3 demo_ui.py")
        print(f"  [ERR] Log: {LOG_FILE}")
        sys.exit(1)


def _check_system() -> bool:
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
            log(f"ERROR: Sistema no compatible: {os_id}")
            return False
        major = int(version.split(".")[0])
        if major < 24:
            log(f"ERROR: Ubuntu {version} no compatible. Se requiere 24.04+")
            return False
        log(f"Sistema detectado: Ubuntu {version}")
        return True
    except Exception as e:
        log(f"ERROR: No se pudo detectar el sistema: {e}")
        return False


if __name__ == "__main__":
    main()
