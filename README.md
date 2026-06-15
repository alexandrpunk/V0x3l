<p align="center">
  <img src="voidforge-logo.png" alt="VoidForge" width="250" />
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

# VoidForge

Post-instalador modular para Ubuntu Server 24.04+ con interfaz TUI (urwid). Automatiza: kernel XanMod, drivers NVIDIA, Wayland, PipeWire, Flatpak, TLP, Plymouth, GRUB, Oh My Zsh, LazyVim y mas.

## Una linea

```bash
curl -fsSL https://raw.githubusercontent.com/alexandrpunk/VoidForge/refactor/install.sh | bash
```

## Requisitos

- Ubuntu Server 24.04 LTS o superior
- Acceso root (sudo)
- Conexion a internet
- 20GB espacio libre en disco

## Caracteristicas

- **Interfaz TUI con urwid**: split panel con pasos (izquierda) + output en vivo (derecha)
- **16 pasos modulares**: cada paso es una clase Python
- **Checkpoint**: reanudable tras fallos
- **Monitor de paquetes**: barra de progreso + velocidad + contador durante nala install
- **Fallback texto**: si urwid no funciona, menu ANSI con colores
- **Idempotente**: se puede re-ejecutar sin riesgo

## Uso

```bash
# Interfaz interactiva
sudo python3 -m voidforge

# Demo de la interfaz (no modifica el sistema)
python3 demo_ui.py
```

## Pasos

| # | Categoria | Descripcion |
|---|-----------|-------------|
| 0 | core | nala, git, curl, zsh, coreutils |
| 1 | core | ButterRepo, PPAs, upgrade, timezone, locale |
| 2 | drivers | Kernel XanMod Edge x64v3 |
| 3 | drivers | NVIDIA 595-open + prime + on-demand |
| 4 | packages | Wayland, Nautilus, PipeWire, codecs, Flatpak, TLP (mega-install) |
| 5 | system | Polkit automount |
| 6 | system | xdg-user-dirs + UFW |
| 7 | system | Netplan + NetworkManager |
| 8 | packages | Flathub + Flatpak apps |
| 9 | system | Servicios + Wayland env |
| 10 | system | TLP + logind |
| 11 | packages | Oh My Zsh + agnoster |
| 12 | packages | LazyVim |
| 13 | theming | Colloid icons |
| 14 | theming | Plymouth + GRUB Vimix + cleanup |
| 15 | final | DMS (Dank Linux) |

## License

MIT

---

**Tu sistema. Tus reglas. Tu forja.**
