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
    JUNO_THEME_NAME, JUNO_THEME_SRC,
    TARGET_USER, TARGET_HOME,
)
from v0x3l.shell import log


def gtk_settings_ini(include_gtk3: bool) -> str:
    """Contenido de ~/.config/gtk-3.0|gtk-4.0/settings.ini.

    Activa los temas instalados (Juno GTK, Colloid icons, cursores Catppuccin);
    los nombres salen de config (.env) para no divergir de lo instalado.
    """
    ini = (
        "[Settings]\n"
        f"gtk-theme-name={JUNO_THEME_NAME}\n"
        f"gtk-icon-theme-name={COLLOID_THEME_NAME}\n"
        f"gtk-cursor-theme-name={CURSOR_THEME_NAME}\n"
        "gtk-cursor-theme-size=24\n"
        "gtk-font-name=Noto Sans 11\n"
        "gtk-application-prefer-dark-theme=1\n"
    )
    if include_gtk3:
        ini += (
            "gtk-toolbar-style=GTK_TOOLBAR_BOTH_HORIZ\n"
            "gtk-toolbar-icon-size=GTK_ICON_SIZE_LARGE_TOOLBAR\n"
            "gtk-button-images=1\n"
            "gtk-menu-images=1\n"
            "gtk-enable-event-sounds=1\n"
            "gtk-enable-input-feedback-sounds=0\n"
            "gtk-xft-antialias=1\n"
            "gtk-xft-hinting=1\n"
            "gtk-xft-hintstyle=hintslight\n"
            "gtk-xft-rgba=rgb\n"
        )
    return ini


class AppearanceStep(BaseStep):
    number = 4
    title = "Apariencia"
    category = "theming"

    def run(self) -> bool:
        """Paso cosmetico (Apariencia). Nunca detiene la instalacion.

        Los temas no son criticos para que el sistema arranque ni para los pasos
        posteriores. StepRunner.run_all aborta la instalacion entera cuando un
        paso devuelve False, asi que aqui no se propaga ningun fallo: cada uno se
        registra en el log y el paso termina en OK.
        """
        failures: list[str] = []

        def _fail(desc: str, detail: str = "") -> None:
            log(f"WARN paso 4: {desc}{': ' + detail if detail else ''}")
            failures.append(desc)

        def _run(desc: str, *args, **kwargs) -> bool:
            """Ejecuta un comando, registra el fallo y nunca aborta el paso."""
            try:
                if self.runner.ui.run_cmd(desc, *args, **kwargs):
                    return True
            except Exception as e:
                _fail(desc, f"excepcion {type(e).__name__}: {e}")
                return False
            _fail(desc, "comando fallo")
            return False

        def copy_theme_local(src_dir: str, dest_dir: str, desc: str) -> bool:
            """Copia tema local a /usr/share/... sin git, sin credenciales."""
            if not os.path.isdir(src_dir):
                _fail(desc, f"origen no existe: {src_dir}")
                return False
            try:
                os.makedirs(dest_dir, exist_ok=True)
                for item in os.listdir(src_dir):
                    s = os.path.join(src_dir, item)
                    d = os.path.join(dest_dir, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s, d)
                log(f"INFO paso 4: {desc}: copiado {src_dir} -> {dest_dir}")
                return True
            except Exception as e:
                _fail(desc, f"{type(e).__name__}: {e}")
                return False

        # ── Catppuccin cursors (asset local zip) ──
        if not os.path.exists(f"/usr/share/icons/{CURSOR_THEME_NAME}"):
            if not os.path.isfile(CURSOR_THEME_SRC):
                _fail(f"cursores {CURSOR_THEME_NAME}", "no estan en assets")
            elif not shutil.which("unzip"):
                _fail("extract cursors", "unzip no instalado")
            else:
                import tempfile
                tmpdir = tempfile.mkdtemp()
                try:
                    shutil.copy(CURSOR_THEME_SRC, f"{tmpdir}/cursors.zip")
                    _run("extract cursors", "unzip", "-q",
                         f"{tmpdir}/cursors.zip", "-d", "/usr/share/icons/",
                         sudo=True)
                finally:
                    shutil.rmtree(tmpdir, ignore_errors=True)

        # ── Colloid icons (asset local) ──
        if not os.path.exists(f"/usr/share/icons/{COLLOID_THEME_NAME}") and os.path.isdir(COLLOID_DIR):
            _run("install Colloid",
                 "bash", f"{COLLOID_DIR}/install.sh", "-b", "-s",
                 "catppuccin", "-t", "green", sudo=True)

        # ── Juno GTK theme (asset local vendorizado en assets/themes/juno-gtk) ──
        juno_dest = f"/usr/share/themes/{JUNO_THEME_NAME}"
        if not os.path.exists(juno_dest):
            copy_theme_local(JUNO_THEME_SRC, juno_dest, "Juno GTK theme")

        # ── Plymouth theme (asset local; requiere el paquete plymouth) ──
        plymouth_dest = "/usr/share/plymouth/themes/v0x3l"
        if not os.path.exists(plymouth_dest):
            if copy_theme_local(PLYMOUTH_THEME_SRC, plymouth_dest, "Plymouth theme v0x3l"):
                if shutil.which("plymouth-set-default-theme"):
                    _run("plymouth set default",
                         "plymouth-set-default-theme", "v0x3l", "-R", sudo=True)
                else:
                    _fail("plymouth set default",
                          "plymouth no instalado (plymouth-set-default-theme ausente)")

        # ── GRUB Vimix theme (asset local grub-vimix) ──
        grub_dest = "/usr/share/grub/themes/vimix"
        if not os.path.exists(grub_dest):
            if copy_theme_local(GRUB_THEME_SRC, grub_dest, "GRUB Vimix theme"):
                grub_conf = "/etc/default/grub"
                if os.path.exists(grub_conf):
                    _run("grub theme config", "sed", "-i",
                         's/^#*GRUB_THEME=.*/GRUB_THEME="\\/usr\\/share\\/grub\\/themes\\/vimix\\/theme.txt"/',
                         grub_conf, sudo=True)
                    _run("grub resolution", "sed", "-i",
                         's/^#*GRUB_GFXMODE=.*/GRUB_GFXMODE=1920x1080/',
                         grub_conf, sudo=True)
                    if shutil.which("update-grub"):
                        _run("update-grub", "update-grub", sudo=True)
                    else:
                        _fail("update-grub", "update-grub no instalado")

        # ── Activar temas GTK para el usuario (settings.ini) ──
        # Los temas se copian a /usr/share; sin settings.ini las apps GTK siguen
        # usando Adwaita. Los valores salen de config (.env) para no divergir de
        # lo realmente instalado.
        if TARGET_USER and TARGET_HOME:
            for rel, content in (
                (".config/gtk-3.0/settings.ini", gtk_settings_ini(True)),
                (".config/gtk-4.0/settings.ini", gtk_settings_ini(False)),
            ):
                gtk_path = os.path.join(TARGET_HOME, rel)
                if os.path.exists(gtk_path):
                    continue
                try:
                    os.makedirs(os.path.dirname(gtk_path), exist_ok=True)
                    with open(gtk_path, "w") as f:
                        f.write(content)
                    if os.geteuid() == 0:
                        subprocess.run(["chown", "-R", f"{TARGET_USER}:",
                                        os.path.dirname(gtk_path)], check=False)
                    log(f"INFO paso 4: GTK settings activados: {gtk_path}")
                except Exception as e:
                    _fail(f"GTK settings {gtk_path}", f"{type(e).__name__}: {e}")

        # ── Resumen ──
        missing = [name for path, name in (
            (f"/usr/share/icons/{CURSOR_THEME_NAME}", "Cursors"),
            (f"/usr/share/icons/{COLLOID_THEME_NAME}", "Colloid icons"),
            (f"/usr/share/themes/{JUNO_THEME_NAME}", "Juno GTK"),
            (plymouth_dest, "Plymouth v0x3l"),
            (grub_dest, "GRUB Vimix"),
        ) if not os.path.exists(path)]
        if missing:
            log(f"WARN paso 4: temas no presentes al final: {', '.join(missing)}")
        if failures:
            log(f"WARN paso 4: no aplicado: {', '.join(failures)}")
        else:
            log("INFO paso 4: todos los temas aplicados")
        return True