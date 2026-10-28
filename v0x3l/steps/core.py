# Step 0: Preparacion del sistema (bootstrap + repos + locale + timezone)

import glob
import os
import subprocess

from v0x3l.config import BASE_DIR, TARGET_USER
from v0x3l.steps.base import BaseStep


class PreparationStep(BaseStep):
    number = 0
    title = "Preparacion del sistema"
    category = "core"

    def run(self) -> bool:
        ok = True

        # ── Bootstrap: herramientas base ──
        self.runner.ui.run_cmd("apt update",
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

        # ButterRepo (endpoint oficial apt.justaguy.dev).
        butterrepo_list = "/etc/apt/sources.list.d/butterrepo.list"
        butterrepo_current = False
        try:
            with open(butterrepo_list) as f:
                butterrepo_current = "https://apt.justaguy.dev" in f.read()
        except OSError:
            pass

        if not butterrepo_current:
            ok &= self.runner.ui.run_cmd("butterrepo key", "bash", "-c",
                "set -o pipefail && "
                "install -d -m 0755 /usr/share/keyrings && "
                "curl -fsSL https://apt.justaguy.dev/key.asc | "
                "gpg --dearmor --yes -o /usr/share/keyrings/butterrepo.gpg",
                sudo=True)
            ok &= self.runner.ui.run_cmd("butterrepo repo", "bash", "-c",
                'echo "deb [arch=amd64 signed-by=/usr/share/keyrings/butterrepo.gpg] '
                'https://apt.justaguy.dev stable main" | '
                f"tee {butterrepo_list}",
                sudo=True)

        # XanMod (kernel)
        if not os.path.exists("/etc/apt/sources.list.d/xanmod-release.list"):
            ok &= self.runner.ui.run_cmd("xanmod key", "bash", "-c",
                "set -o pipefail && "
                "wget -qO- https://dl.xanmod.org/archive.key | "
                "gpg --dearmor -vo /etc/apt/keyrings/xanmod-archive-keyring.gpg",
                sudo=True)
            ok &= self.runner.ui.run_cmd("xanmod repo", "bash", "-c",
                f'echo "deb [signed-by=/etc/apt/keyrings/xanmod-archive-keyring.gpg] '
                f'https://deb.xanmod.org {codename} main non-free" | '
                "tee /etc/apt/sources.list.d/xanmod-release.list",
                sudo=True)

        # Floorp
        if not os.path.exists("/etc/apt/sources.list.d/Floorp.list"):
            ok &= self.runner.ui.run_cmd("floorp key", "bash", "-c",
                "set -o pipefail && "
                "install -d -m 0755 /usr/share/keyrings && "
                "curl -fsSL https://ppa.floorp.app/KEY.gpg | "
                "gpg --dearmor -o /usr/share/keyrings/Floorp.gpg",
                sudo=True)
            ok &= self.runner.ui.run_cmd("floorp repo", "curl", "-sS", "--compressed",
                "-o", "/etc/apt/sources.list.d/Floorp.list",
                "https://ppa.floorp.app/Floorp.list",
                sudo=True)

        # ── Repositorio oficial Noctalia (Ubuntu 26.04 resolute) ──
        # Documentacion: https://docs.noctalia.dev/noctalia/getting-started/installation/
        # Provee: noctalia, umbriel y xdg-desktop-portal-umbriel
        noctalia_key_deb = "/tmp/noctalia-archive-keyring.deb"
        if not os.path.exists(noctalia_key_deb):
            ok &= self.runner.ui.run_cmd("install noctalia key",
                "bash", "-c",
                "set -euo pipefail; "
                "wget -q https://pkg.noctalia.dev/deb/nickh-archive-keyring.deb "
                f"-O {noctalia_key_deb} && "
                f"apt install -y {noctalia_key_deb}",
                sudo=True)
            try:
                os.remove(noctalia_key_deb)
            except OSError:
                pass
        noctalia_list = "/etc/apt/sources.list.d/noctalia-resolute.sources"
        if not os.path.exists(noctalia_list):
            ok &= self.runner.ui.run_cmd("add noctalia repo",
                "bash", "-c",
                "set -euo pipefail; "
                "wget -q https://pkg.noctalia.dev/deb/noctalia-resolute.sources "
                "-O /etc/apt/sources.list.d/noctalia-resolute.sources",
                sudo=True)

        # ── Actualizar paquetes (absorbe todos los repos) ──
        # nala update puede fallar transientemente (mirror, red, keyrings
        # recién agregados). Reintenta una vez; si sigue fallando, solo WARN
        # para no bloquear todo el paso: las instalaciones manejan su propio
        # error si falta un paquete del repo.
        nala_ok = self.runner.ui.run_cmd("nala update",
            "nala", "update", sudo=True)
        if not nala_ok:
            import time as _time
            _time.sleep(2)
            nala_ok = self.runner.ui.run_cmd("nala update (reintento)",
                "nala", "update", sudo=True)
        if not nala_ok:
            log("WARN nala update falló; continuando sin actualizar índice")
        # nala upgrade: one-shot con marker file. Evita re-upgradear todo en
        # cada re-run (lento, puede romper DKMS con kernel bumps).
        upgrade_marker = "/var/lib/v0x3l/.upgraded"
        if not os.path.exists(upgrade_marker):
            ok &= self.runner.ui.run_cmd("nala upgrade",
                "nala", "upgrade", "-y", sudo=True)
            os.makedirs(os.path.dirname(upgrade_marker), exist_ok=True)
            open(upgrade_marker, "w").close()

        # ── Grupos ──
        user = TARGET_USER
        if user:
            ok &= self.runner.ui.run_cmd("add groups",
                "usermod", "-aG", "video,render,audio,plugdev,netdev", user,
                sudo=True)

        # ── Timezone ──
        ok &= self.runner.ui.run_cmd("timezone",
            "timedatectl", "set-timezone", "America/Mazatlan", sudo=True)

        # ── Locale ──
        # Locale: genera es_MX.UTF-8 si falta y setea LANG + LANGUAGE siempre.
        target_locale = "es_MX.UTF-8"
        la = subprocess.run(["locale", "-a"], capture_output=True, text=True).stdout.lower()
        have = any("es_mx" in tok and "utf" in tok for tok in la.split())
        if not have:
            ok &= self.runner.ui.run_cmd("locale-gen", "bash", "-c",
                f"sed -i 's/^# *{target_locale} UTF-8/{target_locale} UTF-8/' "
                f"/etc/locale.gen; "
                f"grep -q '^{target_locale} UTF-8' /etc/locale.gen || "
                f"echo '{target_locale} UTF-8' >> /etc/locale.gen; "
                f"locale-gen",
                sudo=True)
        ok &= self.runner.ui.run_cmd("update-locale",
            "update-locale", f"LANG={target_locale}", "LANGUAGE=es_MX:es",
            sudo=True)

        return ok
