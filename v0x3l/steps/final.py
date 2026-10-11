# Step 5: Entorno — DMS (DankMaterialShell)
# (La instalacion de Hyprland se movio al Step 2: v0x3l/steps/packages.py)

import json
import os
import subprocess
from v0x3l.steps.base import BaseStep
from v0x3l.config import TARGET_USER, TARGET_HOME, DMS_FONTS_SRC
from v0x3l.shell import log


class DesktopStep(BaseStep):
    number = 5
    title = "Entorno"
    category = "final"

    def run(self) -> bool:
        success = True
        user = TARGET_USER

        # ── DMS (DankMaterialShell) via instalador oficial ──────
        # Skip idempotente si ya esta instalado (dpkg -s dms).
        dms_installed = subprocess.run(
            ["dpkg", "-s", "dms"],
            capture_output=True,
        ).returncode == 0

        if not dms_installed:
            ok = self.runner.ui.run_cmd(
                "Installing DMS via official installer",
                "bash", "-c",
                'sudo -v && curl -fsSL https://install.danklinux.com | '
                'sh -s -- -c hyprland -t kitty --include-deps dms-greeter '
                '--replace-configs-all -y',
                sudo=True,
            )
            if not ok:
                success = False

            # ── Permisos para DMS ──
            if ok and user:
                home = os.path.expanduser(f"~{user}")
                ok &= self.runner.ui.run_cmd("fix ~/.config owner",
                    "chown", "-R", f"{user}:", f"{home}/.config", sudo=True)
                ok &= self.runner.ui.run_cmd("add input group",
                    "usermod", "-aG", "input", user, sudo=True)
        else:
            self.runner.ui.run_cmd("dms already installed — skipping", "true")

        # ── Deshabilitar systemd service de DMS ──
        if user:
            self.runner.ui.run_cmd(
                "Disable dms systemd service (Hyprland uses exec-once)",
                "bash", "-c",
                'uid=$(id -u "$1"); '
                'loginctl enable-linger "$1" 2>/dev/null || true; '
                'systemctl start "user@$uid" 2>/dev/null || true; '
                'export XDG_RUNTIME_DIR="/run/user/$uid"; '
                'export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$uid/bus"; '
                'runuser -u "$1" -- systemctl --user daemon-reload 2>/dev/null; '
                'runuser -u "$1" -- systemctl --user disable dms 2>/dev/null || true',
                "dms-disable-svc", user, sudo=True,
            )

        # ── Fuentes de DMS (merge no destructivo en settings.json) ──
        self._apply_dms_fonts()

        return success

    def _apply_dms_fonts(self) -> None:
        """Aplica las fuentes de UI/mono al settings.json de DMS."""
        home = TARGET_HOME
        user = TARGET_USER
        dms_cfg_dir = f"{home}/.config/DankMaterialShell"
        settings_path = f"{dms_cfg_dir}/settings.json"

        if not os.path.isfile(DMS_FONTS_SRC):
            log(f"WARN dms fonts: falta el fragmento {DMS_FONTS_SRC} — no se aplicaron fonts")
            return

        try:
            with open(DMS_FONTS_SRC) as f:
                fonts = json.load(f)
            fonts = {k: v for k, v in fonts.items() if not k.startswith("_")}
        except (json.JSONDecodeError, OSError) as e:
            log(f"ERROR dms fonts: fragmento invalido {DMS_FONTS_SRC}: {e}")
            return

        existed = os.path.isfile(settings_path)
        settings = {}
        if existed:
            try:
                with open(settings_path) as f:
                    settings = json.load(f)
            except (json.JSONDecodeError, OSError):
                settings = {}

        settings.update(fonts)
        if not existed and "configVersion" not in settings:
            settings["configVersion"] = 12

        os.makedirs(dms_cfg_dir, exist_ok=True)
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)

        if user and os.geteuid() == 0:
            subprocess.run(["chown", "-R", f"{user}:", dms_cfg_dir], capture_output=True)
        log(f"dms fonts aplicadas: {fonts} -> {settings_path}")
