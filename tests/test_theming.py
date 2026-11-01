import os
import tempfile
import tomllib
import unittest
from pathlib import Path

from v0x3l import config as C
from v0x3l.steps import system as S
from v0x3l.steps.theming import set_grub_option

# /etc/default/grub tipico de Ubuntu Server: NO tiene GRUB_THEME.
UBUNTU_GRUB = """GRUB_DEFAULT=0
GRUB_TIMEOUT_STYLE=hidden
GRUB_TIMEOUT=0
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"
GRUB_CMDLINE_LINUX=""
#GRUB_GFXMODE=640x480
"""


class GrubOptionTests(unittest.TestCase):
    def _write(self, content: str) -> str:
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "grub")
        Path(path).write_text(content)
        return path

    def test_anade_grub_theme_cuando_no_existe(self):
        path = self._write(UBUNTU_GRUB)
        self.assertTrue(set_grub_option(
            path, "GRUB_THEME", '"/usr/share/grub/themes/vimix/theme.txt"'))
        content = Path(path).read_text()
        self.assertIn(
            'GRUB_THEME="/usr/share/grub/themes/vimix/theme.txt"', content)

    def test_reemplaza_valor_comentado(self):
        path = self._write(UBUNTU_GRUB)
        set_grub_option(path, "GRUB_GFXMODE", "1920x1080")
        content = Path(path).read_text()
        self.assertIn("GRUB_GFXMODE=1920x1080", content)
        self.assertNotIn("640x480", content)

    def test_reemplaza_valor_activo_sin_duplicar(self):
        path = self._write(UBUNTU_GRUB + 'GRUB_THEME="/viejo/theme.txt"\n')
        set_grub_option(path, "GRUB_THEME", '"/nuevo/theme.txt"')
        content = Path(path).read_text()
        self.assertEqual(content.count("GRUB_THEME="), 1)
        self.assertIn('GRUB_THEME="/nuevo/theme.txt"', content)

    def test_idempotente(self):
        path = self._write(UBUNTU_GRUB)
        for _ in range(3):
            set_grub_option(path, "GRUB_THEME", '"/x/theme.txt"')
        self.assertEqual(Path(path).read_text().count("GRUB_THEME="), 1)

    def test_archivo_inexistente_no_lanza(self):
        self.assertFalse(set_grub_option("/no/existe/grub", "GRUB_THEME", "x"))


class UmbrielCursorTests(unittest.TestCase):
    def test_config_sembrado_fija_el_cursor_del_compositor(self):
        """En Wayland el cursor lo fija Umbriel, no GTK: sin [input.cursor]
        el tema instalado nunca se aplica."""
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "config.toml"
            self.assertTrue(S.seed_umbriel_config(
                str(dest), packaged="/nonexistent",
                template=S.UMBRIEL_CONFIG_TEMPLATE))
            cfg = tomllib.loads(dest.read_text())

        self.assertEqual(cfg["input"]["cursor"]["theme"], C.CURSOR_THEME_NAME)
        self.assertEqual(cfg["input"]["cursor"]["size"], 24)
        self.assertEqual(cfg["layout"]["mode"], "stacking")

    def test_apply_prefs_anade_cursor_sin_perder_lo_demas(self):
        """Un config ya existente recibe [input.cursor] sin descartar el resto."""
        existing = ('[layout]\nmode = "stacking"\n\n'
                    '[keybinds]\n"Mod+Q" = "window-close"\n')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(existing)
            self.assertTrue(S.apply_umbriel_prefs(str(path)))
            cfg = tomllib.loads(path.read_text())

        self.assertEqual(cfg["input"]["cursor"]["theme"], C.CURSOR_THEME_NAME)
        self.assertEqual(cfg["layout"]["mode"], "stacking")
        self.assertEqual(cfg["keybinds"]["Mod+Q"], "window-close")


if __name__ == "__main__":
    unittest.main()