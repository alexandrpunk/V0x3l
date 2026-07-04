# Step 5: Entorno — Noctalia Shell v4 + Hyprland

import os
import subprocess
from v0x3l.steps.base import BaseStep


class DesktopStep(BaseStep):
    number = 5
    title = "Entorno"
    category = "final"

    def run(self) -> bool:
        user = os.environ.get("SUDO_USER", os.environ.get("USER", ""))
        success = True

        # ── Noctalia Shell v4 ──────────────────────────────────────
        noctalia_installed = os.path.exists("/usr/bin/noctalia-shell") or \
                             os.path.exists("/usr/bin/noctalia-qs")

        if not noctalia_installed:
            # Import GPG key
            ok = self.runner.ui.run_cmd(
                "Importing Noctalia GPG key",
                "bash", "-c",
                "curl -fsSL https://pkg.noctalia.dev/gpg.key | "
                "gpg --dearmor -o /etc/apt/keyrings/noctalia.gpg",
                sudo=True,
            )
            if not ok:
                success = False

            # Add APT repository
            if ok:
                ok = self.runner.ui.run_cmd(
                    "Adding Noctalia APT repository",
                    "bash", "-c",
                    "echo 'deb [signed-by=/etc/apt/keyrings/noctalia.gpg] "
                    "https://pkg.noctalia.dev/apt trixie main' "
                    "> /etc/apt/sources.list.d/noctalia.list",
                    sudo=True,
                )
                if not ok:
                    success = False

            # Update package lists
            if ok:
                ok = self.runner.ui.run_cmd(
                    "Updating package lists (nala)",
                    "nala", "update",
                    sudo=True,
                )
                if not ok:
                    success = False

            # Install noctalia-shell
            if ok:
                ok = self.runner.ui.run_cmd(
                    "Installing noctalia-shell",
                    "nala", "install", "-y", "noctalia-shell",
                    sudo=True,
                )
                if not ok:
                    success = False
        else:
            self.runner.ui.run_cmd("Noctalia Shell already installed — skipping", "true")

        # ── Hyprland (via PPA cppiber/hyprland) ──────────────────────
        # PPA que aporta Hyprland 0.55.x sobre Ubuntu 26.04. Se instala el
        # minimo: compositor + portal. El resto (hypridle/hyprlock/hyprpaper,
        # barra, lanzador, terminal, notificaciones, ...) lo provee Noctalia
        # Shell y el step de Software. Los kernel params de NVIDIA
        # (nvidia-drm.modeset=1, initramfs) ya los gestiona theming.py.
        hyprland_installed = os.path.exists("/usr/bin/Hyprland") or \
                             os.path.exists("/usr/local/bin/Hyprland")

        if not hyprland_installed:
            # Import GPG key del PPA (Launchpad signing key)
            ok = self.runner.ui.run_cmd(
                "Importing Hyprland PPA key",
                "bash", "-c",
                "install -d -m 0755 /etc/apt/keyrings && "
                "curl -fsSL 'https://keyserver.ubuntu.com/pks/lookup?op=get"
                "&search=0xA54D23B62FF3FCC76EFF71E8FDBAAA1CF0CCF48E' | "
                "gpg --dearmor -o /etc/apt/keyrings/cppiber-hyprland.gpg",
                sudo=True,
            )
            if not ok:
                success = False

            # Add PPA source list
            if ok:
                ok = self.runner.ui.run_cmd(
                    "Adding Hyprland PPA repository",
                    "bash", "-c",
                    'echo "deb [signed-by=/etc/apt/keyrings/cppiber-hyprland.gpg] '
                    'https://ppa.launchpadcontent.net/cppiber/hyprland/ubuntu '
                    '$(lsb_release -sc) main" '
                    '> /etc/apt/sources.list.d/cppiber-hyprland.list',
                    sudo=True,
                )
                if not ok:
                    success = False

            # Update package lists
            if ok:
                ok = self.runner.ui.run_cmd(
                    "Updating package lists (nala)",
                    "nala", "update", sudo=True,
                )
                if not ok:
                    success = False

            # Install Hyprland minimum (compositor + portal). El resto
            # (hypridle/hyprlock/hyprpaper, barra, terminal, ...) lo provee
            # Noctalia Shell y el step de Software.
            if ok:
                ok = self.runner.ui.run_cmd(
                    "Installing Hyprland ecosystem",
                    "nala", "install", "-y",
                    "hyprland", "xdg-desktop-portal-hyprland",
                    sudo=True,
                )
                if not ok:
                    success = False

            # Write Hyprland config (NVIDIA env vars if applicable)
            if ok:
                self._write_hyprland_config(user)
        else:
            self.runner.ui.run_cmd("Hyprland already installed — skipping", "true")

        return success

    def _write_hyprland_config(self, user: str) -> None:
        """Escribe ~/.config/hypr/hyprland.conf (config minimo de respaldo).

        Idempotente: no sobreescribe si ya existe (Noctalia puede proveer el
        suyo). Solo fija monitor, input, binds de sesion y las env vars de
        NVIDIA; la barra/lanzador/terminal/notificaciones corren por cuenta
        de Noctalia. Los kernel params de NVIDIA ya los pone theming.py.
        """
        home = os.path.expanduser(f"~{user}") if user else os.path.expanduser("~")
        hypr_dir = f"{home}/.config/hypr"
        hypr_conf = f"{hypr_dir}/hyprland.conf"
        if os.path.exists(hypr_conf):
            return

        os.makedirs(hypr_dir, exist_ok=True)
        has_nvidia = os.environ.get("HAS_NVIDIA_GPU", "0") == "1"

        nvidia_block = (
            "# ── NVIDIA ──\n"
            "env = LIBVA_DRIVER_NAME,nvidia\n"
            "env = __GLX_VENDOR_LIBRARY_NAME,nvidia\n"
            "env = NVD_BACKEND,direct\n"
            "env = GBM_BACKEND,nvidia-drm\n\n"
        ) if has_nvidia else ""

        config = (
            "# Generated by V0x3l — config minimo de respaldo.\n"
            "# Noctalia Shell provee barra, lanzador, terminal y "
            "notificaciones.\n\n"
            f"{nvidia_block}"
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

        # Asegurar ownership del usuario real (el script corre como root)
        if user and os.geteuid() == 0:
            subprocess.run(["chown", "-R", f"{user}:", hypr_dir], check=False)
