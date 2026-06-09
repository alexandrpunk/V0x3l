# Configuracion global de VoidForge

VERSION = "2.0.0"
TOTAL_STEPS = 15
CHECKPOINT_FILE = "/tmp/voidforge-progress"
LOG_FILE = "/tmp/voidforge.log"

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
THEMES_DIR = ASSETS_DIR / "themes"
ASCII_FILE = BASE_DIR / "ascii.sh"
PALETTE_FILE = BASE_DIR / "collorPalette"

PLYMOUTH_THEME_NAME = "voidforge-boot-theme"
PLYMOUTH_THEME_SRC = str(THEMES_DIR / "voidforge-boot-theme")
PLYMOUTH_ZIP_URL = "https://raw.githubusercontent.com/alexandrpunk/VoidForge/main/voidforge-boot-theme.zip"


def load_palette(path: Path) -> list:
    """Lee collorPalette y devuelve tuplas urwid.

    Formato: nombre | fg_16 | bg_16
    """
    from pathlib import Path
    palette = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p.strip().split("#")[0].strip() for p in line.split("|")]
                if len(parts) >= 3:
                    name, fg, bg = parts[:3]
                    palette.append((name, fg, bg))
    except (FileNotFoundError, OSError):
        pass
    return palette


PALETTE = load_palette(PALETTE_FILE)

if not PALETTE:
    PALETTE = [
        ("header_bg", "light green", "black"),
        ("footer_bg", "dark gray", "black"),
        ("body", "white", "black"),
        ("body_focus", "black", "light gray"),
        ("dim", "dark gray", "black"),
        ("button_normal", "white", "black"),
        ("button_focus", "black", "light green"),
        ("ok", "light green", "black"),
        ("warn", "yellow", "black"),
        ("error", "light red", "black"),
        ("info", "dark gray", "black"),
        ("title", "light green, bold", "black"),
        ("progress_done", "light green", "black"),
        ("progress_bar", "dark green", "black"),
        ("pkg_name", "white, bold", "black"),
        ("pkg_speed", "dark gray", "black"),
    ]
