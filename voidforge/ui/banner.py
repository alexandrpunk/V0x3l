# Banner - muestra el arte ASCII de VoidForge

import subprocess
from voidforge.config import ASCII_FILE


def get_banner_text() -> str:
    """Retorna el arte ASCII de VoidForge, o un fallback."""
    try:
        result = subprocess.run(
            ["bash", str(ASCII_FILE)],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except Exception:
        pass
    return r"   ___      _      __ _                   " "\n" \
           r"  / _ \___| |_   / _(_)__ ___ _ _ ___ ___ " "\n" \
           r" | (_/ -_)  _| |  _| / _/ _ \ '_/ -_|_-<" "\n" \
           r"  \___\___|\__| |_| |_\__\___/_| \___/__/" "\n"
