# Menu principal - panel con botones estilizados

import urwid
from v0x3l.ui.banner import get_banner_text


class MenuButton(urwid.WidgetWrap):
    """Boton de menu navegable con hotkey resaltado.

    Muestra el numero de opcion en color accent y el label en color body.
    Al obtener foco, todo el boton se resalta en verde.
    """

    def __init__(self, key: str, label: str, on_choice):
        self.key = key
        self._on_choice = on_choice

        text = urwid.Text([
            ("hotkey", f"  {key} "),
            ("body", f" \u25B8 {label}"),
        ])
        self._attr = urwid.AttrMap(
            text,
            attr_map={"body": "button_normal"},
            focus_map={"body": "button_focus", "hotkey": "button_focus"},
        )
        padded = urwid.Padding(self._attr, left=1, right=1)
        super().__init__(padded)

    def selectable(self):
        return True

    def keypress(self, size, key):
        if key in ("enter", " "):
            if self._on_choice:
                self._on_choice(self.key)
            return None
        return key


class MainMenu:
    """Menu principal con 6 opciones en un panel con borde."""

    def __init__(self, on_choice):
        self.on_choice = on_choice
        self.choices = [
            ("1", "Instalacion completa (pasos 0-5)"),
            ("2", "Reanudar desde ultimo checkpoint"),
            ("3", "Ejecutar paso especifico"),
            ("4", "Ejecutar rango de pasos"),
            ("5", "Ver estado actual"),
            ("6", "Salir"),
        ]

        buttons = []
        for key, label in self.choices:
            btn = MenuButton(key, label, self._on_choice)
            buttons.append(btn)

        list_box = urwid.ListBox(urwid.SimpleFocusListWalker(buttons))

        menu_content = urwid.Pile([
            ("pack", urwid.Text("")),
            urwid.Padding(list_box, left=1, right=1),
            ("pack", urwid.Text("")),
        ])

        panel = urwid.LineBox(
            menu_content,
            title="\u2500 Opciones \u2500",
            title_align="center",
            tlcorner="\u2554", trcorner="\u2557",
            blcorner="\u255A", brcorner="\u255D",
            tline="\u2550", bline="\u2550",
            lline="\u2551", rline="\u2551",
        )

        banner_text = get_banner_text()

        self.widget = urwid.Pile([
            ("pack", urwid.Padding(
                urwid.AttrMap(urwid.Text(banner_text, align="center"), "title"),
                left=2, right=2
            )),
            ("pack", urwid.AttrMap(
                urwid.Text("Modular post-installer for Ubuntu Server", align="center"),
                "dim"
            )),
            ("pack", urwid.Text("")),
            ("weight", 1, panel),
        ])

    def _on_choice(self, key):
        if self.on_choice:
            self.on_choice(key)

    def get_widget(self):
        return self.widget
