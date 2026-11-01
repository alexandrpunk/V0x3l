# Step 4: Apariencia (cursores, iconos, temas GTK, Plymouth, GRUB)
# Usa assets locales: NO clona de GitHub, NO pide credenciales.

import configparser
import os
import subprocess
import shutil
from v0x3l.steps.base import BaseStep
from v0x3l.config import (
    CURSOR_THEME_NAME, CURSOR_THEME_SRC,
    ICON_THEME_NAME, ICON_THEME_SRC,
    PLYMOUTH_THEME_NAME, PLYMOUTH_THEME_SRC,
    GRUB_THEME_NAME, GRUB_THEME_SRC,
    JUNO_THEME_NAME, JUNO_THEME_SRC,
    TARGET_USER, TARGET_HOME,
)
from v0x3l.shell import log


def gtk_settings_ini(include_gtk3: bool) -> str:
    """Contenido de ~/.config/gtk-3.0|gtk-4.0/settings.ini.

    Activa los temas instalados (Juno GTK, Pure icons, cursores Catppuccin);
    los nombres salen de config (.env) para no divergir de lo instalado.
    """
    ini = (
        "[Settings]\n"
        f"gtk-theme-name={JUNO_THEME_NAME}\n"
        f"gtk-icon-theme-name={ICON_THEME_NAME}\n"
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

def merge_gtk_settings(path: str, content: str) -> bool:
    """Escribe/actualiza settings.ini sin pisar claves ajenas del usuario."""
    parser = configparser.ConfigParser()
    parser.optionxform = str
    try:
        if os.path.exists(path):
            parser.read(path)
        if not parser.has_section("Settings"):
            parser.add_section("Settings")
        for line in content.splitlines():
            if "=" in line and not line.lstrip().startswith("["):
                key, value = line.split("=", 1)
                parser.set("Settings", key.strip(), value.strip())
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            parser.write(f)
        return True
    except Exception as e:
        log(f"WARN paso 4: GTK settings {path}: {type(e).__name__}: {e}")
        return False


def copy_theme_tree(src_dir: str, dest_dir: str) -> None:
    """Copia recursiva preservando symlinks (los temas de iconos los usan)."""
    os.makedirs(dest_dir, exist_ok=True)
    for item in os.listdir(src_dir):
        s = os.path.join(src_dir, item)
        d = os.path.join(dest_dir, item)
        if os.path.islink(s):
            shutil.copy2(s, d, follow_symlinks=False)
        elif os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True, symlinks=True)
        else:
            shutil.copy2(s, d)


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
                copy_theme_tree(src_dir, dest_dir)
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

        # ── Icon theme Pure (asset local vendorizado; src/Pure*) ──
        # El upstream instala copiando src/Pure* a /usr/share/icons. Los temas
        # son autocontenidos (symlinks internos) y se copian tal cual.
        icon_variants = []
        if os.path.isdir(ICON_THEME_SRC):
            icon_variants = sorted(
                d for d in os.listdir(ICON_THEME_SRC)
                if d.startswith("Pure")
                and os.path.isdir(os.path.join(ICON_THEME_SRC, d)))
        if not icon_variants:
            _fail("icon theme Pure", f"no hay variantes en {ICON_THEME_SRC}")
        for variant in icon_variants:
            icon_dest = f"/usr/share/icons/{variant}"
            if not os.path.exists(icon_dest):
                copy_theme_local(os.path.join(ICON_THEME_SRC, variant),
                                 icon_dest, f"Pure icons {variant}")
        if shutil.which("gtk-update-icon-cache"):
            for variant in icon_variants:
                icon_dest = f"/usr/share/icons/{variant}"
                if os.path.isdir(icon_dest):
                    _run(f"icon cache {variant}",
                         "gtk-update-icon-cache", "-f", icon_dest, sudo=True)

        # ── Juno GTK theme (asset local vendorizado en assets/themes/juno-gtk) ──
        juno_dest = f"/usr/share/themes/{JUNO_THEME_NAME}"
        if not os.path.exists(juno_dest):
            copy_theme_local(JUNO_THEME_SRC, juno_dest, "Juno GTK theme")

        # ── Plymouth theme (asset local; requiere el paquete plymouth) ──
        # Plymouth resuelve el tema como <dir>/<nombre>.plymouth, y el asset ya
        # se llama PLYMOUTH_THEME_NAME con ImageDir apuntando a esa ruta.
        plymouth_dest = f"/usr/share/plymouth/themes/{PLYMOUTH_THEME_NAME}"
        if not os.path.exists(plymouth_dest):
            if copy_theme_local(PLYMOUTH_THEME_SRC, plymouth_dest, "Plymouth theme v0x3l"):
                if shutil.which("plymouth-set-default-theme"):
                    _run("plymouth set default",
                         "plymouth-set-default-theme", PLYMOUTH_THEME_NAME, "-R", sudo=True)
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

        # ── Activar temas GTK para el usuario ──
        # 1) settings.ini: fallback para apps GTK sin portal (se mezcla con lo
        #    existente para no pisar configuracion ajena).
        # 2) dconf/gsettings: el portal de settings y GTK en Wayland consultan
        #    org.gnome.desktop.interface; sin esto el tema no queda por defecto.
        if TARGET_USER and TARGET_HOME:
            for rel, content in (
                (".config/gtk-3.0/settings.ini", gtk_settings_ini(True)),
                (".config/gtk-4.0/settings.ini", gtk_settings_ini(False)),
            ):
                gtk_path = os.path.join(TARGET_HOME, rel)
                if not merge_gtk_settings(gtk_path, content):
                    _fail(f"GTK settings {gtk_path}", "no se pudo escribir")
                    continue
                if os.geteuid() == 0:
                    subprocess.run(["chown", "-R", f"{TARGET_USER}:",
                                    os.path.dirname(gtk_path)], check=False)
                log(f"INFO paso 4: GTK settings activados: {gtk_path}")

            gsettings_bin = shutil.which("gsettings")
            dbus_bin = shutil.which("dbus-run-session")
            if gsettings_bin and dbus_bin:
                for schema, key, value in (
                    ("org.gnome.desktop.interface", "gtk-theme", JUNO_THEME_NAME),
                    ("org.gnome.desktop.interface", "icon-theme", ICON_THEME_NAME),
                    ("org.gnome.desktop.interface", "cursor-theme", CURSOR_THEME_NAME),
                    ("org.gnome.desktop.interface", "color-scheme", "prefer-dark"),
                ):
                    argv = [dbus_bin, "--", gsettings_bin, "set", schema, key, value]
                    if os.geteuid() == 0:
                        argv = ["runuser", "-u", TARGET_USER, "--", "env",
                                f"HOME={TARGET_HOME}", *argv]
                    _run(f"gsettings {key}", *argv)
            else:
                _fail("gsettings", "gsettings/dbus-run-session ausente")

        # ── Resumen ──
        missing = [name for path, name in (
            (f"/usr/share/icons/{CURSOR_THEME_NAME}", "Cursors"),
            (f"/usr/share/icons/{ICON_THEME_NAME}", "Pure icons"),
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