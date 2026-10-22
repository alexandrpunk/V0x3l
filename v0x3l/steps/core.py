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
            ok &= self.runner.ui.run_cmd("butterrepo key", "bash", "-c",
                "set -o pipefail && "
                "curl -fsSL https://justaguylinux.codeberg.page/butterrepo/key.asc | "
                "gpg --dearmor -o /usr/share/keyrings/butterrepo.gpg",
                sudo=True)
            ok &= self.runner.ui.run_cmd("butterrepo repo", "bash", "-c",
                'echo "deb [arch=amd64 signed-by=/usr/share/keyrings/butterrepo.gpg] '
                'https://justaguylinux.codeberg.page/butterrepo stable main" | '
                "tee /etc/apt/sources.list.d/butterrepo.list",
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

        # Dux Labs (Dux Shell / DMS 2.x) — docs: https://duxlabs.dev/docs/dms/installation#ubuntu
        # Ubuntu 26.04+ (resolute) via Launchpad PPA:
        #   duxlabs/dux  -> quickshell, matugen, dgop, danksearch, dankcalendar,
        #                   cliphist, dms-greeter (+ deps)
        #   duxlabs/dms  -> dms (shell + CLI)
        # --no-update: NO dejamos que add-apt-repository corra su apt update
        # interno por PPA; el `nala update` de abajo absorbe todos los repos en
        # una sola pasada. Idempotente: se salta si el .sources ya existe
        # (glob no hace cross-match dux<->dms, verificado).
        for ppa in ("ppa:duxlabs/dux", "ppa:duxlabs/dms"):
            name = ppa.split("/", 1)[1]
            if not glob.glob(f"/etc/apt/sources.list.d/duxlabs*{name}*"):
                ok &= self.runner.ui.run_cmd(f"add {ppa}",
                    "add-apt-repository", "-y", "--no-update", ppa, sudo=True)

        # ── Actualizar paquetes (absorbe todos los repos) ──
        ok &= self.runner.ui.run_cmd("nala update",
            "nala", "update", sudo=True)
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
            self.runner.ui.run_cmd("add groups",
                "usermod", "-aG", "video,render,audio,plugdev,netdev", user,
                sudo=True)

        # ── Timezone ──
        self.runner.ui.run_cmd("timezone",
            "timedatectl", "set-timezone", "America/Mazatlan", sudo=True)

        # ── Locale ──
        # Genera es_MX.UTF-8 si falta (idempotente + fallback: append a
        # locale.gen si la linea no viene en instalaciones minimas/server).
        # Setea LANG + LANGUAGE SIEMPRE (no solo al generar): sin LANGUAGE,
        # apps GNOME/gettext como Nautilus caen a ingles aunque LANG=es_MX.
        # Antes el update-locale estaba dentro del `if` y solo seteaba LANG,
        # por eso Nautilus quedaba en ingles en re-runs.
        target_locale = "es_MX.UTF-8"
        la = subprocess.run(["locale", "-a"], capture_output=True, text=True).stdout.lower()
        have = any("es_mx" in tok and "utf" in tok for tok in la.split())
        if not have:
            self.runner.ui.run_cmd("locale-gen", "bash", "-c",
                f"sed -i 's/^# *{target_locale} UTF-8/{target_locale} UTF-8/' "
                f"/etc/locale.gen; "
                f"grep -q '^{target_locale} UTF-8' /etc/locale.gen || "
                f"echo '{target_locale} UTF-8' >> /etc/locale.gen; "
                f"locale-gen",
                sudo=True)
        self.runner.ui.run_cmd("update-locale",
            "update-locale", f"LANG={target_locale}", "LANGUAGE=es_MX:es",
            sudo=True)

        return ok
