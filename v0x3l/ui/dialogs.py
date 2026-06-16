# Dialogos de la UI (confirmacion, input, mensajes)

import urwid
from typing import Callable, Optional


def confirm_dialog(title: str, message: str, on_yes: Callable,
                   on_no: Optional[Callable] = None):
    """Dialogo de confirmacion Si/No."""
    body = [
        urwid.Text(message, align="center"),
        urwid.Text(""),
        urwid.Columns([
            urwid.Button("  Si  ", on_press=lambda _: on_yes()),
            urwid.Button("  No  ", on_press=lambda _: on_no() if on_no else None),
        ]),
    ]
    dialog = urwid.LineBox(
        urwid.Pile(body),
        title=title
    )
    return dialog


def input_dialog(title: str, prompt: str, on_submit: Callable,
                 on_cancel: Optional[Callable] = None):
    """Dialogo de entrada de texto."""
    edit = urwid.Edit(f"  {prompt}: ")
    body = [
        urwid.Text(prompt),
        urwid.Text(""),
        edit,
        urwid.Text(""),
        urwid.Button("  Aceptar  ", on_press=lambda _: on_submit(edit.get_edit_text())),
    ]
    if on_cancel:
        body.append(urwid.Button("  Cancelar  ", on_press=lambda _: on_cancel()))

    dialog = urwid.LineBox(
        urwid.Pile(body),
        title=title
    )
    return dialog, edit


def error_dialog(title: str, message: str, log_path: str, on_close: Callable):
    """Dialogo de error con informacion de log."""
    body = [
        urwid.Text(message, align="center"),
        urwid.Text(""),
        urwid.AttrMap(
            urwid.Text(f"  Log guardado en: {log_path}", align="center"),
            "info"
        ),
        urwid.Text(""),
        urwid.Button("  Cerrar  ", on_press=lambda _: on_close()),
    ]
    dialog = urwid.LineBox(
        urwid.Pile(body),
        title=title
    )
    return dialog
