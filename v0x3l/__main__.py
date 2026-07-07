#!/usr/bin/env python3
# V0x3l v2 - Entry point

import sys
import os
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from v0x3l.config import LOG_FILE, VERSION, PROJECT_NAME, UBUNTU_MIN
from v0x3l.shell import log


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
    # Modo no-interactivo para apt/dpkg/nala: evita que tomen el tty (dialogos,
    # barras de progreso de dpkg) y corrompan la pantalla de la TUI con escapes
    # sueltos. Se setean en el entorno global para que TODOS los subprocess los
    # hereden. setdefault: no pisa si el usuario ya las definio.
    os.environ.setdefault("DEBIAN_FRONTEND", "noninteractive")
    os.environ.setdefault("APT_LISTCHANGES_FRONTEND", "none")
    os.environ.setdefault("NEEDRESTART_MODE", "a")
    os.environ.setdefault("NEEDRESTART_SUSPEND", "1")

    os.makedirs(os.path.dirname(LOG_FILE) or ".", exist_ok=True)
    with open(LOG_FILE, "w") as f:
        from datetime import datetime as dt
        f.write(f"=== {PROJECT_NAME} v{VERSION} - {dt.now()} ===\n")

    log(f"Iniciando {PROJECT_NAME} v{VERSION}")

    if os.geteuid() != 0:
        print(f"{PROJECT_NAME} requiere permisos de administrador (sudo).")
        sys.exit(1)

    if not _check_system():
        sys.exit(1)

    if not ensure_urwid():
        sys.exit(1)

    from v0x3l.app import V0x3lApp
    app = V0x3lApp()
    sys.stdout.flush()
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
        if major < UBUNTU_MIN:
            log(f"ERROR: Ubuntu {version} no compatible. Se requiere {UBUNTU_MIN}.04+")
            return False
        log(f"Sistema detectado: Ubuntu {version}")
        return True
    except Exception as e:
        log(f"ERROR: No se pudo detectar el sistema: {e}")
        return False


if __name__ == "__main__":
    main()
