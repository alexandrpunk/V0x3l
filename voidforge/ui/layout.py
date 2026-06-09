# Layout principal con Frame (header + body + footer)

import urwid


class VoidForgeLayout:
    """Layout principal de la aplicacion.

    Proporciona un Frame fijo con:
    - Header: barra superior con color de fondo (VoidForge.sh : titulo)
    - Body: contenido variable (menu, progreso, dialogo)
    - Footer: barra inferior con informacion contextual
    """

    def __init__(self, body=None, header_text="Menu principal",
                 footer_text="Ctrl+Q salir"):
        self._header_text = urwid.Text(
            f" VoidForge.sh : {header_text}",
            align="left"
        )
        header = urwid.AttrMap(self._header_text, "header_bg")

        self._footer_text = urwid.Text(
            f" {footer_text}",
            align="left"
        )
        footer = urwid.AttrMap(self._footer_text, "footer_bg")

        if body is None:
            body = urwid.SolidFill(" ")

        self.frame = urwid.Frame(
            header=header,
            body=body,
            footer=footer,
        )

    def set_body(self, widget):
        """Cambia el contenido del cuerpo."""
        self.frame.body = widget

    def set_header(self, text: str):
        """Actualiza el titulo en la barra superior."""
        self._header_text.set_text(f" VoidForge.sh : {text}")

    def set_footer(self, text: str):
        """Actualiza la informacion en la barra inferior."""
        self._footer_text.set_text(f" {text}")

    def show_menu(self, widget):
        """Muestra el menu (header appropriado)."""
        self.set_header("Menu principal")
        self.set_footer(u"\u2191\u2193 navegar | Enter elegir | Ctrl+Q salir")
        self.set_body(widget)

    def show_progress(self, step_num: int, total: int, title: str):
        """Configura layout para pantalla de progreso."""
        self.set_header(f"Paso {step_num}/{total} - {title}")
        self.set_footer(u"Ctrl+Q cancelar | Log: /tmp/voidforge.log")

    def show_result(self, ok: bool, msg: str):
        """Muestra resultado breve en el footer."""
        mark = "[OK]" if ok else "[ERR]"
        color = "ok" if ok else "error"
        self.set_footer(f" {mark} {msg}")

    def get_widget(self) -> urwid.Frame:
        return self.frame
