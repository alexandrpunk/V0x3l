# StepsList - panel izquierdo con la lista de pasos

import urwid
from voidforge.config import TOTAL_STEPS


class StepsList:
    """Panel izquierdo que lista los pasos con su estado.

    Estados: pending, running, done, failed.
    El paso en curso aparece resaltado.
    """

    STEP_TITLES: list[str] = []

    def __init__(self):
        # Si STEP_TITLES no fue establecido, usar genericos
        if not StepsList.STEP_TITLES:
            StepsList.STEP_TITLES = [
                f"Paso {i}" for i in range(TOTAL_STEPS + 1)
            ]

        self.status: list[str] = ["pending"] * (TOTAL_STEPS + 1)
        self.items: list[urwid.AttrMap] = []
        self.widgets: list[urwid.Widget] = []

        for i in range(TOTAL_STEPS + 1):
            num = i
            title = StepsList.STEP_TITLES[i] if i < len(StepsList.STEP_TITLES) else f"Paso {i}"
            text = urwid.Text(f"  {num:2d}. {title}")
            attr = self._attr_for_status("pending")
            item = urwid.AttrMap(text, attr[0], attr[1])
            self.items.append(item)
            self.widgets.append(text)

        self.walker = urwid.SimpleFocusListWalker(self.items)
        self.list_box = urwid.ListBox(self.walker)

        # Envolver en un LineBox con titulo
        self.widget = urwid.LineBox(
            self.list_box,
            title="Pasos",
            title_align="left",
        )

    def _attr_for_status(self, status: str) -> tuple:
        return {
            "pending": ("dim", None),
            "running": ("title", "button_focus"),
            "done": ("ok", None),
            "failed": ("error", None),
        }.get(status, ("dim", None))

    def set_status(self, step_num: int, status: str):
        """Actualiza el estado visual de un paso.

        step_num: numero de paso (0-15)
        status: pending | running | done | failed
        """
        idx = step_num
        if idx < 0 or idx >= len(self.items):
            return

        self.status[idx] = status
        title = (StepsList.STEP_TITLES[idx]
                 if idx < len(StepsList.STEP_TITLES)
                 else f"Paso {idx}")
        prefix = {
            "pending": "  ",
            "running": " >",
            "done": "OK",
            "failed": "!!",
        }.get(status, "  ")

        text = urwid.Text(f" {prefix} {idx:2d}. {title}")
        attr = self._attr_for_status(status)
        self.items[idx] = urwid.AttrMap(text, attr[0], attr[1])
        self.walker[idx] = self.items[idx]

        # Si esta running, hacer scroll a ese paso
        if status == "running":
            self.walker.set_focus(idx)

    def set_titles(self, titles: list[str]):
        """Establece los titulos de los pasos."""
        StepsList.STEP_TITLES = titles[:]
        for i in range(min(len(titles), len(self.items))):
            self.set_status(i, self.status[i])

    def get_widget(self):
        return self.widget

    @staticmethod
    def default_titles() -> list[str]:
        """Retorna los titulos por defecto de los 16 pasos."""
        return [
            "Bootstrap",
            "Repositorios",
            "Kernel XanMod",
            "GPU NVIDIA",
            "Paquetes del sistema",
            "Polkit automontaje",
            "xdg-user-dirs + UFW",
            "Red + NetworkManager",
            "Flatpak + apps",
            "Servicios + Wayland",
            "TLP + energia",
            "Oh My Zsh",
            "LazyVim",
            "Colloid icons",
            "Plymouth + GRUB",
            "DMS (Dank Linux)",
        ]
