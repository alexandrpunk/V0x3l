# Layout principal con Frame (header + body + footer)

import urwid
from v0x3l.config import VERSION, PROJECT_NAME


class V0x3lLayout:
    """Layout principal de la aplicacion.

    Header: barra verde con titulo de seccion, separador visual
    Body:   contenido variable (menu, ejecucion, dialogo)
    Footer: hints contextuales (izquierda) + version (derecha)
    """

    def __init__(self, body=None, header_text="Menu principal",
                 footer_text="Q salir"):
        self._header_text = urwid.Text(
            f"  \u25C6 {PROJECT_NAME}  \u2502  {header_text}",
            align="left"
        )
        header = urwid.AttrMap(self._header_text, "header_bg")

        self._footer_left = urwid.Text(f" {footer_text}", align="left")
        self._footer_right = urwid.Text(f" v{VERSION} ", align="right")
        footer_cols = urwid.Columns([
            ("weight", 1, self._footer_left),
            ("pack", urwid.Text(" \u2502 ")),
            ("pack", self._footer_right),
        ])
        footer = urwid.AttrMap(footer_cols, "footer_bg")

        header_pile = urwid.Pile([
            ("pack", header),
            ("pack", urwid.AttrMap(urwid.Text("\u2500" * 200), "separator")),
        ])

        if body is None:
            body = urwid.SolidFill(" ")

        self.frame = urwid.Frame(
            header=header_pile,
            body=body,
            footer=footer,
        )

    def set_body(self, widget):
        self.frame.body = widget

    def set_header(self, text: str):
        self._header_text.set_text(f"  \u25C6 {PROJECT_NAME}  \u2502  {text}")

    def set_footer(self, text: str):
        self._footer_left.set_text(f" {text}")

    def show_menu(self, widget):
        self.set_header("Menu principal")
        self.set_footer("1-6 Seleccionar \u2502 Q Salir")
        self.set_body(widget)

    def show_execution(self, widget):
        self.set_header("Ejecutando")
        self.set_footer("Q Cancelar \u2502 Log: /tmp/v0x3l.log")
        self.set_body(widget)

    def show_result(self, ok: bool, msg: str):
        mark = "\u2714 OK" if ok else "\u2718 ERR"
        self.set_footer(f"[{mark}] {msg}")

    def get_widget(self) -> urwid.Frame:
        return self.frame
