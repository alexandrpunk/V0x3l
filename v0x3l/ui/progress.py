# Pantalla de progreso durante la ejecucion de pasos

import urwid
from typing import Optional
from v0x3l.ui.package_monitor import PackageMonitor


class ProgressScreen:
    """Muestra el progreso de un paso con spinner y salida en vivo."""

    def __init__(self, step_num: int, total: int, title: str):
        self._pkg_monitor: Optional[PackageMonitor] = None

        self.spinner_frames = ["\u28fe", "\u28fd", "\u28fb", "\u28bf",
                               "\u28df", "\u28f7", "\u28ef", "\u28df"]
        self.spinner_idx = 0

        self.header = urwid.Text(
            f" [{step_num}/{total}] {title}",
            align="left"
        )
        self.spinner_widget = urwid.Text("")
        self.cmd_widget = urwid.Text("")
        self.output_walker = urwid.SimpleFocusListWalker([])
        self.output_box = urwid.ListBox(self.output_walker)

        self.pile = urwid.Pile([
            ("pack", urwid.Text("")),
            ("pack", urwid.AttrMap(self.header, "title")),
            ("pack", urwid.Text("")),
            ("pack", self.spinner_widget),
            ("pack", self.cmd_widget),
            ("pack", urwid.Text("")),
            ("weight", 1, urwid.Padding(self.output_box, left=2, right=2)),
        ])
        self.widget = self.pile

    def use_package_monitor(self):
        self._pkg_monitor = PackageMonitor()
        pkg_widget = self._pkg_monitor.get_widget()
        panel = urwid.Padding(
            urwid.LineBox(pkg_widget,
                          title="\u2500 Paquetes \u2500",
                          title_align="center",
                          tlcorner="\u2554", trcorner="\u2557",
                          blcorner="\u255A", brcorner="\u255D",
                          tline="\u2550", bline="\u2550",
                          lline="\u2551", rline="\u2551"),
            left=2, right=2
        )
        self.pile.contents[6] = (panel, ("weight", 1))

    def feed_line(self, line: str):
        if self._pkg_monitor:
            self._pkg_monitor.feed_line(line)
        else:
            self.append_output(line)

    def update_spinner(self):
        if self._pkg_monitor:
            return self._pkg_monitor.update_spinner()
        self.spinner_idx = (self.spinner_idx + 1) % len(self.spinner_frames)
        frame = self.spinner_frames[self.spinner_idx]
        self.spinner_widget.set_text(
            f"  {frame} Procesando..."
        )
        return True

    def show_command(self, desc: str):
        self.cmd_widget.set_text(f"  \u25b8 {desc}")

    def append_output(self, line: str):
        MAX_LINES = 100
        self.output_walker.append(
            urwid.Text(("dim", f"  {line}"))
        )
        if len(self.output_walker) > MAX_LINES:
            del self.output_walker[0]
        if len(self.output_walker) > 0:
            self.output_box.set_focus(len(self.output_walker) - 1)

    def show_result(self, ok: bool, msg: str):
        mark = "OK" if ok else "ERR"
        color = "ok" if ok else "error"
        self.spinner_widget.set_text("")
        self.cmd_widget.set_text("")
        if self._pkg_monitor:
            self._pkg_monitor = None
        self.output_walker.append(
            urwid.AttrMap(urwid.Text(f"  [{mark}] {msg}"), color)
        )

    def get_widget(self):
        return self.widget
