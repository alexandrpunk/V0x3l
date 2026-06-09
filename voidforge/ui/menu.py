# Menu principal — version minimal y probada

import urwid
from voidforge.config import VERSION
from voidforge.ui.banner import get_banner_text


class MainMenu:
    """Menu principal con 6 opciones usando urwid.Button directamente."""

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

        banner_text = get_banner_text()
        banner = urwid.Pile([
            urwid.Text(banner_text, align="center"),
            urwid.Text(f"  v{VERSION}", align="center"),
            urwid.Divider(" "),
        ])

        # Lista de botones simple y probada
        items = []
        for key, label in self.choices:
            btn = urwid.Button(f"  ({key}) {label}")
            urwid.connect_signal(btn, "click", self._on_click, key)
            items.append(
                urwid.AttrMap(btn, "button_normal", "button_focus")
            )

        list_box = urwid.ListBox(urwid.SimpleFocusListWalker(items))

        self.widget = urwid.Pile([
            ("pack", banner),
            ("weight", 1, list_box),
        ])

    def _on_click(self, button, key):
        if self.on_choice:
            self.on_choice(key)

    def get_widget(self):
        return self.widget
