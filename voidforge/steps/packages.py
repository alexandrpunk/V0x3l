# Step 2: Software (mega-install + flatpak + zsh + lazyvim)

import subprocess
import os
from voidforge.steps.base import BaseStep


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
            "neovim", "zen-browser", "tmux", "fastfetch", "geany",
            "nwg-look", "foot", "dialog", "apt-utils",
            "libheif-plugin-libde265", "ufw", "gnome-sushi", "xdg-user-dirs",
            "pipewire", "wireplumber", "libpipewire-0.3-0",
            "libwireplumber-0.5-0",
            "dbus-user-session", "network-manager", "libnm0",
            "xdg-desktop-portal-wlr", "xdg-dbus-proxy",
            "bluez", "bluez-tools", "pipewire-pulse",
            "ubuntu-restricted-extras", "gstreamer1.0-plugins-bad",
            "gstreamer1.0-libav", "ffmpegthumbnailer",
            "flatpak", "tlp", "tlp-rdw", "fonts-powerline",
            sudo=True)

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
        user = os.environ.get("SUDO_USER", os.environ.get("USER", ""))
        home = f"/home/{user}" if user else "/root"

        zsh_path = subprocess.run(
            ["which", "zsh"], capture_output=True, text=True
        ).stdout.strip()
        if zsh_path:
            self.runner.ui.run_cmd("chsh",
                "chsh", "-s", zsh_path, user, sudo=True)

        if not os.path.exists(f"{home}/.oh-my-zsh"):
            ok &= self.runner.ui.run_cmd("install ohmyzsh",
                "sudo", "-u", user, "bash", "-c",
                'sh -c "$(curl -fsSL '
                'https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/'
                'tools/install.sh)" "" --unattended && '
                f'sed -i \"s/^ZSH_THEME=.*/ZSH_THEME=\\"agnoster\\"/\" '
                f'{home}/.zshrc',
                sudo=False)

        # ── LazyVim ──
        nvim_dir = f"{home}/.config/nvim"
        if not os.path.exists(f"{nvim_dir}/init.lua"):
            ok &= self.runner.ui.run_cmd("install lazyvim",
                "sudo", "-u", user, "bash", "-c",
                f"mv {nvim_dir} {nvim_dir}.bak 2>/dev/null || true; "
                f"mv {home}/.local/share/nvim {home}/.local/share/nvim.bak "
                f"2>/dev/null || true; "
                f"git clone https://github.com/LazyVim/starter {nvim_dir} "
                f"2>/dev/null; "
                f"rm -rf {nvim_dir}/.git 2>/dev/null || true",
                sudo=False)

        return ok
