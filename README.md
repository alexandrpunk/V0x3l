<p align="center">
  <img src="voidforge-logo.png" alt="V0x3l" width="250" />
</p>

<p align="center">
  <b>Tu sistema. Tus reglas. Tu forja.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Ubuntu-24.04+-E95420?logo=ubuntu" />
  <img src="https://img.shields.io/badge/license-MIT-green" />
  <img src="https://img.shields.io/badge/Python-3.12+-blue?logo=python" />
</p>

---

# V0x3l

Post-instalador modular para Ubuntu Server 24.04+ con interfaz TUI (urwid). Automatiza: kernel XanMod, drivers NVIDIA, Wayland, PipeWire, Flatpak, TLP, Plymouth, GRUB, Oh My Zsh, LazyVim y mas.

## Una linea

```bash
curl -fsSL https://raw.githubusercontent.com/alexandrpunk/V0x3l/refactor/install.sh | bash
```

## Requisitos

- Ubuntu Server 24.04 LTS o superior
- Acceso root (sudo)
- Conexion a internet

## Caracteristicas

- Interfaz TUI con urwid (split panel)
- 6 secciones modulares
- Checkpoint reanudable
- Monitor de paquetes en vivo
- Navegacion por teclado (1-6 + flechas)
- Proyecto configurable via `.env`

## Uso

```bash
sudo python3 -m voidforge
python3 demo_ui.py  # Demo simulada
```

## Pasos

| # | Seccion | Que hace |
|---|---------|----------|
| 0 | Preparacion del sistema | herramientas + repos + locale + timezone |
| 1 | Rendimiento y drivers | kernel XanMod + NVIDIA |
| 2 | Software | mega-install + flatpak + zsh + lazyvim |
| 3 | Configuracion | polkit + ufw + red + servicios + tlp |
| 4 | Apariencia | iconos + plymouth + grub |
| 5 | Entorno | gestor de escritorio DMS |

## Personalizacion

Editar `.env` en la raiz del proyecto para cambiar:

| Variable | Por defecto | Descripcion |
|----------|-------------|-------------|
| `PROJECT_NAME` | V0x3l | Nombre del proyecto |
| `PROJECT_VERSION` | 1.0.0 | Version |
| `UBUNTU_MIN_VERSION` | 24 | Minima version de Ubuntu |
| `LOG_FILE` | /tmp/v0x3l.log | Archivo de log |
| `CHECKPOINT_FILE` | /tmp/v0x3l-progress | Checkpoint reanudable |
| `TLP_CONF_NAME` | 01-v0x3l.conf | Nombre config TLP |
| `PLYMOUTH_THEME_NAME` | v0x3l-boot-theme | Tema Plymouth |
| `REPO_URL` | https://github.com/alexandrpunk/V0x3l.git | Repositorio |

## License

MIT

---

**Tu sistema. Tus reglas. Tu forja.**
