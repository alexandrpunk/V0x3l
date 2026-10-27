# Shell helper - ejecucion de comandos, sudo, logging

import select
import os
import subprocess
from datetime import datetime
import time
from typing import Optional, Callable
from v0x3l.config import LOG_FILE

def log(message: str) -> None:
    """Anexa una linea al log del instalador."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {message}\n")


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
            # Leer salida sin bloquear la aplicación y vigilar el límite desde
            # el mismo bucle, incluso si el proceso no produce ninguna línea.
            fd = proc.stdout.fileno()
            started = time.monotonic()
            while True:
                if timeout is not None and time.monotonic() - started >= timeout:
                    proc.kill()
                    proc.wait()
                    if proc.stdout:
                        proc.stdout.close()
                    log(f"TIMEOUT: {description}")
                    return False
                ready, _, _ = select.select([fd], [], [], 0.1)
                if on_tick:
                    on_tick()
                if fd in ready:
                    line = proc.stdout.readline()
                    if line == "":
                        break
                    line = line.rstrip()
                    log(f"  {line}")
                    if on_line:
                        on_line(line)
                elif proc.poll() is not None:
                    break
            proc.wait(timeout=timeout)
        else:
            proc.wait(timeout=timeout)
        proc.stdout.close() if proc.stdout else None
        ok = proc.returncode == 0
        log(f"RESULT: {'OK' if ok else f'FAIL({proc.returncode})'} [{description}]")
        return ok

    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        if proc.stdout:
            proc.stdout.close()
        log(f"TIMEOUT: {description}")
        return False
    except FileNotFoundError:
        log(f"NOT_FOUND: {args[0] if args else '?'} - comando no encontrado")
        return False
    except OSError as e:
        log(f"ERROR: {e}")
        return False
