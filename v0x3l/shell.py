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
        on_tick: callback llamado periodicamente (spinner, draw_screen)
        timeout: timeout en segundos
        capture_output: si es False, stdout va directo al terminal (sin pipe)

    Returns:
        True si el comando retorno 0, False en otro caso
    """
    log(f"CMD: pid={os.getpid()} desc='{description}' sudo={sudo} -> {' '.join(args)}")

    cmd = list(args)
    if sudo and os.geteuid() != 0:
        # Asegurar que sudo tenga /usr/sbin y /sbin en PATH (update-initramfs,
        # plymouth-set-default-theme, etc. viven ahi y secure_path los omite).
        env = os.environ.copy()
        path_parts = [p for p in env.get("PATH", "").split(":") if p]
        for extra in ("/usr/local/sbin", "/usr/sbin", "/sbin"):
            if extra not in path_parts:
                path_parts.append(extra)
        env["PATH"] = ":".join(path_parts)
        cmd = ["sudo", "env", "PATH=" + env["PATH"]] + cmd

    try:
        started = time.monotonic()
        stdout = subprocess.PIPE if capture_output else None

        def on_stdout_line(line: bytes):
            try:
                text = line.decode("utf-8", errors="replace").rstrip("\n")
            except Exception:
                text = str(line)
            if on_line:
                on_line(text)

        process = subprocess.Popen(
            cmd,
            stdout=stdout,
            stderr=subprocess.STDOUT if capture_output else None,
            env=env,
        )

        # Si capture_output, leer linea a linea para mostrar en vivo
        if capture_output and process.stdout:
            for raw in process.stdout:
                on_stdout_line(raw)

        ok = process.wait() == 0
        elapsed = time.monotonic() - started
        log(
            f"RESULT: pid={os.getpid()} rc={process.returncode} "
            f"elapsed={elapsed:.2f}s "
            f"{'OK' if ok else 'FAIL(' + str(process.returncode) + ')'}"
        )
        return ok
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - started if "started" in locals() else 0.0
        log(
            f"TIMEOUT: pid={os.getpid()} desc='{description}' "
            f"elapsed={elapsed:.2f}s"
        )
        try:
            process.kill()
        except Exception:
            pass
        return False
    except FileNotFoundError:
        log(f"NOT_FOUND: pid={os.getpid()} cmd={args[0] if args else '?'} - comando no encontrado")
        return False
    except OSError as e:
        log(f"ERROR: pid={os.getpid()} [{description}] {e}")
        return False
