# Step 4: Apariencia (cursores, iconos, temas GTK, Plymouth, GRUB)

import os
import subprocess
import tempfile
import shutil
from v0x3l.steps.base import BaseStep
from v0x3l.config import CURSOR_THEME_NAME, CURSOR_THEME_SRC, COLLOID_THEME_NAME, COLLOID_DIR


class AppearanceStep(BaseStep):
    number = 4
    title = "Apariencia"
    category = "theming"

    def run(self) -> bool:
        ok = True

        # ---- Helpers ----
        def run_critical(desc: str, *args, **kwargs) -> bool:
            try:
                result = self.runner.ui.run_cmd(desc, *args, **kwargs)
                if not result:
                    print(f"ERROR {desc}: comando fallo (critico)")
                return result
            except Exception as e:
                print(f"ERROR {desc}: excepcion {type(e).__name__}: {e}")
                return False

        def run_nonfatal(desc: str, *args, **kwargs) -> bool:
            try:
                result = self.runner.ui.run_cmd(desc, *args, **kwargs)
                if not result:
                    print(f"WARN {desc}: comando fallo (no fatal)")
                return result
            except Exception as e:
                print(f"WARN {desc}: excepcion {type(e).__name__}: {e}")
                return False

        def write_file_if_missing(path: str, content: str, mode: int = 0o644) -> bool:
            try:
                if not os.path.exists(path):
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, "w") as f:
                        f.write(content)
                    os.chmod(path, mode)
                    print(f"INFO escrito: {path}")
                    return True
                return False
            except Exception as e:
                print(f"ERROR escribiendo {path}: {type(e).__name__}: {e}")
                return False

        # Detectar NVIDIA en runtime via lspci (no depender del env var de
        # step 1, que se pierde si step 4 corre standalone o tras reboot).
        # Mismo filtro que drivers.py: solo lineas VGA/3D/display.
        try:
            _lspci = subprocess.run(["lspci", "-nn"],
                capture_output=True, text=True).stdout.lower()
            _gpu = [l for l in _lspci.splitlines()
                    if any(x in l for x in ("vga", "3d", "display"))]
            has_nvidia = any("nvidia" in l for l in _gpu)
        except Exception:
            has_nvidia = os.environ.get("HAS_NVIDIA_GPU", "0") == "1"

        # ── Catppuccin cursors ──
        if not os.path.exists(f"/usr/share/icons/{CURSOR_THEME_NAME}"):
            if os.path.isfile(CURSOR_THEME_SRC):
                tmpdir = tempfile.mkdtemp()
                shutil.copy(CURSOR_THEME_SRC, f"{tmpdir}/cursors.zip")
                ok &= run_critical("extract cursors",
                    "unzip", "-q", f"{tmpdir}/cursors.zip", "-d", "/usr/share/icons/", sudo=True)
                subprocess.run(["rm", "-rf", tmpdir])
            else:
                print(f"WARN cursores {CURSOR_THEME_NAME} no disponibles")

        # ── Colloid icons ──
        if not os.path.exists(f"/usr/share/icons/{COLLOID_THEME_NAME}") and os.path.isdir(COLLOID_DIR):
            ok &= run_critical("install Colloid",
                "bash", f"{COLLOID_DIR}/install.sh", "-b", "-s",
                "catppuccin", "-t", "green", sudo=True)

        # ── Juno (GTK theme, github.com/EliverLara/Juno) ──
        if not os.path.exists("/usr/share/themes/Juno"):
            ok &= run_critical("install Juno GTK theme", "bash", "-c",
                "git clone --depth 1 https://github.com/EliverLara/Juno.git "
                "/usr/share/themes/Juno && "
                "cd /usr/share/themes/Juno && "
                "bash install.sh",
                sudo=True)

        # ── Plymouth (boot splash) ──
        if not os.path.exists("/usr/share/plymouth/themes/vimix"):
            ok &= run_critical("install Plymouth theme", "bash", "-c",
                "git clone --depth 1 https://github.com/vinceliuice/vimix-plymouth.git "
                "/tmp/vimix-plymouth && "
                "cd /tmp/vimix-plymouth && "
                "sudo ./install.sh",
                sudo=True)

        # ── GRUB Vimix theme ──
        if not os.path.exists("/usr/share/grub/themes/vimix"):
            ok &= run_critical("install GRUB theme", "bash", "-c",
                "git clone --depth 1 https://github.com/vinceliuice/vimix-grub2-theme.git "
                "/tmp/vimix-grub && "
                "cd /tmp/vimix-grub && "
                "sudo ./install.sh",
                sudo=True)

        # ---- Verificaciones finales ----
        # Verificar que los temas clave están presentes
        for theme_path in [
            f"/usr/share/icons/{CURSOR_THEME_NAME}",
            f"/usr/share/icons/{COLLOID_THEME_NAME}",
            "/usr/share/themes/Juno",
            "/usr/share/plymouth/themes/vimix",
            "/usr/share/grub/themes/vimix"
        ]:
            if not os.path.exists(theme_path):
                print(f"WARN tema faltante: {theme_path}")

        return ok