# ExecutionScreen - pantalla dividida: pasos (izquierda) + output (derecha)

import urwid
from voidforge.config import TOTAL_STEPS
from voidforge.ui.steps_list import StepsList


class ExecutionScreen:
    """Pantalla de ejecucion con dos paneles lado a lado.

    Izquierda: lista de pasos con estado (StepsList).
    Derecha: output del paso en ejecucion.
    """

    def __init__(self):
        self.steps = StepsList()
        self.steps.set_titles(StepsList.default_titles())

        # Panel derecho: area de output
        self._output_body = urwid.SolidFill(" ")
        self._right_box = urwid.LineBox(
            self._output_body,
            title="Salida",
            title_align="left",
        )

        # Columnas: izquierda (1/3) + derecha (2/3)
        self.columns = urwid.Columns([
            ("weight", 1, self.steps.get_widget()),
            ("weight", 2, self._right_box),
        ])

        self.widget = self.columns

    def set_step_status(self, step_num: int, status: str):
        """Actualiza el estado de un paso en la lista izquierda."""
        self.steps.set_status(step_num, status)

    def set_output(self, widget):
        """Establece el contenido del panel derecho."""
        self._right_box = urwid.LineBox(
            widget,
            title="Salida",
            title_align="left",
        )
        self.columns.contents[1] = (
            self._right_box,
            self.columns.options("weight", 2),
        )

    def set_output_title(self, title: str):
        """Actualiza el titulo del panel derecho."""
        body = self.columns.contents[1][0]
        if isinstance(body, urwid.LineBox):
            body.set_title(title)

    def get_widget(self):
        return self.widget
