# Step 5: Entorno — DMS (DankMaterialShell)
# (La instalacion de Hyprland se movio al Step 2: v0x3l/steps/packages.py)

import os
import subprocess
from v0x3l.steps.base import BaseStep


class DesktopStep(BaseStep):
    number = 5
    title = "Entorno"
    category = "final"

    def run(self) -> bool:
        success = True
        user = os.environ.get("SUDO_USER", os.environ.get("USER", ""))

        # ── DMS (DankMaterialShell, repos agregados en Step 0) ──────
        # dms trae quickshell como dependencia; el greeter y los companeros
        # son opt-in y se anaden explicitamente.
        dms_installed = subprocess.run(
            ["dpkg", "-s", "dms"],
            capture_output=True,
        ).returncode == 0

        if not dms_installed:
            # Install DMS + ecosistema (dms trae quickshell como dep)
            ok = self.runner.ui.run_cmd(
                "Installing DMS ecosystem",
                "nala", "install", "-y",
                "dms",            # el shell (trae quickshell)
                "dms-greeter",    # greeter para greetd (login)
                "dgop",           # telemetria CPU/GPU para widgets
                "matugen",        # temas dinamicos Material
                "cliphist",       # historial de portapapeles
                "danksearch",     # busqueda en el lanzador
                sudo=True,
            )
            if not ok:
                success = False

            # ── dms greeter: configurar greetd como pantalla de login ──
            # Instala greetd, lo configura y deshabilita gdm/sddm/lightdm/
            # lxdm/xdm. No-interactivo (--yes). Best-effort: si falla no rompe
            # el step (los paquetes ya estan; el usuario puede re-correrlo).
            if ok:
                self.runner.ui.run_cmd(
                    "Configuring dms greeter (greetd)",
                    "dms", "greeter", "install", "--yes",
                    sudo=True,
                )

            # ── dms setup: desplegar configs de Hyprland (desatendido) ──
            # AL FINAL de la instalacion y desatendido. Se usan los subcomandos
            # en vez del bare 'dms setup' (que es interactivo y lanza wizard).
            # Con solo Hyprland + foot instalados, los subcomandos auto-detectan
            # compositor y terminal sin prompts. Fallan si el archivo ya existe
            # => se limpia ~/.config/hypr/dms/ antes. Corren como el usuario
            # destino (dms hace FATAL-exit si se ejecuta como root).
            if ok and user:
                home = os.path.expanduser(f"~{user}")
                # Asegurar ~/.config user-owned: dms setup (corriendo como el
                # usuario) crea ~/.config/hypr/dms y fallaria si ~/.config
                # esta root-owned.
                self.runner.ui.run_cmd("fix ~/.config owner",
                    "chown", "-R", f"{user}:", f"{home}/.config", sudo=True)
                dms_cfg = f"{home}/.config/hypr/dms"
                self.runner.ui.run_cmd("clear dms config",
                    "rm", "-rf", dms_cfg, sudo=True)
                for sub in ("binds", "colors", "layout", "outputs",
                            "cursor", "windowrules"):
                    self.runner.ui.run_cmd(f"dms setup {sub}",
                        "sudo", "-u", user, "-H",
                        "dms", "setup", sub, sudo=True)
                # grupo input (Caps Lock OSD): el bare 'dms setup' lo anade
                # via ensureInputGroup; los subcomandos no lo hacen.
                self.runner.ui.run_cmd("add input group",
                    "usermod", "-aG", "input", user, sudo=True)
        else:
            self.runner.ui.run_cmd("dms already installed — skipping", "true")

        # ── Deshabilitar systemd service de DMS ──
        # La doc de DMS (Managing Your Installation) dice explicitamente:
        # "Hyprland, Sway, MangoWC, and Miracle WM don't have systemd session
        #  targets. If you use multiple desktop environments and only want DMS
        #  on one of them, disable the systemd unit and start DMS from your
        #  compositor config instead."
        #
        # En Step 2 agregamos `exec-once = dms run` a hyprland.conf, asi que
        # aca deshabilitamos el systemd service para evitar doble inicio.
        # Corre SIEMPRE (fresh + re-run) para migrar instalaciones existentes.
        if user:
            self.runner.ui.run_cmd(
                "Disable dms systemd service (Hyprland uses exec-once)",
                "bash", "-c",
                'uid=$(id -u "$1"); '
                'loginctl enable-linger "$1" 2>/dev/null || true; '
                'systemctl start "user@$uid" 2>/dev/null || true; '
                'runuser -u "$1" -- systemctl --user daemon-reload 2>/dev/null; '
                'runuser -u "$1" -- systemctl --user disable dms 2>/dev/null || true',
                "dms-disable-svc", user, sudo=True,
            )

        return success
