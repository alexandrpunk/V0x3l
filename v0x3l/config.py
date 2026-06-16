# Configuracion global de V0x3l — lee desde .env con fallbacks

import os
from pathlib import Path

# ── Cargar .env ──
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

_env = {}
if ENV_FILE.exists():
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            _env[key.strip()] = val.strip().strip('"').strip("'")

def env(key: str, default: str = "") -> str:
    """Lee variable de .env o variable de entorno del SO, con fallback."""
    return os.environ.get(key, _env.get(key, default))

# ── Variables del proyecto ──
PROJECT_NAME = env("PROJECT_NAME", "V0x3l")
VERSION = env("PROJECT_VERSION", "1.0.0")
UBUNTU_MIN = int(env("UBUNTU_MIN_VERSION", "26"))

# ── Rutas runtime ──
LOG_FILE = env("LOG_FILE", "/tmp/v0x3l.log")
CHECKPOINT_FILE = env("CHECKPOINT_FILE", "/tmp/v0x3l-progress")

# ── Repo ──
REPO_URL = env("REPO_URL", "https://github.com/alexandrpunk/V0x3l.git")
REPO_BRANCH = env("REPO_BRANCH", "refactor")

# ── Rutas del proyecto ──
ASSETS_DIR = BASE_DIR / "assets"
THEMES_DIR = ASSETS_DIR / "themes"
ASCII_FILE = BASE_DIR / "ascii.sh"
PALETTE_FILE = BASE_DIR / "collorPalette"

# ── Config del sistema ──
TLP_CONF_NAME = env("TLP_CONF_NAME", "01-v0x3l.conf")
PLYMOUTH_THEME_NAME = env("PLYMOUTH_THEME_NAME", "v0x3l-boot-theme")
PLYMOUTH_THEME_SRC = str(THEMES_DIR / PLYMOUTH_THEME_NAME)

# ── Steps ──
TOTAL_STEPS = 5

# ── Cargar paleta de colores ──

PALETTE_FILE = BASE_DIR / "collorPalette"

def load_palette(path: Path) -> list:
    palette = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 6:
                    name, fg16, bg16, mono, fg256, bg256 = parts[:6]
                    palette.append((name, fg16, bg16, mono, fg256, bg256))
                elif len(parts) >= 5:
                    name, fg16, bg16, fg256, bg256 = parts[:5]
                    palette.append((name, fg16, bg16, "", fg256, bg256))
                elif len(parts) == 3:
                    name, fg16, bg16 = parts
                    palette.append((name, fg16, bg16))
    except (FileNotFoundError, OSError):
        palette = [
            ("header_bg", "light green, bold", "black", "", "#74BF04", "#534E48"),
            ("footer_bg", "dark gray", "black", "", "#534E48", "#000000"),
            ("body", "white", "black", "", "#DCD2BF", "#000000"),
            ("body_focus", "black", "light gray", "", "#000000", "#D1C6B2"),
            ("dim", "dark gray", "black", "", "#534E48", "#000000"),
            ("button_normal", "white", "black", "", "#DCD2BF", "#000000"),
            ("button_focus", "black", "light green", "", "#000000", "#74BF04"),
            ("ok", "light green", "black", "", "#74BF04", "#000000"),
            ("warn", "yellow", "black", "", "#D1C6B2", "#000000"),
            ("error", "light red", "black", "", "#FF6B6B", "#000000"),
            ("info", "dark gray", "black", "", "#534E48", "#000000"),
            ("title", "light green, bold", "black", "", "#74BF04", "#000000"),
            ("progress_done", "light green", "black", "", "#74BF04", "#000000"),
            ("progress_bar", "dark green", "black", "", "#467302", "#000000"),
            ("pkg_name", "white, bold", "black", "", "#DCD2BF", "#000000"),
            ("pkg_speed", "dark gray", "black", "", "#534E48", "#000000"),
        ]
    return palette

PALETTE = load_palette(PALETTE_FILE)
