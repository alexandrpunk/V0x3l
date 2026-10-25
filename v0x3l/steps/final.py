# Step 5: Entorno — dotfiles + Oh My Zsh + LazyVim
# (DMS/Dux se instala y configura en Step 2: v0x3l/steps/packages.py;
# dotfiles/zsh/lazyvim al final para evitar conflictos con instaladores
# que tocan ~/.config)

import os
import shutil
from v0x3l.steps.base import BaseStep
from v0x3l.config import (TARGET_USER, TARGET_HOME,
                          DOTFILES_DIR, DOTFILES_MAP)
from v0x3l.shell import log


class DesktopStep(BaseStep):
    number = 5
    title = "Entorno"
    category = "final"

    def run(self) -> bool:
        user = TARGET_USER
        home = TARGET_HOME
        if not user or not home or user == "root" or home == "/root":
            log("ERROR entorno: TARGET_USER/TARGET_HOME invalido; no se "
                "instalan dotfiles ni LazyVim como root")
            return False

        ok = True
        # ---- Dotfiles (assets/dotfiles → ~/.config del usuario) ----
        for src_name, dest_rel in DOTFILES_MAP.items():
            src = os.path.join(str(DOTFILES_DIR), src_name)
            dest = os.path.join(home, dest_rel)
            if not os.path.exists(src):
                continue
            if os.path.exists(dest) and src_name != "kitty":
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if src_name == "kitty" and os.path.isdir(dest):
                copied = self.runner.ui.run_cmd(f"deploy dotfile {src_name}",
                    "cp", "-r", f"{src}/.", dest, sudo=True)
            else:
                copied = self.runner.ui.run_cmd(f"deploy dotfile {src_name}",
                    "cp", "-r", src, dest, sudo=True)
            if not copied:
                log(f"ERROR dotfile: fallo al desplegar {src_name}")
                ok = False
                continue
            if os.geteuid() == 0:
                chowned = self.runner.ui.run_cmd(
                    f"chown dotfile {src_name}", "chown", "-R",
                    f"{user}:", dest, sudo=True)
                ok &= chowned
        return ok and self._install_zsh_lazyvim()

    def _install_zsh_lazyvim(self) -> bool:
        """Instala el starter oficial de LazyVim de forma idempotente.

        Sigue https://www.lazyvim.org/installation: respalda config, data,
        state y cache de Neovim; clona el starter y elimina su .git.
        """
        user = TARGET_USER
        home = TARGET_HOME
        if not user or user == "root" or not home or home == "/root":
            log("ERROR lazyvim: TARGET_USER/TARGET_HOME invalido")
            return False

        config_dir = os.path.join(home, ".config")
        nvim_dir = os.path.join(config_dir, "nvim")
        # El starter valido trae init.lua y lua/ (config y plugins). Un
        # init.lua suelto es una config ajena: se respalda y se reinstala.
        if (os.path.exists(os.path.join(nvim_dir, "init.lua"))
                and os.path.isdir(os.path.join(nvim_dir, "lua"))):
            return True

        os.makedirs(config_dir, exist_ok=True)
        if os.geteuid() == 0:
            if not self.runner.ui.run_cmd("chown nvim parent",
                    "chown", "-R", f"{user}:", config_dir, sudo=True):
                return False
            if not self.runner.ui.run_cmd("chmod nvim parent",
                    "chmod", "755", config_dir, sudo=True):
                return False

        # LazyVim documenta estos cuatro paths. No borres backups anteriores:
        # cada instalacion recibe un sufijo timestamped.
        from datetime import datetime
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_paths = (
            nvim_dir,
            os.path.join(home, ".local", "share", "nvim"),
            os.path.join(home, ".local", "state", "nvim"),
            os.path.join(home, ".cache", "nvim"),
        )
        for path in backup_paths:
            if not os.path.exists(path):
                continue
            backup = f"{path}.bak.{stamp}"
            try:
                shutil.move(path, backup)
            except OSError as exc:
                log(f"ERROR lazyvim: no se pudo respaldar {path}: {exc}")
                return False

        clone_ok = self.runner.ui.run_cmd("install lazyvim",
            "runuser", "-u", user, "--", "env",
            f"HOME={home}", f"USER={user}",
            "git", "clone", "--depth", "1",
            "https://github.com/LazyVim/starter", nvim_dir,
            sudo=False)
        if not clone_ok:
            log("ERROR lazyvim: git clone fallo; revisar red y permisos")
            return False

        git_dir = os.path.join(nvim_dir, ".git")
        if os.path.isdir(git_dir):
            shutil.rmtree(git_dir)
        if os.geteuid() == 0 and not self.runner.ui.run_cmd(
                "chown lazyvim", "chown", "-R", f"{user}:", nvim_dir,
                sudo=True):
            return False
        return True
