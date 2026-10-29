# Step 4: Apariencia (cursores, iconos, temas GTK, Plymouth, GRUB)
# Usa assets locales: NO clona de GitHub, NO pide credenciales.

import os
import subprocess
import shutil
from v0x3l.steps.base import BaseStep
from v0x3l.config import (
    CURSOR_THEME_NAME, CURSOR_THEME_SRC,
    COLLOID_THEME_NAME, COLLOID_DIR,
    PLYMOUTH_THEME_NAME, PLYMOUTH_THEME_SRC,
    GRUB_THEME_NAME, GRUB_THEME_SRC,
)


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

        def copy_theme_local(src_dir: str, dest_dir: str, desc: str) -> bool:
            """Copia tema local a /usr/share/... sin git, sin credenciales."""
            if not os.path.isdir(src_dir):
                print(f"WARN {desc}: origen no existe: {src_dir}")
                return False
            try:
                os.makedirs(dest_dir, exist_ok=True)
                # Copiar recursivamente preservando estructura
                for item in os.listdir(src_dir):
                    s = os.path.join(src_dir, item)
                    d = os.path.join(dest_dir, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s, d)
                print(f"INFO {desc}: copiado desde {src_dir} → {dest_dir}")
                return True
            except Exception as e:
                print(f"ERROR {desc}: {type(e).__name__}: {e}")
                return False

        # Detectar NVIDIA en runtime via lspci
        try:
            _lspci = subprocess.run(["lspci", "-nn"],
                capture_output=True, text=True).stdout.lower()
            _gpu = [l for l in _lspci.splitlines()
                    if any(x in l for x in ("vga", "3d", "display"))]
            has_nvidia = any("nvidia" in l for l in _gpu)
        except Exception:
            has_nvidia = os.environ.get("HAS_NVIDIA_GPU", "0") == "1"

        # ── Catppuccin cursors (desde asset local zip) ──
        if not os.path.exists(f"/usr/share/icons/{CURSOR_THEME_NAME}"):
            if os.path.isfile(CURSOR_THEME_SRC):
                import tempfile
                tmpdir = tempfile.mkdtemp()
                try:
                    shutil.copy(CURSOR_THEME_SRC, f"{tmpdir}/cursors.zip")
                    ok &= run_critical("extract cursors",
                        "unzip", "-q", f"{tmpdir}/cursors.zip", "-d", "/usr/share/icons/", sudo=True)
                finally:
                    shutil.rmtree(tmpdir, ignore_errors=True)
            else:
                print(f"WARN cursores {CURSOR_THEME_NAME} no disponibles en assets")

        # ── Colloid icons (desde asset local) ──
        if not os.path.exists(f"/usr/share/icons/{COLLOID_THEME_NAME}") and os.path.isdir(COLLOID_DIR):
            ok &= run_critical("install Colloid",
                "bash", f"{COLLOID_DIR}/install.sh", "-b", "-s",
                "catppuccin", "-t", "green", sudo=True)

        # ── Juno GTK theme (asset local si existe, sino fallback) ──
        juno_local = "/home/alexandr/proyects/VoidForge/assets/themes/juno-gtk"
        if not os.path.exists("/usr/share/themes/Juno"):
            if os.path.isdir(juno_local):
                ok &= copy_theme_local(juno_local, "/usr/share/themes/Juno", "Juno GTK theme")
            else:
                # Fallback: clona solo si no hay asset local (último recurso)
                ok &= run_nonfatal("install Juno GTK theme (fallback git)",
                    "bash", "-c",
                    "git clone --depth 1 https://github.com/EliverLara/Juno.git "
                    "/usr/share/themes/Juno && "
                    "cd /usr/share/themes/Juno && "
                    "bash install.sh",
                    sudo=True)

        # ── Plymouth theme (asset local v0x3l-boot-theme) ──
        plymouth_src = "/home/alexandr/proyects/VoidForge/assets/themes/v0x3l-boot-theme"
        plymouth_dest = "/usr/share/plymouth/themes/v0x3l"
        if not os.path.exists(plymouth_dest):
            if os.path.isdir(plymouth_src):
                ok &= copy_theme_local(plymouth_src, plymouth_dest, "Plymouth theme v0x3l")
                # Registrar y configurar
                ok &= run_critical("plymouth set default",
                    "plymouth-set-default-theme", "v0x3l", "-R", sudo=True)
            else:
                print(f"WARN Plymouth theme origen no existe: {plymouth_src}")

        # ── GRUB Vimix theme (asset local grub-vimix) ──
        grub_src = "/home/alexandr/proyects/VoidForge/assets/themes/grub-vimix"
        grub_dest = "/usr/share/grub/themes/vimix"
        if not os.path.exists(grub_dest):
            if os.path.isdir(grub_src):
                ok &= copy_theme_local(grub_src, grub_dest, "GRUB Vimix theme")
                # Configurar GRUB para usar el tema
                grub_conf = "/etc/default/grub"
                if os.path.exists(grub_conf):
                    ok &= run_nonfatal("grub theme config",
                        "sed", "-i",
                    's/^#*GRUB_THEME=.*/GRUB_THEME="\\/usr\\/share\\/grub\\/themes\\/vimix\\/theme.txt"/',
                        grub_conf, sudo=True)
                    ok &= run_nonfatal("grub resolution",
                        "sed", "-i",
                        's/^#*GRUB_GFXMODE=.*/GRUB_GFXMODE=1920x1080/',
                        grub_conf, sudo=True)
                    ok &= run_critical("update-grub", "update-grub", sudo=True)
            else:
                print(f"WARN GRUB theme origen no existe: {grub_src}")

        # ── Verificaciones finales ----
        for theme_path, name in [
            (f"/usr/share/icons/{CURSOR_THEME_NAME}", "Cursors"),
            (f"/usr/share/icons/{COLLOID_THEME_NAME}", "Colloid icons"),
            ("/usr/share/themes/Juno", "Juno GTK"),
            (plymouth_dest, "Plymouth v0x3l"),
            (grub_dest, "GRUB Vimix"),
        ]:
            if not os.path.exists(theme_path):
                print(f"WARN tema faltante: {name} ({theme_path})")

        return ok