# Paso 5: Entorno — dotfiles + Oh My Zsh + LazyVim + harness omp
# (Noctalia/Umbriel/ly se instalan en Step 2: packages.py;
# dotfiles/zsh/lazyvim/omp al final para evitar conflictos con instaladores
# que tocan ~/.config y ~/.local)

import os
import shutil
import tempfile
from v0x3l.steps.base import BaseStep
from v0x3l.config import (TARGET_USER, TARGET_HOME,
                          DOTFILES_DIR, DOTFILES_MAP, OMP_HARNESS_REPO)
from v0x3l.shell import log

OMP_HARNESS_KEEP = ("config.yml", "models.yml", ".env")


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
        return ok and self._install_zsh_lazyvim() and self._install_omp_harness()

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

    @staticmethod
    def _omp_binary(home: str) -> str:
        """Ruta del binario omp instalado, o '' si no existe.

        El instalador oficial deja omp en ~/.local/bin (binario) o en
        ~/.bun/bin (instalacion via bun).
        """
        if not home:
            return ""
        for rel in (".local/bin/omp", ".bun/bin/omp"):
            path = os.path.join(home, rel)
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        return ""

    def _install_omp_harness(self) -> bool:
        """Instala omp y despliega el harness personal desde el repo.

        Docs: https://omp.sh/docs/quickstart
        El binario oficial vive en ~/.local/bin/omp. La configuracion se
        copia a ~/.omp/agent preservando config.yml, models.yml y .env: el
        endpoint y la API key se fijan despues de forma manual con
        scripts/setup.sh (genera la key e introduce la URL del proveedor).
        """
        user = TARGET_USER
        home = TARGET_HOME
        if not user or user == "root" or not home or home == "/root":
            log("ERROR omp: TARGET_USER/TARGET_HOME invalido")
            return False

        agent_dir = os.path.join(home, ".omp", "agent")

        # 1) Binario omp (instalador oficial, como usuario destino).
        # El instalador usa ~/.bun/bin si hay bun compatible y ~/.local/bin
        # si no; se resuelve el binario en vez de asumir una ruta.
        omp_bin = self._omp_binary(home)
        ok = True
        if not omp_bin:
            ok = self.runner.ui.run_cmd("install omp",
                "runuser", "-u", user, "--", "env", f"HOME={home}",
                "bash", "-c",
                "curl -fsSL https://omp.sh/install | sh",
                "omp-install", sudo=False)
            omp_bin = self._omp_binary(home)
        if not ok or not omp_bin:
            log("ERROR omp: fallo la instalacion del binario")
            return False

        # Enlace global: la sesion grafica y otros shells pueden no incluir
        # ~/.local/bin ni ~/.bun/bin en PATH.
        if os.geteuid() == 0:
            ok &= self.runner.ui.run_cmd("link omp in system PATH",
                "ln", "-sf", omp_bin, "/usr/local/bin/omp", sudo=True)

        # 2) Configuracion personal desde el repo.
        staging = tempfile.mkdtemp(prefix="v0x3l-omp-")
        try:
            if os.geteuid() == 0:
                shutil.chown(staging, user=user)
            clone = os.path.join(staging, "repo")
            if not self.runner.ui.run_cmd("clone omp-harness",
                    "runuser", "-u", user, "--", "env", f"HOME={home}",
                    "git", "clone", "--depth", "1", OMP_HARNESS_REPO, clone,
                    sudo=False):
                log("ERROR omp: no se pudo clonar el harness")
                return False
            if not self._deploy_omp_harness(clone, agent_dir):
                return False
        finally:
            shutil.rmtree(staging, ignore_errors=True)

        if os.geteuid() == 0:
            ok &= self.runner.ui.run_cmd("chown omp agent dir",
                "chown", "-R", f"{user}:", os.path.join(home, ".omp"),
                sudo=True)


        log("omp instalado. Configura endpoint y API key manualmente con: "
            f"sh {agent_dir}/scripts/setup.sh")
        return ok

    def _deploy_omp_harness(self, src: str, agent_dir: str) -> bool:
        """Copia el harness respetando los archivos locales del usuario."""
        if not os.path.isdir(src):
            log(f"ERROR omp: harness origen inexistente: {src}")
            return False
        keep = {}
        for name in OMP_HARNESS_KEEP:
            path = os.path.join(agent_dir, name)
            if os.path.isfile(path):
                with open(path, "rb") as f:
                    keep[name] = f.read()

        os.makedirs(agent_dir, exist_ok=True)
        for entry in os.listdir(src):
            if entry in (".git", ".gitignore"):
                continue
            source = os.path.join(src, entry)
            target = os.path.join(agent_dir, entry)
            if os.path.isdir(source):
                shutil.copytree(source, target, dirs_exist_ok=True)
            else:
                shutil.copy2(source, target)

        for name, content in keep.items():
            path = os.path.join(agent_dir, name)
            with open(path, "wb") as f:
                f.write(content)
            log(f"omp harness: se conservo {name} existente")
        return True
