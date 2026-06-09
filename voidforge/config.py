# Configuracion global de VoidForge

VERSION = "2.0.0"
TOTAL_STEPS = 15
CHECKPOINT_FILE = "/tmp/voidforge-progress"
LOG_FILE = "/tmp/voidforge.log"

# Paths base (se resuelven desde la ubicacion del modulo)
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
THEMES_DIR = ASSETS_DIR / "themes"
ASCII_FILE = BASE_DIR / "ascii.sh"

# Tema Plymouth
PLYMOUTH_THEME_NAME = "voidforge-boot-theme"
PLYMOUTH_THEME_SRC = str(THEMES_DIR / "voidforge-boot-theme")
PLYMOUTH_ZIP_URL = "https://raw.githubusercontent.com/alexandrpunk/VoidForge/main/voidforge-boot-theme.zip"

# Colores para urwid (paleta)
PALETTE = [
    ("header", "light cyan", "black"),
    ("body", "white", "black"),
    ("footer", "dark gray", "black"),
    ("selected", "black", "light gray"),
    ("ok", "light green", "black"),
    ("warn", "yellow", "black"),
    ("error", "light red", "black"),
    ("info", "dark gray", "black"),
    ("title", "light cyan, bold", "black"),
    ("progress_done", "light green", "black"),
    ("progress_bar", "dark cyan", "black"),
]
