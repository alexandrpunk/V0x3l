# Steps 0-1: bootstrap y repos

from voidforge.steps.base import BaseStep


class BootstrapStep(BaseStep):
    number = 0
    title = "Instalando herramientas base"
    category = "core"

    def run(self) -> bool:
        ok1 = self.runner.ui.run_cmd("apt update", "apt", "update", sudo=True)
        ok2 = self.runner.ui.run_cmd("apt install base",
            "apt", "install", "-y",
            "nala", "wget", "tar", "unzip", "file", "zsh", "git",
            "dialog", "apt-utils", "curl", "ca-certificates",
            "pciutils", "locales", "gnupg", "software-properties-common",
            sudo=True)
        return ok1 or ok2


class SystemPrepStep(BaseStep):
    number = 1
    title = "Configurando repositorios y sistema base"
    category = "core"

    def run(self) -> bool:
        ok = True

        # ButterRepo
        if not __import__("os").path.exists("/etc/apt/sources.list.d/butterrepo.list"):
            ok &= self.runner.ui.run_cmd("butterrepo key",
                "bash", "-c",
                "curl -fsSL https://justaguylinux.codeberg.page/butterrepo/key.asc | "
                "gpg --dearmor -o /usr/share/keyrings/butterrepo.gpg",
                sudo=True)
            ok &= self.runner.ui.run_cmd("butterrepo repo",
                "bash", "-c",
                'echo "deb [arch=amd64 signed-by=/usr/share/keyrings/butterrepo.gpg] '
                'https://justaguylinux.codeberg.page/butterrepo stable main" | '
                "tee /etc/apt/sources.list.d/butterrepo.list",
                sudo=True)

        # Update y upgrade
        ok &= self.runner.ui.run_cmd("nala update", "nala", "update", sudo=True)
        ok &= self.runner.ui.run_cmd("nala upgrade", "nala", "upgrade", "-y", sudo=True)

        # Grupos
        import os
        user = os.environ.get("SUDO_USER", os.environ.get("USER", ""))
        if user:
            self.runner.ui.run_cmd("add groups",
                "usermod", "-aG", "video,render,audio,plugdev,netdev", user,
                sudo=True)

        return ok
