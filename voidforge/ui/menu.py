# Menu principal - panel con delineado

import urwid
from voidforge.ui.banner import get_banner_text


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

        self.widget = panel

    def _on_click(self, button, key):
        if self.on_choice:
            self.on_choice(key)

    def get_widget(self):
        return self.widget
