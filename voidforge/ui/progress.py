# Pantalla de progreso durante la ejecucion de pasos

import urwid


class ProgressScreen:
    """Muestra el progreso de un paso con spinner y salida en vivo."""

    def __init__(self, step_num: int, total: int, title: str):
        self.spinner_frames = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
        self.spinner_idx = 0

        self.header = urwid.Text(
            f"[{step_num}/{total}] {title}",
            align="center"
        )
        self.spinner_widget = urwid.Text("")
        self.cmd_widget = urwid.Text("")
        self.output_walker = urwid.SimpleFocusListWalker([])
        self.output_box = urwid.ListBox(self.output_walker)

        # Limitar altura del output a 10 lineas
        output_cols = urwid.Columns([
            ("weight", 1, self.output_box),
        ])
        output_padded = urwid.Padding(output_cols, left=2, right=2)

        pile = urwid.Pile([
            ("pack", urwid.Divider("─")),
            ("pack", urwid.AttrMap(self.header, "title")),
            ("pack", urwid.Divider("")),
            ("pack", self.spinner_widget),
            ("pack", self.cmd_widget),
            ("pack", urwid.Divider("")),
            ("weight", 1, output_padded),
        ])
        self.widget = urwid.Filler(pile, valign="top")

    def update_spinner(self):
        self.spinner_idx = (self.spinner_idx + 1) % len(self.spinner_frames)
        frame = self.spinner_frames[self.spinner_idx]
        self.spinner_widget.set_text(f"   {frame} Trabajando...")
        return True  # seguir animando

    def show_command(self, desc: str):
        self.cmd_widget.set_text(f"   -> {desc}")

    def append_output(self, line: str):
        MAX_LINES = 100
        self.output_walker.append(
            urwid.Text(f"   {line}")
        )
        # Mantener maximo de lineas
        if len(self.output_walker) > MAX_LINES:
            del self.output_walker[0]
        # Auto-scroll
        if len(self.output_walker) > 0:
            self.output_box.set_focus(len(self.output_walker) - 1)

    def show_result(self, ok: bool, msg: str):
        mark = "[OK]" if ok else "[ERR]"
        color = "ok" if ok else "error"
        self.spinner_widget.set_text("")
        self.cmd_widget.set_text("")
        self.output_walker.append(
            urwid.AttrMap(urwid.Text(f"   {mark} {msg}"), color)
        )

    def get_widget(self):
        return self.widget
