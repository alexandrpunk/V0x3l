# Shell helper - ejecucion de comandos, sudo, logging

import subprocess
import os
from datetime import datetime
from typing import Optional, Callable

LOG_FILE = "/tmp/voidforge.log"

INSTALL_COMMANDS = (
    "nala install",
    "nala update",
    "nala upgrade",
    "apt install",
    "apt-get install",
    "flatpak install",
)


def is_package_install(args: tuple) -> bool:
    """Detecta si el comando es de instalacion de paquetes."""
    cmd_str = " ".join(str(a) for a in args)
    for kw in INSTALL_COMMANDS:
        if kw in cmd_str:
            return True
    return False


def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{ts}] {msg}\n")


def run(
    description: str,
    *args: str,
    sudo: bool = False,
    on_line: Optional[Callable[[str], None]] = None,
    timeout: Optional[int] = None,
    package_monitor: bool = False,
) -> bool:
    """Ejecuta un comando, loguea salida, opcionalmente muestra en vivo.

    Si package_monitor=True y on_line tiene un .use_package_monitor(),
    activa el visor compacto de paquetes antes de ejecutar.

    Args:
        description: descripcion para el log
        args: comando y argumentos
        sudo: si es True, antepone sudo
        on_line: callback llamado por cada linea de salida (para UI en vivo)
        timeout: timeout en segundos
        package_monitor: si es True, intenta activar el monitor de paquetes

    Returns:
        True si el comando retorno 0, False en otro caso
    """
    log(f"CMD: {' '.join(args)} (sudo={sudo})")

    # Activar monitor de paquetes si corresponde
    if package_monitor or (not package_monitor and is_package_install(args)):
        if on_line and hasattr(on_line, '__self__'):
            screen = on_line.__self__
            if hasattr(screen, 'use_package_monitor'):
                screen.use_package_monitor()

    cmd = list(args)
    if sudo and os.geteuid() != 0:
        cmd = ["sudo"] + cmd

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        for line in proc.stdout:
            line = line.rstrip()
            log(f"  {line}")
            if on_line:
                on_line(line)

        proc.wait(timeout=timeout)
        ok = proc.returncode == 0
        log(f"RESULT: {'OK' if ok else f'FAIL({proc.returncode})'} [{description}]")
        return ok

    except subprocess.TimeoutExpired:
        if hasattr(proc, 'kill'):
            proc.kill()
        log(f"TIMEOUT: {description}")
        return False
    except FileNotFoundError:
        log(f"NOT_FOUND: {args[0]} - comando no encontrado")
        return False
    except Exception as e:
        log(f"ERROR: {e}")
        return False
