import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from v0x3l.steps import system as S


class UmbrielPrefsTests(unittest.TestCase):
    """seed_umbriel_config debe dejar el config valido para Umbriel 5.x.

    Regresion: la barra de titulo venia desactivada (default mode = "off") y
    el cheatsheet se abria en cada arranque.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.src = self.root / "packaged.toml"
        self.src.write_text(
            "[layout]\nmode = \"scrolling\"\n\n"
            "[general]\nshow_cheatsheet = true\n\n"
            "[keybinds]\n\"Mod+Q\" = \"window-close\"\n")

    def seed(self):
        dest = self.root / "out.toml"
        self.assertTrue(S.seed_umbriel_config(
            str(dest), packaged=str(self.src), template=str(self.src)))
        return dest.read_text()

    def test_title_bar_and_keys_are_valid_toml(self):
        text = self.seed()
        data = tomllib.loads(text)

        bar = data["appearance"]["title_bar"]
        self.assertEqual(bar["mode"], "forced")
        self.assertEqual(bar["button_position"], "left")
        self.assertEqual(bar["buttons"], ["maximize", "minimize", "close"])
        self.assertEqual(bar["button_glyph"], "hover")
        self.assertTrue(data["appearance"]["prefer_no_csd"])

    def test_cheatsheet_disabled_and_bound_to_mod_f2(self):
        data = tomllib.loads(self.seed())
        self.assertFalse(data["general"]["show_cheatsheet"])
        self.assertEqual(data["keybinds"]["Mod+F2"],
                         {"action": "cheatsheet-toggle", "repeat": False})

    def test_alt_tab_opens_noctalia_switcher(self):
        data = tomllib.loads(self.seed())
        bind = {"action": "spawn noctalia msg window-switcher hold current",
                "repeat": False}
        self.assertEqual(data["keybinds"]["Alt+Tab"], bind)
        self.assertEqual(data["keybinds"]["Alt+Shift+Tab"], bind)
        # El set empaquetado no se pierde.
        self.assertEqual(data["keybinds"]["Mod+Q"], "window-close")
        self.assertEqual(data["layout"]["mode"], "stacking")

    def test_real_template_seeds_valid_toml(self):
        template = str(Path(S.UMBRIEL_CONFIG_TEMPLATE))
        dest = self.root / "from-template.toml"
        self.assertTrue(S.seed_umbriel_config(
            str(dest), packaged=str(self.root / "missing.toml"),
            template=template))
        data = tomllib.loads(dest.read_text())
        self.assertEqual(data["appearance"]["title_bar"]["mode"], "forced")


class DefaultAppsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)
        self.path = self.home / ".config" / "mimeapps.list"

    def write_existing(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(
            "[Added Associations]\n"
            "text/plain=old-editor.desktop;\n"
            "\n"
            "[Default Applications]\n"
            "text/plain=old-editor.desktop;\n")

    def test_sets_all_requested_defaults(self):
        self.write_existing()
        self.assertTrue(S.apply_default_apps(str(self.home)))
        text = self.path.read_text()
        self.assertIn("x-scheme-handler/http=floorp.desktop;", text)
        self.assertIn("text/html=floorp.desktop;", text)
        self.assertIn("text/plain=mousepad.desktop;", text)
        self.assertIn("image/png=viewnior.desktop;", text)
        self.assertIn("application/pdf=qpdfview.desktop;", text)
        self.assertIn("video/mp4=io.github.diegopvlk.Cine.desktop;", text)
        # Las secciones ajenas se conservan.
        self.assertIn("[Added Associations]", text)
        self.assertIn("text/plain=old-editor.desktop;", text)

    def test_idempotent_no_duplicate_keys(self):
        self.assertTrue(S.apply_default_apps(str(self.home)))
        self.assertTrue(S.apply_default_apps(str(self.home)))
        text = self.path.read_text()
        self.assertEqual(text.count("text/plain="), 1)
        self.assertEqual(text.count("[Default Applications]"), 1)


class ThunarTerminalTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)
        self.path = self.home / ".config" / "xfce4" / "helpers.rc"

    def test_sets_kitty_and_keeps_other_keys(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("WebBrowser=floorp\nTerminalEmulator=xfce4-terminal\n")
        self.assertTrue(S.configure_thunar_terminal(str(self.home)))
        lines = self.path.read_text().splitlines()
        self.assertIn("TerminalEmulator=kitty", lines)
        self.assertIn("WebBrowser=floorp", lines)
        helper = (self.home / ".local" / "share" / "xfce4" / "helpers"
                  / "kitty.desktop")
        # .desktop usa [Desktop Entry] (con espacio): no es TOML parseable.
        helper_text = helper.read_text()
        self.assertTrue(helper_text.startswith("[Desktop Entry]\n"))
        self.assertIn("Type=X-XFCE-Helper", helper_text)
        self.assertIn("X-XFCE-Category=TerminalEmulator", helper_text)
        self.assertIn(
            f"X-XFCE-Binaries={self.home}/.local/kitty.app/bin/kitty;",
            helper_text)
        # exo antepone [Default]: una cabecera propia romperia el parseo.
        self.assertNotIn("[Default]", lines)
        self.assertEqual(sum(l.startswith("TerminalEmulator=") for l in lines), 1)

    def test_creates_file_when_missing(self):
        self.assertTrue(S.configure_thunar_terminal(str(self.home)))
        self.assertEqual(self.path.read_text(), "TerminalEmulator=kitty\n")


class NoctaliaSwitcherTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)

    def test_writes_workspace_scoped_switcher_fragment(self):
        self.assertTrue(S.apply_noctalia_switcher(str(self.home)))
        path = (self.home / ".config" / "noctalia"
                / S.NOCTALIA_SHELL_CFG)
        data = tomllib.loads(path.read_text())
        self.assertEqual(data["shell"]["window_switcher"], {
            "current_workspace_only": True,
            "show_all_outputs": False,
            "mru": True,
        })
        self.assertFalse((path.parent / "settings.toml").exists())


if __name__ == "__main__":
    unittest.main()