# Step 0: Preparacion del sistema (bootstrap + repos + locale + timezone + Pika)

import os
import subprocess
from voidforge.steps.base import BaseStep
from voidforge.config import BASE_DIR


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

        # ── ButterRepo ──
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

        # ── Pika OS Repo ──
        if not os.path.exists("/etc/apt/sources.list.d/pika.list"):
            os.makedirs("/etc/apt/keyrings", exist_ok=True)
            # Desarmar llave ASCII a binario
            self.runner.ui.run_cmd("pika key dearmor",
                "gpg", "--dearmor",
                "--output", "/etc/apt/keyrings/pika-keyring.gpg",
                f"{BASE_DIR}/assets/pika-keyring.gpg.key",
                sudo=True)
            self.runner.ui.run_cmd("chmod pika key",
                "chmod", "644", "/etc/apt/keyrings/pika-keyring.gpg",
                sudo=True)
            self.runner.ui.run_cmd("pika repo", "bash", "-c",
                'echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/pika-keyring.gpg] '
                'https://ppa.pika-os.com pika cockatiel" | '
                "tee /etc/apt/sources.list.d/pika.list",
                sudo=True)

            # Pinning: solo instalar paquetes explicitos de PikaOS,
            # no actualizar el resto del sistema desde este repo
            self.runner.ui.run_cmd("pika pin", "bash", "-c",
                'cat > /etc/apt/preferences.d/pika-pin << \'EOF\'\n'
                'Package: *\nPin: origin ppa.pika-os.com\nPin-Priority: 1\n\n'
                'Package: pikman-update-manager cosmic-app-library pika-device-manager\n'
                'Pin: origin ppa.pika-os.com\nPin-Priority: 500\n'
                'EOF',
                sudo=True)

        # ── Actualizar paquetes ──
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
