# Menu principal interactivo con urwid

import urwid
from voidforge.config import VERSION
from voidforge.ui.banner import get_banner_text


class MainMenu:
    """Menu principal con 6 opciones, navegable con ↑↓ Enter."""

    def __init__(self, on_choice: callable):
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
        header = urwid.Pile([
            urwid.Text(banner_text, align="center"),
            urwid.Text(f"                      v{VERSION}", align="center"),
            urwid.Divider(),
        ])

        buttons = []
        for key, label in self.choices:
            b = urwid.Button(f"  [{key}] {label}")
            urwid.connect_signal(b, "click", self._on_click, key)
            buttons.append(
                urwid.AttrMap(b, "body", "selected")
            )

        list_walker = urwid.SimpleFocusListWalker(buttons)
        list_box = urwid.ListBox(list_walker)

        footer_text = "  ↑↓ navegar | Enter seleccionar | Ctrl+C salir"
        footer = urwid.AttrMap(urwid.Text(footer_text), "footer")

        self.widget = urwid.Frame(
            body=urwid.Pile([
                ("pack", header),
                ("weight", 1, list_box),
            ]),
            footer=footer,
        )

    def _on_click(self, button, key):
        self.on_choice(key)

    def get_widget(self):
        return self.widget
