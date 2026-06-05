# VoidForge — Agent Notes

## What this is

Monolintary Bash post-installer for Ubuntu Server. The entire codebase is `VoidForge.sh`.

## Running

```bash
sudo bash VoidForge.sh
```

Interactive menu launches by default. CLI flags available for automation:

```bash
sudo bash VoidForge.sh --resume      # Resume from checkpoint
sudo bash VoidForge.sh --step 5      # Run only step 5
sudo bash VoidForge.sh --range 5-10  # Run steps 5-10
sudo bash VoidForge.sh --skip 3,7    # Skip steps 3 and 7
sudo bash VoidForge.sh --all         # Run all steps
```

- Must run as root (`EUID` check exits immediately otherwise).
- Uses `$SUDO_USER` to target the real user's home and services — never hardcode a username.
- Uses `set -euo pipefail` — any unbound variable or failing command aborts the whole script.

## Script structure (16 steps, numbered 0–15)

| Step | What it does |
|------|-------------|
| 0 | Bootstrap: installs `nala`, `wget`, `git`, `curl`, `zsh`, `pciutils`, `locales` via `apt` |
| 1 | Adds ButterRepo, full system upgrade, adds user to groups, timezone (America/Mazatlan), locale (es_MX.UTF-8) |
| 2 | Installs XanMod Edge kernel (via dedicated repo) |
| 3 | Detects GPU: uses `ubuntu-drivers devices` to find latest compatible NVIDIA driver, installs `nvidia-driver-<VERSION>` + `nvidia-prime` for Optimus or pure NVIDIA, skips otherwise. Enables `nvidia-suspend/resume/hibernate` services. |
| 4 | **Mega-installation** of all packages: Wayland stack, Nautilus, apps (neovim, zen-browser, tmux, fastfetch, geany, nwg-look), Audio/Bluetooth (PipeWire, bluez), Codecs, Flatpak, TLP, fonts-powerline. 8+ nala calls consolidated into 1. |
| 5 | Polkit automount rule (`/etc/polkit-1/rules.d/90-udisks2-automount.rules`) — grants auto-mount to `plugdev` group |
| 6 | `xdg-user-dirs-update` (creates user dirs), UFW enabled (deny incoming, allow outgoing) |
| 7 | Masks `systemd-networkd-wait-online.service` (avoids 5-min boot hang), writes `/etc/netplan/01-netcfg.yaml` (renderer: NetworkManager), runs `netplan apply` |
| 8 | Adds Flathub, installs Flatpak apps (Papers, Resources, Showtime), writes `/etc/flatpak/overrides/global` for Nautilus access |
| 9 | Enables services (NetworkManager, udisks2, bluetooth), enables user services (pipewire, wireplumber), writes `~/.config/environment.d/wayland.conf` with Wayland env vars |
| 10 | TLP config (`/etc/tlp.d/01-voidforge.conf`) — limits CPU to 80% on battery, PCIe ASPM powersupersave, USB autosuspend, WiFi power save. Also configures `logind` (lid switch, power key). |
| 11 | Installs Oh My Zsh with agnoster theme, sets zsh as default shell, installs `fonts-powerline` (already included in step 4 mega-install) |
| 12 | Icon theme Colloid with catppuccin green variant (from GitHub) |
| 13 | Plymouth theme from a `.zip` colocated with the script (auto-detected), GRUB theme (Vimix Very Dark Blue from GitHub), adds NVIDIA DRM/KMS kernel parameters if GPU detected, updates GRUB and initramfs, `nala autoremove + clean` |
| 14 | Cleanup: `nala autoremove -y`, `nala clean` |
| 15 | Downloads and pipes Dank Linux installer (runs last to avoid interference) |

## Non-obvious gotchas

- **Plymouth theme detection**: looks for any `*.zip` in the script's own directory (`$SCRIPT_DIR`). If absent, step 13 warns and skips without error.
- **Step 7 critical side-effect**: masks `systemd-networkd-wait-online.service` and overwrites `/etc/netplan/01-netcfg.yaml`. Editing this step requires care on systems that depend on netplan's default renderer.
- **Step 8 installs Flatpak apps**: the Flatpak apps (Papers, Resources, Showtime) must stay in step 8, AFTER Flathub is added — not earlier.
- **Step 10 TLP config**: writes `/etc/tlp.d/01-voidforge.conf` — limits CPU to 80% on battery, PCIe ASPM powersupersave, USB autosuspend, WiFi power save on battery. Also configures logind lid switch behavior.
- **Step 13 NVIDIA DRM/KMS**: if NVIDIA GPU detected, adds `nvidia-drm.modeset=1 nvidia-drm.fbdev=1 nvidia.NVreg_PreserveVideoMemoryAllocations=1` to `GRUB_CMDLINE_LINUX_DEFAULT`. Required for Wayland on NVIDIA. Also adds NVIDIA modules to initramfs.
- **Step 15 is external**: fetches and runs Dank Linux installer as unprivileged user. Runs last to avoid interference with other steps.
- **GRUB is modified**: `sed` on `/etc/default/grub` adds `splash`, sets `GRUB_THEME`, adds NVIDIA parameters if needed, then `grub-mkconfig` + `update-initramfs -u` are run. A typo here can break boot visuals.
- **Checkpoints**: script saves last completed step in `/tmp/voidforge-progress`. Use `--resume` to continue from interruption.
- **Polkit rule**: writes `/etc/polkit-1/rules.d/90-udisks2-automount.rules` — grants auto-mount to `plugdev` group.
- **UFW is enabled** in step 6 with `deny incoming / allow outgoing`. Adding services later requires opening ports explicitly.
- **XanMod kernel**: requires reboot to apply. Script warns at end if installed.
- **NVIDIA drivers**: require reboot to apply DRM/KMS parameters. Script warns at end if installed.

## Code conventions

- Each step is a function `step_N()`.
- Helper functions: `log_step()`, `log_ok()`, `log_skip()`, `log_warn()`, `log_error()`.
- Checkpoints: `save_checkpoint <N>` and `load_checkpoint`.
- Colors: `C_CYAN`, `C_GREEN`, `C_YELLOW`, `C_RED`, `C_GRAY`, `C_WHITE`, `C_BLUE`.
- Mega-installation: step 4 installs 8+ steps' worth of packages in 1 nala call for speed.
- NVIDIA detection: `ubuntu-drivers devices` finds optimal version dynamically.
- Interactive menu: `select` loop with 7 options (all, resume, step, range, status, readme, exit).
- CLI flags: `--resume`, `--step N`, `--range N-M`, `--skip N,M,...`, `--all`.
- Package installs use `--no-install-recommends -y` for minimal footprint.

## Verification

No tests, linter, or CI. Verify changes by:
- ShellCheck: `shellcheck VoidForge.sh`
- Test individual steps: `sudo bash VoidForge.sh --step <N>`
- Test ranges: `sudo bash VoidForge.sh --range 0-4`
- Dry-review: read the diff carefully, since this script modifies system-level config as root.