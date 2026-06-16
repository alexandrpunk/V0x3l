# ExecutionScreen - pantalla dividida: pasos (izquierda) + output (derecha)

import urwid
from v0x3l.config import TOTAL_STEPS
from v0x3l.ui.steps_list import StepsList


class ExecutionScreen:
    """Pantalla de ejecucion con dos paneles lado a lado.

    Izquierda: lista de pasos con iconos de estado.
    Derecha: output del paso en ejecucion.
    Usa bordes dobles unicode para estetica.
    """

    def __init__(self):
        self.steps = StepsList()
        self.steps.set_titles(StepsList.default_titles())

        self._output_body = urwid.SolidFill(" ")
        self._right_box = self._make_panel(self._output_body, "Salida")

        self.columns = urwid.Columns([
            ("weight", 1, self.steps.get_widget()),
            ("weight", 2, self._right_box),
        ], dividechars=1)

        self.widget = urwid.Padding(self.columns, left=1, right=1)

    def _make_panel(self, widget, title):
        """Crea un LineBox con bordes dobles unicode."""
        return urwid.LineBox(
            widget,
            title=f"\u2500 {title} \u2500",
            title_align="center",
            tlcorner="\u2554", trcorner="\u2557",
            blcorner="\u255A", brcorner="\u255D",
            tline="\u2550", bline="\u2550",
            lline="\u2551", rline="\u2551",
        )

    def set_step_status(self, step_num: int, status: str):
        self.steps.set_status(step_num, status)

    def set_output(self, widget):
        self._right_box = self._make_panel(widget, "Salida")
        self.columns.contents[1] = (
            self._right_box,
            self.columns.options("weight", 2),
        )

    def get_widget(self):
        return self.widget
