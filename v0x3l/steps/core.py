# Step 0: Preparacion del sistema (bootstrap + repos + locale + timezone)

import os
import subprocess
from v0x3l.shell import log
from v0x3l.config import BASE_DIR, TARGET_USER
from v0x3l.steps.base import BaseStep


class PreparationStep(BaseStep):
    number = 0
    title = "Preparacion del sistema"
    category = "core"

    def run(self) -> bool:
        ok = True

        # ---- Helpers ----
        def run_critical(desc: str, *args, **kwargs) -> bool:
            """Ejecuta comando crítico; falla ok si falla."""
            try:
                result = self.runner.ui.run_cmd(desc, *args, **kwargs)
                if not result:
                    log(f"ERROR {desc}: comando fallo (critico)")
                return result
            except Exception as e:
                log(f"ERROR {desc}: excepcion {type(e).__name__}: {e}")
                return False

        def run_nonfatal(desc: str, *args, **kwargs) -> bool:
            """Ejecuta comando no crítico; loggea warning si falla pero no rompe ok."""
            try:
                result = self.runner.ui.run_cmd(desc, *args, **kwargs)
                if not result:
                    log(f"WARN {desc}: comando fallo (no fatal)")
                return result
            except Exception as e:
                log(f"WARN {desc}: excepcion {type(e).__name__}: {e}")
                return False

        def write_file_if_missing(path: str, content: str, mode: int = 0o644) -> bool:
            """Escribe archivo solo si no existe."""
            try:
                if not os.path.exists(path):
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, "w") as f:
                        f.write(content)
                    os.chmod(path, mode)
                    log(f"INFO escrito: {path}")
                    return True
                return False
            except Exception as e:
                log(f"ERROR escribiendo {path}: {type(e).__name__}: {e}")
                return False

        # ── Bootstrap: herramientas base ──
        ok &= run_critical("apt update", "apt", "update", sudo=True)
        ok &= run_critical("apt install base",
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
            ok &= run_critical("butterrepo key", "bash", "-c",
                "set -o pipefail && "
                "install -d -m 0755 /usr/share/keyrings && "
                "curl -fsSL https://apt.justaguy.dev/key.asc | "
                "gpg --dearmor --yes -o /usr/share/keyrings/butterrepo.gpg",
                sudo=True)
            ok &= run_critical("butterrepo repo", "bash", "-c",
                'echo "deb [arch=amd64 signed-by=/usr/share/keyrings/butterrepo.gpg] '
                'https://apt.justaguy.dev stable main" | '
                f"tee {butterrepo_list}",
                sudo=True)

        # XanMod (kernel)
        if not os.path.exists("/etc/apt/sources.list.d/xanmod-release.list"):
            ok &= run_critical("xanmod key", "bash", "-c",
                "set -o pipefail && "
                "wget -qO- https://dl.xanmod.org/archive.key | "
                "gpg --dearmor -vo /etc/apt/keyrings/xanmod-archive-keyring.gpg",
                sudo=True)
            ok &= run_critical("xanmod repo", "bash", "-c",
                f'echo "deb [signed-by=/etc/apt/keyrings/xanmod-archive-keyring.gpg] '
                f'https://deb.xanmod.org {codename} main non-free" | '
                "tee /etc/apt/sources.list.d/xanmod-release.list",
                sudo=True)

        # Floorp
        if not os.path.exists("/etc/apt/sources.list.d/Floorp.list"):
            ok &= run_critical("floorp key", "bash", "-c",
                "set -o pipefail && "
                "install -d -m 0755 /usr/share/keyrings && "
                "curl -fsSL https://ppa.floorp.app/KEY.gpg | "
                "gpg --dearmor -o /usr/share/keyrings/Floorp.gpg",
                sudo=True)
            ok &= run_critical("floorp repo", "curl", "-sS", "--compressed",
                "-o", "/etc/apt/sources.list.d/Floorp.list",
                "https://ppa.floorp.app/Floorp.list",
                sudo=True)

        # ── Repositorio oficial Noctalia (Ubuntu 26.04 resolute) ──
        # Documentacion: https://docs.noctalia.dev/noctalia/getting-started/installation/
        # Provee: noctalia, umbriel y xdg-desktop-portal-umbriel
        noctalia_key_deb = "/tmp/noctalia-archive-keyring.deb"
        if not os.path.exists(noctalia_key_deb):
            key_ok = run_nonfatal("install noctalia key",
                "bash", "-c",
                "set -euo pipefail; "
                "wget -q https://pkg.noctalia.dev/deb/nickh-archive-keyring.deb "
                f"-O {noctalia_key_deb} && "
                f"apt install -y --allow-downgrades {noctalia_key_deb}",
                sudo=True)
            if not key_ok:
                log("WARN noctalia key: no se pudo instalar; nala update puede "
                    "mostrar advertencias de firma pero continua")
            try:
                os.remove(noctalia_key_deb)
            except OSError:
                pass
        noctalia_list = "/etc/apt/sources.list.d/noctalia-resolute.sources"
        if not os.path.exists(noctalia_list):
            ok &= run_critical("add noctalia repo", "bash", "-c",
                "set -euo pipefail; "
                "wget -q https://pkg.noctalia.dev/deb/noctalia-resolute.sources "
                "-O /etc/apt/sources.list.d/noctalia-resolute.sources",
                sudo=True)

        # ── Actualizar paquetes (absorbe todos los repos) ──
        # nala update puede fallar transientemente. Reintenta una vez; si sigue
        # fallando, solo WARN para no bloquear todo el paso.
        nala_ok = run_critical("nala update", "nala", "update", sudo=True)
        if not nala_ok:
            import time as _time
            _time.sleep(2)
            nala_ok = run_critical("nala update (reintento)", "nala", "update", sudo=True)
        if not nala_ok:
            log("WARN nala update falló; continuando sin actualizar índice")

        # nala upgrade: one-shot con marker file. Evita re-upgradear en cada re-run.
        upgrade_marker = "/var/lib/v0x3l/.upgraded"
        if not os.path.exists(upgrade_marker):
            ok &= run_critical("nala upgrade", "nala", "upgrade", "-y", sudo=True)
            os.makedirs(os.path.dirname(upgrade_marker), exist_ok=True)
            open(upgrade_marker, "w").close()

        # ── Grupos ──
        user = TARGET_USER
        if user:
            ok &= run_critical("add groups",
                "usermod", "-aG", "video,render,audio,plugdev,netdev", user,
                sudo=True)

        # ── Timezone ──
        ok &= run_critical("timezone",
            "timedatectl", "set-timezone", "America/Mazatlan", sudo=True)

        # ── Locale ──
        target_locale = "es_MX.UTF-8"
        la = subprocess.run(["locale", "-a"], capture_output=True, text=True).stdout.lower()
        have = any("es_mx" in tok and "utf" in tok for tok in la.split())
        if not have:
            ok &= run_critical("locale-gen", "bash", "-c",
                f"sed -i 's/^# *{target_locale} UTF-8/{target_locale} UTF-8/' "
                f"/etc/locale.gen; "
                f"grep -q '^{target_locale} UTF-8' /etc/locale.gen || "
                f"echo '{target_locale} UTF-8' >> /etc/locale.gen; "
                f"locale-gen",
                sudo=True)
        ok &= run_critical("update-locale",
            "update-locale", f"LANG={target_locale}", "LANGUAGE=es_MX:es",
            sudo=True)

        # ---- Verificaciones finales ----
        # Verificar que los repos clave están presentes
        for repo_file in [butterrepo_list, "/etc/apt/sources.list.d/xanmod-release.list",
                          noctalia_list]:
            if not os.path.exists(repo_file):
                log(f"WARN repo faltante: {repo_file}")

        # Verificar herramientas base instaladas
        for tool in ["nala", "git", "curl", "wget", "zsh"]:
            if not self._which(tool):
                log(f"WARN herramienta base no encontrada: {tool}")

        return ok

    def _which(self, cmd: str) -> bool:
        """Verifica si un comando existe en PATH."""
        try:
            subprocess.run(["which", cmd], capture_output=True, check=True)
            return True
        except Exception:
            return False