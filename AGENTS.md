# VoidForge — Agent Notes

## What this is

Post-instalador modular para Ubuntu Server 24.04+ escrito en Python con interfaz TUI urwid.

## Estructura

```
VoidForge/
├── install.sh                # Bootstrap bash (curl | bash) → clona repo → python3 -m voidforge
├── voidforge/                # Paquete Python
│   ├── __main__.py           # Entry point (check_system, ensure_urwid, lanza App)
│   ├── app.py                # Event loop urwid + menu + dispatch de steps
│   ├── config.py             # Variables, paleta de colores, paths
│   ├── shell.py              # subprocess.run() con output en vivo + logging
│   ├── runner.py             # Ejecutor secuencial de steps + checkpoint
│   ├── ui/
│   │   ├── menu.py           # Menu principal (LineBox + urwid.Button)
│   │   ├── layout.py         # Frame (header + body + footer)
│   │   ├── progress.py       # Pantalla de progreso por step
│   │   ├── package_monitor.py # Monitor de instalacion de paquetes (barra + contador)
│   │   ├── execution_screen.py # Split panel: pasos (izq) + output (der)
│   │   ├── steps_list.py     # Lista de 16 pasos con estados
│   │   ├── dialogs.py        # Dialogos (mensaje, confirmacion, input)
│   │   └── banner.py         # Logo ASCII (Pillow PNG → ASCII, fallback ascii.sh)
│   └── steps/
│       ├── base.py           # Clase base BaseStep
│       ├── core.py           # Steps 0-1 (bootstrap + repos)
│       ├── drivers.py        # Steps 2-3 (kernel + GPU)
│       ├── packages.py       # Steps 4,8,11,12 (software)
│       ├── system.py         # Steps 5,6,7,9,10 (config)
│       ├── theming.py        # Steps 13-14 (icons + Plymouth/GRUB)
│       └── final.py          # Step 15 (DMS)
├── assets/themes/            # Tema Plymouth pre-extraido
├── ascii.sh                  # Banner ASCII art
├── collorPalette             # Paleta de colores (urwid, formato pipe-delimited)
├── colores                   # Colores hex originales (referencia)
├── voidforge-logo.png/svg    # Logo
├── demo_ui.py                # Demo de la interfaz (no modifica el sistema)
├── AGENTS.md
└── README.md
```

## Running

```bash
# One-liner
curl -fsSL https://raw.githubusercontent.com/alexandrpunk/VoidForge/refactor/install.sh | bash

# Desde repo clonado
sudo python3 -m voidforge

# Demo de la interfaz
python3 demo_ui.py
```

## Key decisions

- **Python + urwid**: misma stack que Subiquity (instalador oficial Ubuntu Server)
- **collorPalette**: colores externos editables (formato: `nombre | fg_16 | bg_16 | mono | fg_256 | bg_256`)
- **shell.py**: subprocess con output en vivo via callback `on_line`
- **capture_output=False**: para comandos interactivos (DMS installer)
- **AsyncioEventLoop**: evita PermissionError de epoll en algunos TTY
- **Fallback texto**: si urwid falla, menu ANSI con colores

## Verification

```bash
python3 -m py_compile voidforge/*.py voidforge/**/*.py && echo "Syntax OK"
python3 demo_ui.py  # Test interfaz
```
