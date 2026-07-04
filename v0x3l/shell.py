# Shell helper - ejecucion de comandos, sudo, logging

import select
import subprocess
import os
from datetime import datetime
from typing import Optional, Callable
from v0x3l.config import LOG_FILE

INSTALL_COMMANDS = (
    "nala install",
    "nala update",
    "nala upgrade",
    "apt install",
    "apt-get install",
    "flatpak install",
)


def log(msg: str) -> None:
    """Escribe un mensaje al archivo de log con timestamp."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{ts}] {msg}\n")
    except OSError:
        pass


def is_package_install(args: tuple) -> bool:
    """Detecta si el comando es de instalacion de paquetes."""
    cmd_str = " ".join(str(a) for a in args)
    for kw in INSTALL_COMMANDS:
        if kw in cmd_str:
            return True
    return False


def run(
    description: str,
    *args: str,
    sudo: bool = False,
    on_line: Optional[Callable[[str], None]] = None,
    on_tick: Optional[Callable[[], None]] = None,
    timeout: Optional[int] = None,
    capture_output: bool = True,
) -> bool:
    """Ejecuta un comando, loguea salida, opcionalmente muestra en vivo.

    Args:
        description: descripcion para el log
        args: comando y argumentos
        sudo: si es True, antepone sudo
        on_line: callback llamado por cada linea de salida (para UI en vivo)
        timeout: timeout en segundos
        capture_output: si es False, stdout va directo al terminal (sin pipe)

    Returns:
        True si el comando retorno 0, False en otro caso
    """
    log(f"CMD: {' '.join(args)} (sudo={sudo})")

    cmd = list(args)
    if sudo and os.geteuid() != 0:
        cmd = ["sudo"] + cmd

    try:
        stdout = subprocess.PIPE if capture_output else None
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        if capture_output and proc.stdout:
            # Loop con select: redibuja (on_tick) cada ~100ms haya o no output,
            # y lee lineas en cuanto llegan. Asi la UI no se congela con
            # comandos silenciosos.
            fd = proc.stdout.fileno()
            while True:
                ready, _, _ = select.select([fd], [], [], 0.1)
                if on_tick:
                    on_tick()
                if fd in ready:
                    line = proc.stdout.readline()
                    if line == "":  # EOF
                        break
                    line = line.rstrip()
                    log(f"  {line}")
                    if on_line:
                        on_line(line)
                elif proc.poll() is not None:  # sin datos y el proc ya termino
                    break

        proc.wait(timeout=timeout)
        ok = proc.returncode == 0
        log(f"RESULT: {'OK' if ok else f'FAIL({proc.returncode})'} [{description}]")
        return ok

    except subprocess.TimeoutExpired:
        proc.kill()
        log(f"TIMEOUT: {description}")
        return False
    except FileNotFoundError:
        log(f"NOT_FOUND: {args[0] if args else '?'} - comando no encontrado")
        return False
    except Exception as e:
        log(f"ERROR: {e}")
        return False
