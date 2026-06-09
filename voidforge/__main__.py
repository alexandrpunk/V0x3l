#!/usr/bin/env python3
# VoidForge v2 - Entry point

import sys
import os
import subprocess

# Asegurar que el directorio actual esta en el path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voidforge.config import LOG_FILE, VERSION
from voidforge.shell import log


def main():
    # Inicializar log
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "w") as f:
        f.write(f"=== VoidForge v{VERSION} - $(date) ===\n")

    log(f"Iniciando VoidForge v{VERSION}")

    # Verificar que corremos como root
    if os.geteuid() != 0:
        print("VoidForge requiere permisos de administrador (sudo).")
        sys.exit(1)

    # Verificar Ubuntu >= 24
    if not _check_system():
        sys.exit(1)

    # Iniciar UI
    from voidforge.app import VoidForgeApp
    app = VoidForgeApp()
    app.run()


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
