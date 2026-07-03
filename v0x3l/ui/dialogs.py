# Dialogos de la UI (confirmacion, input, mensajes)

import urwid
from typing import Callable, Optional


def _make_dialog(pile_body, title: str) -> urwid.LineBox:
    """Helper: creates a consistently styled LineBox dialog."""
    return urwid.LineBox(
        urwid.Padding(urwid.Pile(pile_body), left=2, right=2),
        title=f" {title} ",
        title_align="center",
        tlcorner="\u2554", trcorner="\u2557",
        blcorner="\u255A", brcorner="\u255D",
        tline="\u2550", bline="\u2550",
        lline="\u2551", rline="\u2551",
    )


def confirm_dialog(title: str, message: str, on_yes: Callable,
                   on_no: Optional[Callable] = None):
    """Dialogo de confirmacion Si/No."""
    body = [
        urwid.Text(""),
        urwid.Text(message, align="center"),
        urwid.Text(""),
        urwid.Columns([
            ("pack", urwid.Text("  ")),
            urwid.Button("  Si  ", on_press=lambda _: on_yes()),
            ("pack", urwid.Text("   ")),
            urwid.Button("  No  ", on_press=lambda _: on_no() if on_no else None),
            ("pack", urwid.Text("  ")),
        ]),
        urwid.Text(""),
    ]
    return _make_dialog(body, title)


def input_dialog(title: str, prompt: str, on_submit: Callable,
                 on_cancel: Optional[Callable] = None):
    """Dialogo de entrada de texto."""
    edit = urwid.Edit(f"  {prompt}: ")
    body = [
        urwid.Text(""),
        urwid.Text(prompt),
        urwid.Text(""),
        edit,
        urwid.Text(""),
        urwid.Button("  Aceptar  ", on_press=lambda _: on_submit(edit.get_edit_text())),
    ]
    if on_cancel:
        body.append(urwid.Button("  Cancelar  ", on_press=lambda _: on_cancel()))
    body.append(urwid.Text(""))

    return _make_dialog(body, title), edit


def message_dialog(title: str, message: str, on_close: Callable):
    """Dialogo de mensaje informativo."""
    body = [
        urwid.Text(""),
        urwid.Text(message, align="center"),
        urwid.Text(""),
        urwid.Button("  OK  ", on_press=lambda _: on_close()),
        urwid.Text(""),
    ]
    return _make_dialog(body, title)


def error_dialog(title: str, message: str, log_path: str, on_close: Callable):
    """Dialogo de error con informacion de log."""
    body = [
        urwid.Text(""),
        urwid.Text(message, align="center"),
        urwid.Text(""),
        urwid.AttrMap(
            urwid.Text(f"  Log guardado en: {log_path}", align="center"),
            "info"
        ),
        urwid.Text(""),
        urwid.Button("  Cerrar  ", on_press=lambda _: on_close()),
        urwid.Text(""),
    ]
    return _make_dialog(body, title)
