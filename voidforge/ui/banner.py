# Banner - muestra el logo de VoidForge en el terminal

import subprocess
import importlib.util
import sys
from pathlib import Path
from voidforge.config import BASE_DIR

ASCII_FILE = BASE_DIR / "ascii.sh"
LOGO_PNG = BASE_DIR / "voidforge-logo.png"
LOGO_SVG = BASE_DIR / "voidforge-logo.svg"

FALLBACK_TEXT = (
    "   ___      _      __ _                   \n"
    "  / _ \\___| |_   / _(_)__ ___ _ _ ___ ___ \n"
    " | (_/ -_)  _| |  _| / _/ _ \\ '_/ -_|_-< \n"
    "  \\___\\___|\\__| |_| |_\\__\\___/_| \\___/__/\n"
)


def _try_pillow(target_width: int = 60) -> str | None:
    """Convierte el PNG a ASCII usando Pillow (grayscale)."""
    try:
        from PIL import Image
    except ImportError:
        return None

    png = Path(LOGO_PNG)
    if not png.exists():
        return None

    try:
        img = Image.open(png)

        # Componer sobre fondo negro si tiene transparencia
        if img.mode == "RGBA":
            bg = Image.new("RGBA", img.size, (0, 0, 0, 255))
            img = Image.alpha_composite(bg, img)
        img = img.convert("L")  # Grayscale

        # Redimensionar para terminal
        aspect = img.height / img.width
        # Ajuste por proporcion de caracter (alto/ancho ≈ 0.45)
        target_height = int(target_width * aspect * 0.45)
        img = img.resize((target_width, target_height), Image.LANCZOS)

        # Gradiente de 10 niveles
        chars = "@%#*+=-:. "

        pixels = list(img.getdata())

        # Auto-contraste
        vals = [p for p in pixels if p < 250]
        if vals:
            minv, maxv = min(vals), max(vals)
            rng = maxv - minv
            if rng > 0:
                pixels = [int((p - minv) / rng * 255) for p in pixels]

        lines = []
        for y in range(target_height):
            line = ""
            for x in range(target_width):
                px = pixels[y * target_width + x]
                # Invertir: oscuro = espacio, claro = char denso
                idx = int((255 - px) / 256 * len(chars))
                idx = max(0, min(idx, len(chars) - 1))
                line += chars[idx]
            line = line.rstrip()
            lines.append(line)

        # Quitar lineas vacias al inicio/fin
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()

        if lines:
            return "\n".join(lines)
        return None

    except Exception:
        return None


def _try_ascii_sh() -> str | None:
    """Ejecuta ascii.sh y captura su salida."""
    try:
        result = subprocess.run(
            ["bash", str(ASCII_FILE)],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except Exception:
        pass
    return None


def get_banner_text() -> str:
    """Retorna el texto del banner (logo ASCII de VoidForge).

    Orden de prioridad:
    1. Conversion del PNG a ASCII via Pillow
    2. Script ascii.sh
    3. Texto fallback simple
    """
    banner = _try_pillow()
    if banner:
        return banner

    banner = _try_ascii_sh()
    if banner:
        return banner

    return FALLBACK_TEXT
