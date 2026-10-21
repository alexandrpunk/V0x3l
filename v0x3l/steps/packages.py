# Step 2: Software (mega-install + DMS + flatpak)

import os
import subprocess

from v0x3l.steps.base import BaseStep
from v0x3l.config import TARGET_USER



class SoftwareStep(BaseStep):
    number = 2
    title = "Software"
    category = "packages"

    def run(self) -> bool:
        ok = True

        # ── Mega-install de paquetes ──
        ok &= self.runner.ui.run_cmd("mega-install",
            "nala", "install", "--no-install-recommends", "-y",
            "wayland-protocols", "libwayland-dev", "libegl1",
            "libgl1-mesa-dri", "mesa-vulkan-drivers", "xwayland",
            "nautilus", "gvfs-backends", "gvfs-fuse", "udisks2", "polkitd",
            "ntfs-3g", "exfatprogs", "libglib2.0-bin",
            "neovim", "tmux", "fastfetch", "geany",
            "nwg-look", "dialog", "apt-utils",
            "libheif-plugin-libde265", "ufw", "gnome-sushi", "xdg-user-dirs",
            "pipewire", "wireplumber", "libpipewire-0.3-0",
            "libwireplumber-0.5-0",
            "dbus-user-session", "dbus-x11", "network-manager", "libnm0",
            "xdg-desktop-portal-wlr", "xdg-dbus-proxy",
            "bluez", "bluez-tools", "pipewire-pulse",
            "ubuntu-restricted-extras", "gstreamer1.0-plugins-bad",
            "gstreamer1.0-libav", "ffmpegthumbnailer",
            "floorp", "flatpak", "tlp", "tlp-rdw", "fonts-powerline", "fonts-noto", "fonts-noto-mono",
            "cups-pk-helper", "kimageformat-plugins",
            sudo=True)


        # ── DMS (DankMaterialShell) via DankInstall oficial ──
        # Docs: https://danklinux.com/docs/dankinstall
        # Instalacion completa desatendida: Hyprland + kitty + todos los
        # accesorios (--all-features: dms-greeter, danksearch, dankcalendar).
        # Sin --replace-configs: no pisa configs existentes del usuario
        # (los que faltan si se deployan). Skip idempotente si dms ya esta.
        dms_installed = subprocess.run(
            ["dpkg", "-s", "dms"],
            capture_output=True,
        ).returncode == 0

        if not dms_installed:
            ok &= self.runner.ui.run_cmd(
                "DankInstall (hyprland + kitty + all features)",
                "bash", "-c",
                "sudo -v && curl -fsSL https://install.danklinux.com | "
                "sh -s -- -c hyprland -t kitty --all-features -y",
                sudo=True,
            )

            # ── Permisos para DMS ──
            if ok and TARGET_USER:
                home = os.path.expanduser(f"~{TARGET_USER}")
                ok &= self.runner.ui.run_cmd("fix ~/.config owner",
                    "chown", "-R", f"{TARGET_USER}:", f"{home}/.config",
                    sudo=True)
                ok &= self.runner.ui.run_cmd("add input group",
                    "usermod", "-aG", "input", TARGET_USER, sudo=True)
        else:
            self.runner.ui.run_cmd("dms already installed — skipping", "true")


        # ── Flatpak ──
        result = subprocess.run(
            ["flatpak", "remotes"],
            capture_output=True, text=True
        )
        if "flathub" not in result.stdout:
            ok &= self.runner.ui.run_cmd("add flathub",
                "flatpak", "remote-add", "--if-not-exists", "flathub",
                "https://dl.flathub.org/repo/flathub.flatpakrepo",
                sudo=True)

        for app in ("org.gnome.Papers", "net.nokyan.Resources",
                     "org.gnome.Showtime"):
            result = subprocess.run(
                ["flatpak", "list", "--app"],
                capture_output=True, text=True
            )
            if app not in result.stdout:
                ok &= self.runner.ui.run_cmd(f"flatpak install {app}",
                    "flatpak", "install", "--system", "-y", "flathub", app,
                    sudo=True)

        override_path = "/etc/flatpak/overrides/global"
        if not os.path.exists(override_path):
            os.makedirs("/etc/flatpak/overrides", exist_ok=True)
            with open(override_path, "w") as f:
                f.write("[Context]\nfilesystems=xdg-run/gvfs:host;host:ro;\n")

        return ok
