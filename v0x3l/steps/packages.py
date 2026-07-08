# Step 2: Software (mega-install + flatpak + zsh + lazyvim)

import os
import shutil
import subprocess

from v0x3l.steps.base import BaseStep
from v0x3l.config import HYPR_LUA_SRC, HYPR_DMS_DIR


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

        # Deploy del config de Hyprland (hyprland.lua). Se ejecuta siempre que
        # Hyprland este presente. El template incluye env Qt, exec-once dms run,
        # require("dms.*") para cargar configs de DMS (Step 5), y deteccion
        # NVIDIA en runtime.
        if os.path.exists("/usr/bin/Hyprland") or os.path.exists("/usr/local/bin/Hyprland"):
            self._write_hyprland_config()
            # Ocultar la sesion "Hyprland (uwsm-managed)" del greeter: requiere
            # uwsm (no instalado, no lo necesitamos — arrancamos DMS via exec-once
            # directo). Sin esto, greetd muestra dos sesiones y la uwsm falla.
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
            # Asegurar que ~/.config exista (git clone no crea dirs intermedios)
            os.makedirs(f"{home}/.config", exist_ok=True)
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
            ok &= lok
            # Limpiar .git + asegurar ownership del usuario
            if os.path.isdir(nvim_dir):
                shutil.rmtree(f"{nvim_dir}/.git", ignore_errors=True)
                subprocess.run(["chown", "-R", f"{user}:", nvim_dir],
                               capture_output=True)

        return ok

    def _write_hyprland_config(self) -> None:
        """Deploya ~/.config/hypr/hyprland.lua + dms/*.lua desde assets.

        Usa el formato Lua (Hyprland 0.55+) porque DMS genera configs .lua
        (require("dms.*")), no .conf. Mezclar formatos no funciona: source=
        no puede cargar .lua y require() no anda en .conf.

        Deploya:
          - hyprland.lua (config principal con env Qt, NVIDIA runtime detect,
            exec-once dms run, require("dms.*"), keyboard latam)
          - dms/*.lua (7 modulos: binds, colors, layout, outputs, cursor,
            windowrules, binds-user — pre-stageados desde templates de DMS)

        Migracion .conf -> .lua: si existe hyprland.conf viejo, se backupea
        a hyprland.conf.bak (hyprland.lua tiene precedencia sobre .conf).
        """
        user = os.environ.get("SUDO_USER", os.environ.get("USER", ""))
        home = os.path.expanduser(f"~{user}") if user else os.path.expanduser("~")
        hypr_dir = f"{home}/.config/hypr"
        hypr_lua = f"{hypr_dir}/hyprland.lua"
        hypr_conf = f"{hypr_dir}/hyprland.conf"
        dms_dest = f"{hypr_dir}/dms"
        os.makedirs(hypr_dir, exist_ok=True)

        # Deployar hyprland.lua desde el template (sobreescribe: es config managed)
        if os.path.isfile(HYPR_LUA_SRC):
            shutil.copy(HYPR_LUA_SRC, hypr_lua)

        # Deployar dms/*.lua (7 modulos pre-stageados). dirs_exist_ok permite
        # sobreescribir en re-runs sin error.
        if os.path.isdir(HYPR_DMS_DIR):
            shutil.copytree(HYPR_DMS_DIR, dms_dest, dirs_exist_ok=True)

        # Migracion: backupear hyprland.conf viejo si existe (.lua tiene precedencia)
        if os.path.isfile(hypr_conf) and not os.path.isfile(f"{hypr_conf}.bak"):
            os.rename(hypr_conf, f"{hypr_conf}.bak")

        if user and os.geteuid() == 0:
            subprocess.run(["chown", "-R", f"{user}:", hypr_dir], check=False)
