# VoidForge — Agent Notes

## What this is

Single-file Bash post-installer for Ubuntu Server. The entire codebase is `VoidForge.sh`.

## Running

```bash
sudo bash VoidForge.sh
```

- Must run as root (`EUID` check exits immediately otherwise).
- Uses `$SUDO_USER` to target the real user's home and services — never hardcode a username.
- Uses `set -euo pipefail` — any unbound variable or failing command aborts the whole script.

## Script structure (14 steps, numbered 0–13)

| Step | What it does |
|------|-------------|
| 0 | Installs Nala + basic utilities (including zsh, git, curl, ca-certificates) |
| 1 | Adds ButterRepo, full system upgrade, adds user to groups, timezone (America/Mazatlan), locale (es_MX.UTF-8) |
| 2 | Wayland stack + Mesa/Vulkan drivers |
| 3 | Nautilus + GVFS + polkitd + polkit automount rule |
| 4 | Additional packages via nala (neovim, zen-browser, tmux, fastfetch, geany, nwg-look, libheif-plugin-libde265, ufw, gnome-sushi, xdg-user-dirs), UFW firewall enabled (deny incoming) |
| 5 | PipeWire, NetworkManager, Bluetooth, disables `systemd-networkd-wait-online` (avoids 5-min boot hang), writes netplan config |
| 6 | Multimedia codecs |
| 7 | Flatpak + Flathub + Nautilus portal override + Flatpak apps (Papers, Resources, Showtime) |
| 8 | Enables services, writes `~/.config/environment.d/wayland.conf` with Wayland env vars |
| 9 | Laptop power optimization: installs TLP with custom config, configures logind (lid switch, power key) |
| 10 | Installs Oh My Zsh with agnoster theme, sets zsh as default shell, installs `fonts-powerline` |
| 11 | Icon theme Colloid with catppuccin green variant (from GitHub) |
| 12 | Plymouth theme from a `.zip` colocated with the script (auto-detected), GRUB theme (Vimix Very Dark Blue from GitHub), updates GRUB and initramfs, `nala autoremove + clean` |
| 13 | Downloads and pipes an external installer from `install.danklinux.com` (runs last to avoid interference) |

## Non-obvious gotchas

- **Plymouth theme detection**: looks for any `*.zip` in the script's own directory (`$SCRIPT_DIR`). If absent, step 12 is silently skipped (warn-only).
- **Step 5 critical side-effect**: masks `systemd-networkd-wait-online.service` and overwrites `/etc/netplan/01-netcfg.yaml`. Editing this step requires care on systems that depend on netplan's default renderer.
- **Step 7 installs Flatpak apps**: the Flatpak apps (Papers, Resources, Showtime) must stay in step 7, AFTER Flathub is added — not earlier.
- **Step 9 TLP config**: writes `/etc/tlp.d/01-voidforge.conf` — limits CPU to 80% on battery, PCIe ASPM powersupersave, USB autosuspend, WiFi power save on battery. Also configures logind lid switch behavior.
- **Step 13 is external**: fetches and runs the Dank Linux installer as the unprivileged user. Runs last to avoid interference with other steps.
- **GRUB is modified**: `sed` on `/etc/default/grub` adds `splash` and sets `GRUB_THEME` to Vimix Very Dark Blue, then `grub-mkconfig` + `update-initramfs -u` are run. A typo here can break boot visuals.
- **Polkit rule**: writes `/etc/polkit-1/rules.d/90-udisks2-automount.rules` — grants auto-mount to the `plugdev` group.
- **UFW is enabled** in step 4 with `deny incoming / allow outgoing`. Adding services later requires opening ports explicitly.

## Style conventions

- Step logs use emoji-prefixed `echo` lines.
- Inline configs are written via heredocs (quoted delimiter to prevent variable expansion).
- Package installs consistently use `--no-install-recommends -y`.

## Verification

No tests, linter, or CI. Verify changes by:
- ShellCheck: `shellcheck VoidForge.sh`
- Dry-review: read the diff carefully, since this script modifies system-level config as root.
