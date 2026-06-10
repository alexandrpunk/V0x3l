# Menu principal - panel con delineado

import urwid
import subprocess
from voidforge.config import ASCII_FILE


class MainMenu:
    """Menu principal con 6 opciones en un panel con borde."""

    def __init__(self, on_choice):
        self.on_choice = on_choice
        self.choices = [
            ("1", "Instalacion completa (pasos 0-15)"),
            ("2", "Reanudar desde ultimo checkpoint"),
            ("3", "Ejecutar paso especifico"),
            ("4", "Ejecutar rango de pasos"),
            ("5", "Ver estado actual"),
            ("6", "Salir"),
        ]

        buttons = []
        for key, label in self.choices:
            btn = urwid.Button(f"  ({key}) {label}")
            urwid.connect_signal(btn, "click", self._on_click, key)
            buttons.append(
                urwid.AttrMap(btn, "button_normal", "button_focus")
            )

        list_box = urwid.ListBox(urwid.SimpleFocusListWalker(buttons))

        # Panel con borde
        panel = urwid.LineBox(
            urwid.Pile([
                list_box,
            ]),
            title="Menu",
            title_align="left",
        )

        banner_text = ""
        try:
            r = subprocess.run(["bash", str(ASCII_FILE)],
                               capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout.strip():
                banner_text = r.stdout
        except Exception:
            pass
        self.widget = urwid.Pile([
            ("pack", urwid.Text(banner_text, align="center")),
            ("pack", urwid.Text("")),
            ("weight", 1, panel),
        ])

    def _on_click(self, button, key):
        if self.on_choice:
            self.on_choice(key)

    def get_widget(self):
        return self.widget
