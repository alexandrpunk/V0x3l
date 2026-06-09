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
PALETTE_FILE = BASE_DIR / "collorPalette"

# Tema Plymouth
PLYMOUTH_THEME_NAME = "voidforge-boot-theme"
PLYMOUTH_THEME_SRC = str(THEMES_DIR / "voidforge-boot-theme")
PLYMOUTH_ZIP_URL = "https://raw.githubusercontent.com/alexandrpunk/VoidForge/main/voidforge-boot-theme.zip"

# ── Cargar paleta de colores desde archivo externo ──

def load_palette(path: Path) -> list:
    """Lee collorPalette y devuelve lista de tuplas urwid.

    Formatos:
      6 columnas: nombre | fg_16 | bg_16 | mono | fg_256 | bg_256
      3 columnas: nombre | fg_16 | bg_16
    """
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
            ("error", "light red", "black", "", "#74BF04", "#000000"),
            ("info", "dark gray", "black", "", "#534E48", "#000000"),
            ("title", "light green, bold", "black", "", "#74BF04", "#000000"),
            ("progress_done", "light green", "black", "", "#74BF04", "#000000"),
            ("progress_bar", "dark green", "black", "", "#467302", "#000000"),
            ("pkg_name", "white, bold", "black", "", "#DCD2BF", "#000000"),
            ("pkg_speed", "dark gray", "black", "", "#534E48", "#000000"),
        ]
    return palette

PALETTE = load_palette(PALETTE_FILE)
