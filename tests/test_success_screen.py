import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from v0x3l.app import V0x3lApp
from v0x3l.ui.dialogs import success_dialog


class _FakeLoop:
    """Loop minimo: registra alarms y dibujos."""

    def __init__(self):
        self.draws = 0
        self.alarms = []

    def draw_screen(self):
        self.draws += 1

    def set_alarm_in(self, delay, callback):
        self.alarms.append((delay, callback))


class SuccessScreenTests(unittest.TestCase):
    def _app(self) -> V0x3lApp:
        app = V0x3lApp()
        app.loop = None
        return app

    def test_success_dialog_builds(self):
        dialog = success_dialog(
            "Listo", "mensaje", lambda: None, lambda: None,
            log_path="/tmp/v0x3l.log")
        self.assertIsNotNone(dialog)

    def test_text_success_con_no_no_reinicia(self):
        app = self._app()
        with redirect_stdout(io.StringIO()), \
                patch("builtins.input", return_value="n"), \
                patch.object(app, "_reboot_system") as reboot:
            app.on_all_done()
        reboot.assert_not_called()

    def test_text_success_con_si_reinicia(self):
        app = self._app()
        with redirect_stdout(io.StringIO()), \
                patch("builtins.input", return_value="s"), \
                patch.object(app, "_reboot_system", return_value=True) as reboot:
            app.on_all_done()
        reboot.assert_called_once()

    def test_tui_programa_y_muestra_pantalla_de_exito(self):
        app = self._app()
        app.loop = _FakeLoop()
        app.on_all_done()

        self.assertEqual(len(app.loop.alarms), 1)
        _delay, callback = app.loop.alarms[0]
        callback(app.loop, None)

        self.assertTrue(app._success)
        self.assertTrue(app._modal)
        self.assertGreaterEqual(app.loop.draws, 1)


    def test_pulsar_reiniciar_muestra_confirmacion(self):
        import urwid

        app = self._app()
        app._on_reboot_pressed()
        self.assertIsInstance(app.layout.frame.body, urwid.Overlay)

    def test_reboot_llama_systemctl(self):
        app = self._app()
        with patch("v0x3l.app.run", return_value=True) as run_mock:
            self.assertTrue(app._reboot_system())
        run_mock.assert_called_once_with("reboot", "systemctl", "reboot", sudo=True)

    def test_reboot_falla_devuelve_false(self):
        app = self._app()
        with patch("v0x3l.app.run", return_value=False):
            self.assertFalse(app._reboot_system())


if __name__ == "__main__":
    unittest.main()