# Step 2: Software (mega-install + flatpak + zsh + lazyvim)

import os
import shutil
import subprocess

from v0x3l.steps.base import BaseStep
from v0x3l.config import TARGET_USER, TARGET_HOME
from v0x3l.shell import log


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
            "nwg-look", "foot", "dialog", "apt-utils",
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

        # ── Hyprland ─────────────────────────────────────────────
        # La instalacion de DMS + Hyprland + configs la hace el instalador
        # oficial de DankLinux (headless) en Step 5 (v0x3l/steps/final.py).
        # Aca solo saneamos la lista de sesiones del greeter.

        # Ocultar la sesion "Hyprland (uwsm-managed)" del greeter: requiere
        # uwsm (no instalado, no lo necesitamos). Sin esto, greetd muestra
        # dos sesiones y la uwsm falla.
        if os.path.exists("/usr/bin/Hyprland") or \
           os.path.exists("/usr/local/bin/Hyprland"):
            uwsm_desktop = "/usr/share/wayland-sessions/hyprland-uwsm.desktop"
            if os.path.isfile(uwsm_desktop):
                self.runner.ui.run_cmd("remove uwsm session from greeter",
                    "rm", "-f", uwsm_desktop, sudo=True)

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

        # ── Oh My Zsh ──
        user = TARGET_USER
        home = TARGET_HOME

        zsh_path = subprocess.run(
            ["which", "zsh"], capture_output=True, text=True
        ).stdout.strip()
        if zsh_path:
            ok &= self.runner.ui.run_cmd("chsh",
                "chsh", "-s", zsh_path, user, sudo=True)

        if not os.path.exists(f"{home}/.oh-my-zsh"):
            ok &= self.runner.ui.run_cmd("install ohmyzsh",
                "sudo", "-u", user, "-H", "bash", "-c",
                'sh -c "$(curl -fsSL '
                'https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/'
                'tools/install.sh)" "" --unattended && '
                f'sed -i \"s/^ZSH_THEME=.*/ZSH_THEME=\\"agnoster\\"/\" '
                f'{home}/.zshrc',
                sudo=False)

        # ── LazyVim ──
        nvim_dir = f"{home}/.config/nvim"
        if not os.path.exists(f"{nvim_dir}/init.lua"):
            # Asegurar que ~/.config exista y sea del usuario destino:
            # el instalador de DMS corre como root y puede dejar ~/.config
            # root-owned; si ~/.config no existia
            # (Step 1 salto su chown por el guard isdir, o venimos de un resume),
            # queda root-owned y el `sudo -u <user> git clone` hacia ~/.config/nvim
            # falla con permission denied, dejando nvim/ vacio.
            os.makedirs(f"{home}/.config", exist_ok=True)
            if user and os.geteuid() == 0:
                subprocess.run(["chown", "-R", f"{user}:", f"{home}/.config"],
                               capture_output=True)
            # Backup de config/data existente
            shutil.rmtree(f"{nvim_dir}.bak", ignore_errors=True)
            if os.path.isdir(nvim_dir):
                shutil.move(nvim_dir, f"{nvim_dir}.bak")
            # Clonar LazyVim starter como el usuario destino. -H setea HOME
            # correcto para git. Sin 2>/dev/null: los errores deben verse.
            lok = self.runner.ui.run_cmd("install lazyvim",
                "sudo", "-u", user, "-H",
                "git", "clone", "--depth", "1",
                "https://github.com/LazyVim/starter", nvim_dir,
                sudo=False)
            if not lok:
                log("ERROR lazyvim: git clone fallo — revisar permisos de "
                    f"{home}/.config o red. nvim/ puede quedar vacio.")
            ok &= lok
            # Limpiar .git + asegurar ownership del usuario
            if os.path.isdir(nvim_dir):
                shutil.rmtree(f"{nvim_dir}/.git", ignore_errors=True)
                subprocess.run(["chown", "-R", f"{user}:", nvim_dir],
                               capture_output=True)

        return ok

