# Step 5: Entorno — dotfiles + Oh My Zsh + LazyVim
# (DMS/Dux se instala y configura en Step 2: v0x3l/steps/packages.py;
# dotfiles/zsh/lazyvim al final para evitar conflictos con instaladores
# que tocan ~/.config)

import os
import shutil
import subprocess
from v0x3l.steps.base import BaseStep
from v0x3l.config import (TARGET_USER, TARGET_HOME,
                          DOTFILES_DIR, DOTFILES_MAP)
from v0x3l.shell import log


class DesktopStep(BaseStep):
    number = 5
    title = "Entorno"
    category = "final"

    def run(self) -> bool:
        success = True
        user = TARGET_USER
        home = TARGET_HOME
        # (DMS/Dux se instala, configura y bindea dms.service a
        #  hyprland-session.target en Step 2: v0x3l/steps/packages.py.
        #  loginctl enable-linger ya corre en Step 3.)
        # ---- Dotfiles (assets/dotfiles → ~/.config del usuario) ----
        # Despliega cada entrada de DOTFILES_MAP a su ruta bajo $HOME. Es
        # idempotente (no sobrescribe si ya existe) y deja ownership al
        # usuario real (los cp corren como root).
        for src_name, dest_rel in DOTFILES_MAP.items():
            src = os.path.join(str(DOTFILES_DIR), src_name)
            dest = os.path.join(home, dest_rel)
            if not os.path.exists(src):
                continue
            if os.path.exists(dest) and src_name != "kitty":
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if src_name == "kitty" and os.path.isdir(dest):
                # Dux crea primero ~/.config/kitty; Butter reemplaza solo sus
                # archivos versionados y conserva otros archivos del usuario.
                self.runner.ui.run_cmd(f"deploy dotfile {src_name}",
                    "cp", "-r", f"{src}/.", dest, sudo=True)
            else:
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

        # ── LazyVim ──
        nvim_dir = f"{home}/.config/nvim"
        if not os.path.exists(f"{nvim_dir}/init.lua"):
            # Asegurar ~/.config existente y del usuario destino: varios
            # instaladores (dms setup, dotfiles deploy) corren como root y
            # pueden dejar ~/.config (o nvim/) root-owned; el clone como
            # usuario falla con "could not create work tree dir ...
            # Permission denied". Chown incondicional e inmediato antes
            # del clone.
            os.makedirs(f"{home}/.config", exist_ok=True)
            if user and os.geteuid() == 0:
                subprocess.run(["chown", "-R", f"{user}:", f"{home}/.config"],
                               capture_output=True)
                # chmod 755: por si quedo 0700 root o similar
                subprocess.run(["chmod", "755", f"{home}/.config"],
                               capture_output=True)
            # Backup de config/data existente
            shutil.rmtree(f"{nvim_dir}.bak", ignore_errors=True)
            if os.path.isdir(nvim_dir):
                shutil.move(nvim_dir, f"{nvim_dir}.bak")
            # Clonar LazyVim starter como usuario destino con runuser
            # (no depende de sudo ni de su env_reset; dms setup headless
            # usa el mismo patron para correr cosas como el usuario real).
            lok = self.runner.ui.run_cmd("install lazyvim",
                "runuser", "-u", user, "--",
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
