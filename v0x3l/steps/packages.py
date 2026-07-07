# Step 2: Software (mega-install + flatpak + zsh + lazyvim)

import os
import subprocess

from v0x3l.steps.base import BaseStep


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
            "flatpak", "tlp", "tlp-rdw", "fonts-powerline", "fonts-noto", "fonts-noto-mono",
            sudo=True)

        # ── Hyprland (repo agregado en Step 0) ─────────────────────
        # Minimo: compositor + portal. El resto (barra, lanzador, terminal,
        # notificaciones, ...) lo provee DMS (Step 5). Los kernel params de
        # NVIDIA ya los gestiona theming.py.
        hyprland_installed = os.path.exists("/usr/bin/Hyprland") or \
                             os.path.exists("/usr/local/bin/Hyprland")
        if not hyprland_installed:
            hok = self.runner.ui.run_cmd(
                "Installing Hyprland ecosystem",
                "nala", "install", "-y",
                "hyprland", "xdg-desktop-portal-hyprland",
                sudo=True)
            ok &= hok
        else:
            self.runner.ui.run_cmd("Hyprland already installed — skipping", "true")

        # Config de Hyprland + init de sesion systemd (idempotente). Se ejecuta
        # siempre que Hyprland este presente: en fresh-install escribe el config
        # completo; en re-runs asegura las lineas exec-once que activan
        # graphical-session.target (requerido por dms.service).
        if os.path.exists("/usr/bin/Hyprland") or os.path.exists("/usr/local/bin/Hyprland"):
            self._write_hyprland_config()

        # ── Floorp (repo agregado en Step 0) ─────────────────────────
        floorp_installed = subprocess.run(
            ["dpkg", "-s", "floorp"],
            capture_output=True,
        ).returncode == 0
        if not floorp_installed:
            fok = self.runner.ui.run_cmd(
                "Installing floorp",
                "nala", "install", "-y", "floorp", sudo=True)
            ok &= fok
        else:
            self.runner.ui.run_cmd("floorp already installed — skipping", "true")

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

    def _write_hyprland_config(self) -> None:
        """Escribe ~/.config/hypr/hyprland.conf (config minimo de respaldo).

        Idempotente: no sobreescribe si ya existe (DMS puede proveer el
        suyo). Solo fija monitor, input, binds de sesion y las env vars de
        NVIDIA; la barra/lanzador/terminal/notificaciones corren por cuenta
        de DMS. Los kernel params de NVIDIA ya los pone theming.py.
        """
        user = os.environ.get("SUDO_USER", os.environ.get("USER", ""))
        home = os.path.expanduser(f"~{user}") if user else os.path.expanduser("~")
        hypr_dir = f"{home}/.config/hypr"
        hypr_conf = f"{hypr_dir}/hyprland.conf"
        os.makedirs(hypr_dir, exist_ok=True)
        has_nvidia = os.environ.get("HAS_NVIDIA_GPU", "0") == "1"

        nvidia_block = (
            "# ── NVIDIA ──\n"
            "env = LIBVA_DRIVER_NAME,nvidia\n"
            "env = __GLX_VENDOR_LIBRARY_NAME,nvidia\n"
            "env = NVD_BACKEND,direct\n"
            "env = GBM_BACKEND,nvidia-drm\n\n"
        ) if has_nvidia else ""

        # CRITICO: estas dos lineas activan graphical-session.target al iniciar
        # Hyprland. Sin ellas, dms.service (Requisite=graphical-session.target)
        # y otros servicios de usuario NO arrancan -> DMS no renderiza.
        session_init = (
            "# ── Systemd session init (requerido por dms.service) ──\n"
            "exec-once = dbus-update-activation-environment --systemd --all\n"
            "exec-once = systemctl --user start hyprland-session.target\n\n"
        )

        if not os.path.exists(hypr_conf):
            config = (
                "# Generated by V0x3l — config minimo de respaldo.\n"
                "# DMS provee barra, lanzador, terminal y "
                "notificaciones.\n\n"
                f"{nvidia_block}"
                f"{session_init}"
                "# ── Monitors ──\n"
                "monitor = ,preferred,auto,1\n\n"
                "# ── Input ──\n"
                "input {\n"
                "    kb_layout = latam\n"
                "    follow_mouse = 1\n"
                "    touchpad { natural_scroll = yes }\n"
                "}\n\n"
                "# ── Keybindings de sesion ──\n"
                "bind = SUPER, Q,      killactive,\n"
                "bind = SUPER CTRL, Q, exit,\n"
                "bind = SUPER, V,      togglefloating,\n"
                "bind = SUPER, 1, workspace, 1\n"
                "bind = SUPER, 2, workspace, 2\n"
                "bind = SUPER, 3, workspace, 3\n"
                "bind = SUPER, 4, workspace, 4\n"
                "bind = SUPER, 5, workspace, 5\n"
            )
            with open(hypr_conf, "w") as f:
                f.write(config)
        else:
            # Re-run: asegurar que el session init este presente (no sobrescribe
            # el resto del config del usuario).
            with open(hypr_conf) as f:
                content = f.read()
            if "hyprland-session.target" not in content:
                with open(hypr_conf, "a") as f:
                    f.write("\n" + session_init)

        if user and os.geteuid() == 0:
            subprocess.run(["chown", "-R", f"{user}:", hypr_dir], check=False)
