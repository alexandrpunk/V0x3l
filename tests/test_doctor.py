import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v0x3l.config import CURSOR_THEME_NAME
from v0x3l.doctor import (
    FAIL, OK, WARN, Check, format_report, run_checks, summarize,
)

CONFIG_OK = """[layout]
mode = "stacking"

[general]
autostart = ["noctalia"]

[keybinds]
"Mod+Q" = "window-close"

[input.cursor]
theme = "%s"
size = 24
""" % CURSOR_THEME_NAME


class ReportTests(unittest.TestCase):
    def test_summarize_cuenta_estados(self):
        checks = [
            Check("g", "a", OK),
            Check("g", "b", WARN, "detalle", "pista"),
            Check("g", "c", FAIL, "", "pista"),
            Check("g", "d", FAIL),
        ]
        self.assertEqual(summarize(checks), (1, 1, 2))

    def test_format_report_incluye_marca_y_pista(self):
        report = format_report([Check("Sistema", "algo", FAIL, "roto",
                                      "sudo arreglalo")])
        self.assertIn("[FALLA]", report)
        self.assertIn("algo: roto", report)
        self.assertIn("-> sudo arreglalo", report)
        self.assertIn("Resumen: 0 ok, 0 avisos, 1 fallos", report)


class RunChecksTests(unittest.TestCase):
    def test_no_lanza_y_devuelve_estados_validos(self):
        checks = run_checks(home="/tmp", user="nadie")
        self.assertTrue(checks)
        self.assertLessEqual({c.status for c in checks}, {OK, WARN, FAIL})
        self.assertTrue(all(c.group and c.name for c in checks))

    def test_detecta_config_de_umbriel_ausente(self):
        with tempfile.TemporaryDirectory() as tmp:
            names = {c.name: c.status for c in run_checks(home=tmp, user="nadie")}
        self.assertEqual(names["config de Umbriel"], FAIL)

    def test_acepta_config_de_umbriel_correcto(self):
        with tempfile.TemporaryDirectory() as tmp:
            umbriel = Path(tmp) / ".config" / "umbriel"
            umbriel.mkdir(parents=True)
            (umbriel / "config.toml").write_text(CONFIG_OK)

            names = {c.name: c.status for c in run_checks(home=tmp, user="nadie")}

        self.assertEqual(names["Umbriel: layout flotante"], OK)
        self.assertEqual(names["Umbriel: atajos de teclado"], OK)
        self.assertEqual(names["Umbriel: tema de cursor"], OK)
        self.assertEqual(names["Umbriel: autostart sin kitty"], OK)

    def test_rechaza_layout_invalido_y_cursor_incorrecto(self):
        with tempfile.TemporaryDirectory() as tmp:
            umbriel = Path(tmp) / ".config" / "umbriel"
            umbriel.mkdir(parents=True)
            (umbriel / "config.toml").write_text(
                '[layout]\nmode = "floating"\n\n[general]\n'
                'autostart = ["noctalia", "kitty"]\n\n[keybinds]\n'
                '"Mod+Q" = "window-close"\n\n[input.cursor]\ntheme = ""\n')

            names = {c.name: c.status for c in run_checks(home=tmp, user="nadie")}

        self.assertEqual(names["Umbriel: layout flotante"], FAIL)
        self.assertEqual(names["Umbriel: tema de cursor"], FAIL)
        self.assertEqual(names["Umbriel: autostart sin kitty"], WARN)

    def test_detecta_dotfiles_y_temas_ausentes(self):
        with tempfile.TemporaryDirectory() as tmp:
            names = {c.name: c.status for c in run_checks(home=tmp, user="nadie")}
        self.assertEqual(names["dotfile kitty"], WARN)
        self.assertEqual(names["tema GTK Juno"], FAIL)
        self.assertEqual(names[f"cursores {CURSOR_THEME_NAME}"], FAIL)

    def test_avisa_si_nautilus_esta_instalado(self):
        """gnome-sushi arrastraba Nautilus; el doctor debe detectarlo."""
        with tempfile.TemporaryDirectory() as tmp, \
                patch("v0x3l.doctor._package_installed",
                      side_effect=lambda name: name == "nautilus"):
            names = {c.name: c.status for c in run_checks(home=tmp, user="nadie")}
        self.assertEqual(names["sin Nautilus (se usa Thunar)"], WARN)

    def test_nautilus_ausente_es_ok(self):
        with tempfile.TemporaryDirectory() as tmp, \
                patch("v0x3l.doctor._package_installed", return_value=False):
            names = {c.name: c.status for c in run_checks(home=tmp, user="nadie")}
        self.assertEqual(names["sin Nautilus (se usa Thunar)"], OK)


if __name__ == "__main__":
    unittest.main()
