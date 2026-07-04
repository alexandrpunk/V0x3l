# Step 0: Preparacion del sistema (bootstrap + repos + locale + timezone)

import os
import subprocess

from v0x3l.config import BASE_DIR
from v0x3l.steps.base import BaseStep


class PreparationStep(BaseStep):
    number = 0
    title = "Preparacion del sistema"
    category = "core"

    def run(self) -> bool:
        ok = True

        # ── Bootstrap: herramientas base ──
        ok &= self.runner.ui.run_cmd("apt update",
            "apt", "update", sudo=True)
        ok &= self.runner.ui.run_cmd("apt install base",
            "apt", "install", "-y",
            "nala", "wget", "tar", "unzip", "file", "zsh", "git",
            "dialog", "apt-utils", "curl", "ca-certificates",
            "pciutils", "locales", "gnupg", "software-properties-common",
            sudo=True)

        # ── Repositorios y PPAs (centralizados en Step 0) ──
        codename = subprocess.run(
            ["lsb_release", "-sc"], capture_output=True, text=True
        ).stdout.strip()

        # ButterRepo
        if not os.path.exists("/etc/apt/sources.list.d/butterrepo.list"):
            self.runner.ui.run_cmd("butterrepo key", "bash", "-c",
                "curl -fsSL https://justaguylinux.codeberg.page/butterrepo/key.asc | "
                "gpg --dearmor -o /usr/share/keyrings/butterrepo.gpg",
                sudo=True)
            self.runner.ui.run_cmd("butterrepo repo", "bash", "-c",
                'echo "deb [arch=amd64 signed-by=/usr/share/keyrings/butterrepo.gpg] '
                'https://justaguylinux.codeberg.page/butterrepo stable main" | '
                "tee /etc/apt/sources.list.d/butterrepo.list",
                sudo=True)

        # XanMod (kernel)
        if not os.path.exists("/etc/apt/sources.list.d/xanmod-release.list"):
            self.runner.ui.run_cmd("xanmod key", "bash", "-c",
                "wget -qO- https://dl.xanmod.org/archive.key | "
                "gpg --dearmor -vo /etc/apt/keyrings/xanmod-archive-keyring.gpg",
                sudo=True)
            self.runner.ui.run_cmd("xanmod repo", "bash", "-c",
                f'echo "deb [signed-by=/etc/apt/keyrings/xanmod-archive-keyring.gpg] '
                f'https://deb.xanmod.org {codename} main non-free" | '
                "tee /etc/apt/sources.list.d/xanmod-release.list",
                sudo=True)

        # Hyprland (PPA cppiber)
        if not os.path.exists("/etc/apt/sources.list.d/cppiber-hyprland.list"):
            self.runner.ui.run_cmd("hyprland key", "bash", "-c",
                "install -d -m 0755 /etc/apt/keyrings && "
                "curl -fsSL 'https://keyserver.ubuntu.com/pks/lookup?op=get"
                "&search=0xA54D23B62FF3FCC76EFF71E8FDBAAA1CF0CCF48E' | "
                "gpg --dearmor -o /etc/apt/keyrings/cppiber-hyprland.gpg",
                sudo=True)
            self.runner.ui.run_cmd("hyprland repo", "bash", "-c",
                f'echo "deb [signed-by=/etc/apt/keyrings/cppiber-hyprland.gpg] '
                f'https://ppa.launchpadcontent.net/cppiber/hyprland/ubuntu '
                f'{codename} main" | '
                "tee /etc/apt/sources.list.d/cppiber-hyprland.list",
                sudo=True)

        # Floorp
        if not os.path.exists("/etc/apt/sources.list.d/Floorp.list"):
            self.runner.ui.run_cmd("floorp key", "bash", "-c",
                "install -d -m 0755 /usr/share/keyrings && "
                "curl -fsSL https://ppa.floorp.app/KEY.gpg | "
                "gpg --dearmor -o /usr/share/keyrings/Floorp.gpg",
                sudo=True)
            self.runner.ui.run_cmd("floorp repo", "curl", "-sS", "--compressed",
                "-o", "/etc/apt/sources.list.d/Floorp.list",
                "https://ppa.floorp.app/Floorp.list",
                sudo=True)

        # DMS (PPAs avengemedia: danklinux = dependencias, dms = shell)
        if subprocess.run(["grep", "-rqsF", "avengemedia/danklinux",
                           "/etc/apt/sources.list.d/"],
                          capture_output=True).returncode != 0:
            self.runner.ui.run_cmd("add danklinux PPA",
                "add-apt-repository", "-y", "ppa:avengemedia/danklinux", sudo=True)
        if subprocess.run(["grep", "-rqsF", "avengemedia/dms",
                           "/etc/apt/sources.list.d/"],
                          capture_output=True).returncode != 0:
            self.runner.ui.run_cmd("add dms PPA",
                "add-apt-repository", "-y", "ppa:avengemedia/dms", sudo=True)

        # ── Actualizar paquetes (absorbe todos los repos) ──
        ok &= self.runner.ui.run_cmd("nala update",
            "nala", "update", sudo=True)
        ok &= self.runner.ui.run_cmd("nala upgrade",
            "nala", "upgrade", "-y", sudo=True)

        # ── Grupos ──
        user = os.environ.get("SUDO_USER", os.environ.get("USER", ""))
        if user:
            self.runner.ui.run_cmd("add groups",
                "usermod", "-aG", "video,render,audio,plugdev,netdev", user,
                sudo=True)

        # ── Timezone ──
        self.runner.ui.run_cmd("timezone",
            "timedatectl", "set-timezone", "America/Mazatlan", sudo=True)

        # ── Locale ──
        result = subprocess.run(["locale", "-a"], capture_output=True, text=True)
        if "es_MX.utf8" not in result.stdout:
            self.runner.ui.run_cmd("locale-gen", "bash", "-c",
                "sed -i 's/^# *es_MX\\.UTF-8 UTF-8/es_MX.UTF-8 UTF-8/' "
                "/etc/locale.gen && locale-gen", sudo=True)
            self.runner.ui.run_cmd("update-locale",
                "update-locale", "LANG=es_MX.UTF-8", sudo=True)

        return ok
