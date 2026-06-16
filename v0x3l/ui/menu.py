# Menu principal - panel con botones estilizados

import urwid
import subprocess
from v0x3l.config import ASCII_FILE


class MenuButton(urwid.WidgetWrap):
    """Boton de menu navegable sin los feos [ ] de urwid.Button."""

    def __init__(self, key: str, label: str, on_choice):
        self.key = key
        self._on_choice = on_choice

        self._icon = urwid.SelectableIcon(
            f"   {key}  {label}", cursor_position=0
        )
        self._attr = urwid.AttrMap(self._icon, "button_normal", "button_focus")
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
            urwid.Padding(list_box, left=1, right=1),
        ])

        panel = urwid.LineBox(
            menu_content,
            title="\u2500 Menu \u2500",
            title_align="center",
            tlcorner="\u2554", trcorner="\u2557",
            blcorner="\u255A", brcorner="\u255D",
            tline="\u2550", bline="\u2550",
            lline="\u2551", rline="\u2551",
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
            ("pack", urwid.Padding(
                urwid.AttrMap(urwid.Text(banner_text, align="center"), "body"),
                left=2, right=2
            )),
            ("pack", urwid.Text("")),
            ("weight", 1, panel),
        ])

    def _on_choice(self, key):
        if self.on_choice:
            self.on_choice(key)

    def get_widget(self):
        return self.widget
