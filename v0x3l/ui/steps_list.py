# StepsList - panel izquierdo con la lista de pasos e iconos de estado

import urwid
from v0x3l.config import TOTAL_STEPS


class StepsList:
    """Panel izquierdo que lista los pasos con su estado.

    Iconos unicode:
      \u25CB  pendiente (circulo vacio)
      \u25B8  en curso (triangulo derecha, resaltado)
      \u2713  completado (check verde)
      \u2717  fallido (cruz roja)
    """

    STEP_TITLES: list[str] = []

    STATUS_ICONS = {
        "pending": "\u25CB",
        "running": "\u25B8",
        "done":    "\u2713",
        "failed":  "\u2717",
    }

    STATUS_ATTRS = {
        "pending": ("dim", None),
        "running": ("title", "button_focus"),
        "done":    ("ok", None),
        "failed":  ("error", None),
    }

    def __init__(self):
        if not StepsList.STEP_TITLES:
            StepsList.STEP_TITLES = [f"Paso {i}" for i in range(TOTAL_STEPS + 1)]

        self.status: list[str] = ["pending"] * (TOTAL_STEPS + 1)
        self.items: list[urwid.AttrMap] = []

        for i in range(TOTAL_STEPS + 1):
            title = (StepsList.STEP_TITLES[i]
                     if i < len(StepsList.STEP_TITLES) else f"Paso {i}")
            text = urwid.Text(f"  \u25CB  {title}")
            attr = self.STATUS_ATTRS["pending"]
            item = urwid.AttrMap(text, attr[0], attr[1])
            self.items.append(item)

        self.walker = urwid.SimpleFocusListWalker(self.items)
        self.list_box = urwid.ListBox(self.walker)

        self.widget = urwid.LineBox(
            urwid.Padding(self.list_box, left=1, right=1),
            title="\u2500 Pasos \u2500",
            title_align="center",
            tlcorner="\u2554", trcorner="\u2557",
            blcorner="\u255A", brcorner="\u255D",
            tline="\u2550", bline="\u2550",
            lline="\u2551", rline="\u2551",
        )

    def set_status(self, step_num: int, status: str):
        """Actualiza el estado visual de un paso."""
        idx = step_num
        if idx < 0 or idx >= len(self.items):
            return

        self.status[idx] = status
        title = (StepsList.STEP_TITLES[idx]
                 if idx < len(StepsList.STEP_TITLES) else f"Paso {idx}")
        icon = self.STATUS_ICONS.get(status, "\u25CB")
        attr = self.STATUS_ATTRS.get(status, ("dim", None))

        text = urwid.Text(f"  {icon}  {title}")
        self.items[idx] = urwid.AttrMap(text, attr[0], attr[1])
        self.walker[idx] = self.items[idx]

        if status == "running":
            self.walker.set_focus(idx)

    def set_titles(self, titles: list[str]):
        StepsList.STEP_TITLES = titles[:]
        for i in range(min(len(titles), len(self.items))):
            self.set_status(i, self.status[i])

    def get_widget(self):
        return self.widget

    @staticmethod
    def default_titles() -> list[str]:
        return [
            "Preparacion del sistema",
            "Rendimiento y drivers",
            "Software",
            "Configuracion",
            "Apariencia",
            "Entorno",
        ]
