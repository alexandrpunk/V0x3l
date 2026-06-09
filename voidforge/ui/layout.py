# Layout principal con Frame (header + body + footer)

import urwid
from voidforge.config import VERSION


class VoidForgeLayout:
    """Layout principal de la aplicacion.

    Proporciona un Frame fijo con:
    - Header: separador (VoidForge.sh : titulo)
    - Body: contenido variable (menu, ejecucion, dialogo)
    - Footer: info contextual + version a la derecha
    """

    def __init__(self, body=None, header_text="Menu principal",
                 footer_text="Ctrl+Q salir"):
        self._header_text = urwid.Text(
            f" VoidForge.sh : {header_text}",
            align="left"
        )
        header = urwid.AttrMap(self._header_text, "header_bg")

        # Footer con version a la derecha
        self._footer_left = urwid.Text(f" {footer_text}", align="left")
        self._footer_right = urwid.Text(f" v{VERSION} ", align="right")
        footer_pile = urwid.Columns([
            ("weight", 1, self._footer_left),
            ("pack", self._footer_right),
        ])
        footer = urwid.AttrMap(footer_pile, "footer_bg")

        header_pile = urwid.Pile([
            ("pack", header),
            ("pack", urwid.Divider("─")),
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
        self._header_text.set_text(f" VoidForge.sh : {text}")

    def set_footer(self, text: str):
        self._footer_left.set_text(f" {text}")

    def show_menu(self, widget):
        self.set_header("Menu principal")
        self.set_footer(u"\u2191\u2193 navegar | Enter elegir | Ctrl+Q salir")
        self.set_body(widget)

    def show_execution(self, widget):
        self.set_header("Ejecutando...")
        self.set_footer("Ctrl+Q cancelar | Log: /tmp/voidforge.log")
        self.set_body(widget)

    def show_result(self, ok: bool, msg: str):
        mark = "[OK]" if ok else "[ERR]"
        self.set_footer(f" {mark} {msg}")

    def get_widget(self) -> urwid.Frame:
        return self.frame
