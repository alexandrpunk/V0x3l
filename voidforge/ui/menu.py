# Menu principal interactivo con urwid

import urwid
from voidforge.config import VERSION
from voidforge.ui.banner import get_banner_text


class MenuOption(urwid.WidgetWrap):
    """Opcion de menu navegable, con estilo mejorado.

    Al recibir el foco cambia a color resaltado (button_focus).
    Enter ejecuta la accion.
    """

    def __init__(self, key: str, label: str, on_choice):
        self.key = key
        self._on_choice = on_choice
        self.label = label

        # El texto con el numero y nombre de la opcion
        text = urwid.SelectableIcon(f"   ({key}) {label}", 0)

        # Colores: normal y al recibir foco
        self._widget = urwid.AttrMap(text, "button_normal", "button_focus")
        super().__init__(urwid.Padding(self._widget, left=2, right=2))

    def selectable(self):
        return True

    def keypress(self, size, key):
        if key in ("enter", " "):
            if self._on_choice:
                self._on_choice(self.key)
            return None
        return key


class MainMenu:
    """Menu principal con 6 opciones."""

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
            urwid.AttrMap(
                urwid.Text(banner_text, align="center"),
                "body"
            ),
            urwid.AttrMap(
                urwid.Text(f"  v{VERSION}", align="center"),
                "dim"
            ),
            urwid.Divider(" "),
        ])

        # Lista de opciones
        items = []
        for key, label in self.choices:
            option = MenuOption(key, label, self._on_choice)
            items.append(option)

        list_walker = urwid.SimpleFocusListWalker(items)
        list_box = urwid.ListBox(list_walker)

        self.widget = urwid.Pile([
            ("pack", banner),
            ("weight", 1, list_box),
        ])

    def _on_choice(self, key):
        if self.on_choice:
            self.on_choice(key)

    def get_widget(self):
        return self.widget
