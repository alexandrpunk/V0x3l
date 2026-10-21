# Step 5: Entorno — DMS (DankMaterialShell) + dotfiles + Oh My Zsh + LazyVim
# (DMS via apt/PPA; dotfiles/zsh/lazyvim al final para evitar conflictos
# con otros instaladores que tocan ~/.config)

import json
import os
import shutil
import subprocess
from v0x3l.steps.base import BaseStep
from v0x3l.config import (TARGET_USER, TARGET_HOME, DMS_FONTS_SRC,
                          DOTFILES_DIR, DOTFILES_MAP)
from v0x3l.shell import log


class DesktopStep(BaseStep):
    number = 5
    title = "Entorno"
    category = "final"

    def run(self) -> bool:
        success = True
        user = TARGET_USER

        # (DMS se instala y configura en Step 2: v0x3l/steps/packages.py)
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

        # ---- Dotfiles (assets/dotfiles → ~/.config del usuario) ----
        # Despliega cada entrada de DOTFILES_MAP a su ruta bajo $HOME. Es
        # idempotente (no sobrescribe si ya existe) y deja ownership al
        # usuario real (los cp corren como root).
        for src_name, dest_rel in DOTFILES_MAP.items():
            src = os.path.join(str(DOTFILES_DIR), src_name)
            dest = os.path.join(home, dest_rel)
            if os.path.exists(dest) or not os.path.exists(src):
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            self.runner.ui.run_cmd(f"deploy dotfile {src_name}",
                "cp", "-r", src, dest, sudo=True)
            if user and os.geteuid() == 0:
                subprocess.run(["chown", "-R", f"{user}:", dest],
                               capture_output=True)
        return self._install_zsh_lazyvim()

    def _install_zsh_lazyvim(self) -> bool:
        """Oh My Zsh + LazyVim al final: otros instaladores (DMS) pueden
        pisar ~/.config o dejarlo root-owned; haciendolo ultimo evita
        conflictos."""
        ok = True
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
