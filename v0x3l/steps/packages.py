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
            "floorp", "flatpak", "tlp", "tlp-rdw", "fonts-powerline", "fonts-noto", "fonts-noto-mono",
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
        """Escribe ~/.config/hypr/hyprland.conf con exec-once dms + env Qt.

        Idempotente: no sobreescribe si ya existe. En re-runs asegura que las
        lineas exec-once, env vars de Qt y los source de DMS esten presentes
        (append si falta).

        Segun la doc de DMS (Managing Your Installation), Hyprland NO tiene
        systemd session targets nativos. El approach correcto es exec-once
        directo (dms run) + deshabilitar el service de systemd (Step 5).
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

        # Qt env vars: obligatorias para DMS (Quickshell/Qt). Sin
        # QT_QPA_PLATFORM=wayland, Qt intenta usar xcb y falla.
        qt_env = (
            "# ── DMS / Qt environment ──\n"
            "env = QT_QPA_PLATFORM,wayland\n"
            "env = QT_QPA_PLATFORMTHEME,gtk3\n"
            "env = ELECTRON_OZONE_PLATFORM_HINT,auto\n\n"
        )

        # exec-once: dbus-update (necesario para XDG Desktop Portal y servicios
        # systemd) + dms run (lanza DMS directamente). La doc de DMS dice:
        # "Hyprland... don't have systemd session targets" -> usar exec-once.
        dms_exec = (
            "# ── DMS startup (exec-once directo, ver DMS managing docs) ──\n"
            "exec-once = dbus-update-activation-environment --systemd --all\n"
            "exec-once = dms run\n\n"
        )

        # DMS sourced configs: los subcomandos 'dms setup ...' (Step 5) crean
        # archivos en ~/.config/hypr/dms/. Sin source =, Hyprland los ignora.
        dms_source = (
            "# ── DMS sourced configs (creados por Step 5) ──\n"
            "source = ~/.config/hypr/dms/binds.conf\n"
            "source = ~/.config/hypr/dms/colors.conf\n"
            "source = ~/.config/hypr/dms/layout.conf\n"
            "source = ~/.config/hypr/dms/outputs.conf\n"
            "source = ~/.config/hypr/dms/cursor.conf\n"
            "source = ~/.config/hypr/dms/windowrules.conf\n"
        )

        if not os.path.exists(hypr_conf):
            config = (
                "# Generated by V0x3l — config minimo de respaldo.\n"
                "# DMS provee barra, lanzador, terminal y "
                "notificaciones.\n\n"
                f"{nvidia_block}"
                f"{qt_env}"
                f"{dms_exec}"
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
                f"\n{dms_source}"
            )
            with open(hypr_conf, "w") as f:
                f.write(config)
        else:
            # Re-run: asegurar que exec-once dms, env Qt y los source DMS
            # esten presentes (append si falta).
            with open(hypr_conf) as f:
                content = f.read()
            if "dms run" not in content:
                with open(hypr_conf, "a") as f:
                    f.write("\n" + dms_exec)
            if "QT_QPA_PLATFORM" not in content:
                with open(hypr_conf, "a") as f:
                    f.write("\n" + qt_env)
            if "~/.config/hypr/dms/binds.conf" not in content:
                with open(hypr_conf, "a") as f:
                    f.write("\n" + dms_source)

        if user and os.geteuid() == 0:
            subprocess.run(["chown", "-R", f"{user}:", hypr_dir], check=False)
