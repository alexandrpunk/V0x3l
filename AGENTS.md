# VoidForge — Agent Notes (refactor branch)

## What this is

Modular Bash post-installer for Ubuntu Server, rebuilt from the monolithic `VoidForge.sh` into a clean directory structure inspired by [Omakub](https://github.com/basecamp/omakub).

## Structure

```
VoidForge/
├── voidforge.sh              # Entry point / runner — sources libs + steps, handles menu & CLI
├── boot.sh                   # curl | bash entry — clones repo, runs voidforge.sh
├── ascii.sh                  # ASCII banner art
├── lib/
│   ├── config.sh             # Variables globales (colores, TOTAL_STEPS, paths)
│   ├── helpers.sh            # root(), log_*(), run_cmd(), spinner, checkpoint, run_step, run_all_steps
│   └── gum.sh                # Gum detection + install + wrapper functions (spin, choose, confirm, style)
├── install/
│   ├── core/                 # Base del sistema
│   │   ├── bootstrap.sh      # step_0 — nala, git, curl, zsh...
│   │   └── system-prep.sh    # step_1 — ButterRepo, PPAs, upgrade, locale, grupos
│   ├── drivers/              # Kernel y drivers
│   │   ├── kernel.sh         # step_2 — XanMod Edge
│   │   └── gpu.sh            # step_3 — GPU NVIDIA + prime
│   ├── packages/             # Software y aplicaciones
│   │   ├── mega.sh           # step_4 — Mega-instalación (Wayland, Nautilus, PipeWire, codecs...)
│   │   ├── flatpak.sh        # step_8 — Flathub + Flatpak apps
│   │   ├── shell.sh          # step_11 — Oh My Zsh + tema agnoster
│   │   └── editor.sh         # step_12 — LazyVim
│   ├── system/               # Configuración del sistema
│   │   ├── polkit.sh         # step_5 — Polkit automount
│   │   ├── xdg-ufw.sh        # step_6 — xdg-user-dirs + UFW
│   │   ├── network.sh        # step_7 — Netplan + NetworkManager
│   │   ├── services.sh       # step_9 — Servicios + Wayland env
│   │   └── tlp.sh            # step_10 — TLP + logind
│   ├── theming/              # Capa visual
│   │   ├── icons.sh          # step_13 — Colloid catppuccin green
│   │   └── boot.sh           # step_14 — Plymouth + GRUB + limpieza
│   └── final/                # Post-instalación
│       └── dms.sh            # step_15 — DMS (Dank Linux)
├── assets/
│   └── voidforge-boot-theme.zip
├── VoidForge.sh              # (legacy) Monolítico original, mantenido como referencia
├── AGENTS.md
└── README.md
```

## Running

```bash
# Interactive menu
sudo bash voidforge.sh

# CLI flags
sudo bash voidforge.sh --resume      # Resume from checkpoint
sudo bash voidforge.sh --step 5      # Run only step 5
sudo bash voidforge.sh --range 5-10  # Run steps 5-10
sudo bash voidforge.sh --skip 3,7    # Skip steps 3 and 7
sudo bash voidforge.sh --all         # Run all steps

# One-liner (clones repo first)
bash <(curl -fsSL https://raw.githubusercontent.com/alexandrpunk/VoidForge/main/boot.sh)
```

## Key architectural decisions

- **Modularity**: Each step is a separate file in `install/<category>/`. The runner `voidforge.sh` sources everything via `find` + `source` at startup.
- **Gum integration**: `lib/gum.sh` detects and installs Charmbracelet Gum. All UI functions have text fallbacks if gum isn't available.
- **DEBIAN_FRONTEND=noninteractive**: Set in `lib/helpers.sh` to prevent debconf prompts from blocking package installation.
- **NEEDRESTART_MODE=a**: Suppresses needrestart prompts for service restarts after package updates.
- **tee in run_cmd**: `run_cmd()` now uses `tee -a "$LOG_FILE"` so output is visible in real-time AND logged — no more blind spinner while nala waits for input.
- **boot.sh**: Follows Omakub's pattern — minimal entry point (~30 lines) that clones the repo and hands off to `voidforge.sh`.
- **16 steps (0–15)**: Unchanged from the monolithic version. Each step file defines one `step_N()` function.

## Fixes included vs the monolithic version

| Issue | Fix |
|-------|-----|
| Nala/apt hanging on debconf prompts | `DEBIAN_FRONTEND=noninteractive` + `NEEDRESTART_MODE=a` |
| Nala output hidden (blind spinner) | `tee -a` en `run_cmd()` |
| Plymouth theme not found in `curl | bash` | `PLYMOUTH_ZIP_URL` fallback download (line 53 of config.sh) |
| Ubuntu version check blocking 24.04 | Fixed `-ge 26` → `-ge 24` in `check_system()` |
| Menu `read` fails on piped input | All `read` calls use `</dev/tty` |
| DMS installer not included | Reintegrated as `step_15` via `curl | sh` |

## Code conventions

- Each `install/*/*.sh` defines a single `step_N()` function
- Step functions use `should_run_step N || return 0` for idempotency
- All `root()` calls protected with `|| true` or equivalent
- `set -euo pipefail` at the top of `voidforge.sh`
- Colors via `$C_*` variables (defined in `config.sh`)
- Gum wrappers in `lib/gum.sh` auto-fallback to text mode
- Two traps in `helpers.sh`:
  - `trap 'nospin 2>/dev/null || true' EXIT` — kills spinner on exit
  - `trap 'error_handler $? $LINENO "$BASH_COMMAND"' ERR` — logs errors

## Verification

```bash
bash -n voidforge.sh && echo "Syntax OK"
find . -name "*.sh" -exec bash -n {} \; && echo "All OK"
```

For functional testing:
```bash
sudo bash voidforge.sh --step 0     # Test bootstrap only
sudo bash voidforge.sh --range 0-4  # Test core + drivers + packages
```
