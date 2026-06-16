# V0x3l — Agent Notes

## What this is

Post-instalador modular para Ubuntu Server 24.04+ escrito en Python con interfaz TUI urwid.  
El nombre del proyecto, versión, repo y rutas se configuran desde `.env`.

## Estructura

```
V0x3l/
├── .env                     # Configuracion centralizada
├── install.sh               # Bootstrap bash (curl | bash)
├── v0x3l/               # Paquete Python
│   ├── __main__.py          # Entry point
│   ├── app.py               # Event loop urwid + menu + dispatch
│   ├── config.py            # Carga .env + defaults
│   ├── shell.py             # subprocess + logging
│   ├── runner.py            # Step runner + checkpoint
│   ├── ui/                  # Componentes urwid
│   └── steps/               # 6 secciones de instalacion
├── assets/                  # Temas, logos, keyrings
├── colores / collorPalette  # Paleta de colores
├── demo_ui.py               # Demo de la interfaz
├── AGENTS.md
└── README.md
```

## Running

```bash
# One-liner
curl -fsSL https://raw.githubusercontent.com/alexandrpunk/V0x3l/refactor/install.sh | bash

# Desde repo clonado
sudo python3 -m v0x3l

# Demo
python3 demo_ui.py
```

## Configuracion (.env)

Editar `.env` para cambiar:
- `PROJECT_NAME` — nombre mostrado en la interfaz
- `PROJECT_VERSION` — version
- `UBUNTU_MIN_VERSION` — minima version de Ubuntu soportada
- `LOG_FILE`, `CHECKPOINT_FILE` — rutas de archivos runtime
- `TLP_CONF_NAME` — nombre del archivo de configuracion TLP
- `PLYMOUTH_THEME_NAME` — nombre del tema Plymouth
- `REPO_URL` — URL del repositorio git
- `REPO_BRANCH` — rama por defecto

## Verification

```bash
python3 -m py_compile v0x3l/*.py v0x3l/**/*.py && echo "Syntax OK"
python3 demo_ui.py
```
