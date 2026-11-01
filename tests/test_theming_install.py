import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v0x3l.steps import theming as T

UBUNTU_GRUB = """GRUB_DEFAULT=0
GRUB_TIMEOUT_STYLE=hidden
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"
#GRUB_GFXMODE=640x480
"""


class _UI:
    def __init__(self):
        self.calls = []

    def run_cmd(self, desc, *args, **kwargs):
        self.calls.append((desc, args))
        return True


class _Runner:
    def __init__(self):
        self.ui = _UI()
        self.shell = None


class ThemeInstallTests(unittest.TestCase):
    """Ejecuta el paso 4 contra un 'root' falso para verificar Plymouth y GRUB.

    Las rutas del sistema son constantes de modulo (SYSTEM_ICONS, PLYMOUTH_THEMES,
    GRUB_THEMES, GRUB_DEFAULT_CONF) precisamente para poder redirigirlas aqui.
    """

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.grub_conf = self.root / "default-grub"
        self.grub_conf.write_text(UBUNTU_GRUB)

        self._patches = [
            patch.object(T, "SYSTEM_ICONS", str(self.root / "icons")),
            patch.object(T, "SYSTEM_THEMES", str(self.root / "themes")),
            patch.object(T, "PLYMOUTH_THEMES", str(self.root / "plymouth")),
            patch.object(T, "PLYMOUTH_DEFAULT_LINK",
                         str(self.root / "plymouth" / "default.plymouth")),
            patch.object(T, "GRUB_THEMES", str(self.root / "grub-themes")),
            patch.object(T, "GRUB_DEFAULT_CONF", str(self.grub_conf)),
            patch.object(T, "TARGET_USER", "testuser"),
            patch.object(T, "TARGET_HOME", str(self.root / "home")),
            # Evita copiar los 120 MB de iconos y el zip de cursores.
            patch.object(T, "ICON_THEME_SRC", str(self.root / "no-icons")),
            patch.object(T, "CURSOR_THEME_SRC", str(self.root / "no-cursors.zip")),
            patch.object(T, "JUNO_THEME_SRC", str(self.root / "no-juno")),
        ]
        for p in self._patches:
            p.start()
            self.addCleanup(p.stop)

    def _which(self, available):
        real = shutil.which

        def fake(name, *args, **kwargs):
            if name in available:
                return f"/usr/bin/{name}"
            if name in ("plymouth-set-default-theme", "update-grub",
                        "update-initramfs", "gtk-update-icon-cache"):
                return None
            return real(name, *args, **kwargs)

        return patch("shutil.which", side_effect=fake)

    def test_grub_se_copia_y_se_activa_en_default_grub(self):
        runner = _Runner()
        with self._which({"update-grub"}):
            self.assertTrue(T.AppearanceStep(runner).run())

        theme_txt = self.root / "grub-themes" / "vimix" / "theme.txt"
        self.assertTrue(theme_txt.is_file(), "no se copio el tema de GRUB")

        conf = self.grub_conf.read_text()
        self.assertIn(f'GRUB_THEME="{theme_txt}"', conf)
        self.assertIn("GRUB_GFXMODE=1920x1080", conf)
        self.assertNotIn("640x480", conf)

        descs = [c[0] for c in runner.ui.calls]
        self.assertIn("update-grub", descs)

    def test_plymouth_fallback_cuando_falta_plymouth_set_default_theme(self):
        runner = _Runner()
        with self._which({"update-initramfs"}):
            self.assertTrue(T.AppearanceStep(runner).run())

        theme_file = (self.root / "plymouth" / T.PLYMOUTH_THEME_NAME
                      / f"{T.PLYMOUTH_THEME_NAME}.plymouth")
        self.assertTrue(theme_file.is_file(), "no se copio el tema de Plymouth")

        calls = {c[0]: c[1] for c in runner.ui.calls}
        self.assertIn("plymouth default symlink", calls)
        self.assertEqual(calls["plymouth default symlink"][2], str(theme_file))
        self.assertIn("update-initramfs", calls)

    def test_plymouth_usa_plymouth_set_default_theme_si_existe(self):
        runner = _Runner()
        with self._which({"plymouth-set-default-theme", "update-initramfs"}):
            self.assertTrue(T.AppearanceStep(runner).run())

        calls = {c[0]: c[1] for c in runner.ui.calls}
        self.assertIn("plymouth set default", calls)
        self.assertEqual(
            calls["plymouth set default"],
            ("plymouth-set-default-theme", T.PLYMOUTH_THEME_NAME, "-R"))
        self.assertNotIn("plymouth default symlink", calls)


if __name__ == "__main__":
    unittest.main()