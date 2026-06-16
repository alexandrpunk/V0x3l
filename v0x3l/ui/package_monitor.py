# Visor compacto de instalacion de paquetes (nala/apt/flatpak)

import re
import urwid
from datetime import datetime


class PackageMonitor:
    """Monitor compacto para instalacion de paquetes.

    Reemplaza el output generico del ProgressScreen con una vista
    estructurada: barra de progreso, contador, velocidad, paquete actual.
    """

    def __init__(self):
        self.total_packages: int = 0
        self.current_package: int = 0
        self.current_pkg_name: str = ""
        self.speed: str = "--"
        self.percentage: int = 0
        self.downloaded: str = "0 MB"
        self.total_download: str = "--"
        self.start_time = datetime.now()
        self.last_lines: list[str] = []

        # ── Widgets urwid ──
        self.spinner_frames = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
        self.spinner_idx = 0
        self.spinner_widget = urwid.Text("   ⣾ Iniciando...")

        self.progress_bar = urwid.ProgressBar("progress_bar", "progress_done")
        self.progress_bar.set_completion(0)

        self.counter_widget = urwid.Text("", align="right")
        self.speed_widget = urwid.Text("   Velocidad: --", align="left")
        self.package_widget = urwid.AttrMap(
            urwid.Text("", align="center"),
            "pkg_name"
        )
        self.eta_widget = urwid.Text("   ⏱ --", align="right")

        # Zona de progreso: barra + contador
        self.progress_row = urwid.Columns([
            ("weight", 3, self.progress_bar),
            ("weight", 1, self.counter_widget),
        ])

        # Zona de detalles: velocidad + ETA
        self.detail_row = urwid.Columns([
            self.speed_widget,
            self.eta_widget,
        ])

        # Log que llena el espacio disponible
        self.log_walker = urwid.SimpleFocusListWalker([])
        self.log_box = urwid.ListBox(self.log_walker)
        self.log_area = urwid.Padding(self.log_box, left=2, right=2)

        # ── Layout final ──
        columns = urwid.Columns([
            ("weight", 1, self.spinner_widget),
        ])
        self.widget = urwid.Pile([
            ("pack", urwid.Text(" ")),
            ("pack", columns),
            ("pack", urwid.Text(" ")),
            ("pack", self.progress_row),
            ("pack", self.detail_row),
            ("pack", urwid.Text("─")),
            ("pack", self.package_widget),
            ("pack", urwid.Text("─")),
            ("weight", 1, self.log_area),
        ])

    # ── Procesamiento de lineas ──

    def feed_line(self, line: str):
        """Procesa una linea del output de nala/apt."""
        self.last_lines.append(line)
        if len(self.last_lines) > 20:
            self.last_lines.pop(0)

        # Progreso porcentual: "45%" o "[45%]"
        m = re.search(r"(\d+)%", line)
        if m:
            pct = int(m.group(1))
            if pct > self.percentage:
                self.percentage = pct
                self.progress_bar.set_completion(pct)

        # Contador de paquetes: "Get:1 http://..." o "(45/77)"
        m = re.search(r"\((\d+)/(\d+)\)", line)
        if m:
            self.current_package = max(self.current_package, int(m.group(1)))
            self.total_packages = max(self.total_packages, int(m.group(2)))

        # Velocidad de descarga
        m = re.search(r"([\d.]+ [KMGT]B/s)", line)
        if m:
            self.speed = m.group(1)

        # Tamaño total descargado: "Fetched 45.8 MB in 12s (3.8 MB/s)"
        m = re.search(r"Fetched ([\d.]+ [KMGT]B) in", line)
        if m:
            self.downloaded = m.group(1)

        # Paquete actual
        for keyword in ("Get:", "Unpacking", "Setting"):
            if keyword in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == keyword and i + 1 < len(parts):
                        self.current_pkg_name = parts[i + 1].split("/")[0]
                        break

        self._refresh()

    # ── Actualizacion visual ──

    def _refresh(self):
        """Refresca todos los widgets con datos actuales."""
        # Spinner
        self.spinner_idx = (self.spinner_idx + 1) % len(self.spinner_frames)
        self.spinner_widget.set_text(
            f"   {self.spinner_frames[self.spinner_idx]} Instalando paquetes..."
        )

        # Contador
        if self.total_packages > 0:
            self.counter_widget.set_text(
                f" {self.current_package}/{self.total_packages} paquetes"
            )
        else:
            pct = min(self.percentage, 100)
            self.counter_widget.set_text(f" {pct}%")

        # Velocidad
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if elapsed < 5:
            self.speed_widget.set_text(f"   Velocidad: {self.speed}")
        else:
            self.speed_widget.set_text(f"   \u2193 {self.speed}")

        # ETA
        if self.percentage > 0 and elapsed > 3:
            remaining = (elapsed / self.percentage) * (100 - self.percentage)
            mins, secs = divmod(int(remaining), 60)
            if mins > 0:
                self.eta_widget.set_text(f"\u23f1 ~{mins}m {secs}s")
            else:
                self.eta_widget.set_text(f"\u23f1 ~{secs}s")
        else:
            self.eta_widget.set_text(f"\u23f1 --")

        # Paquete actual
        if self.current_pkg_name:
            self.package_widget.original_widget.set_text(
                f"  {self.current_pkg_name}"
            )
        else:
            self.package_widget.original_widget.set_text("")

        # Log: tantas lineas como quepan
        self.log_walker.clear()
        for ln in self.last_lines[-15:]:
            display = ln[:80]
            self.log_walker.append(
                urwid.Text(("dim", f"  {display}"))
            )
        if len(self.log_walker) > 0:
            self.log_box.set_focus(len(self.log_walker) - 1)

    def update_spinner(self):
        """Actualiza solo el spinner (llamado desde el event loop)."""
        self.spinner_idx = (self.spinner_idx + 1) % len(self.spinner_frames)
        self.spinner_widget.set_text(
            f"   {self.spinner_frames[self.spinner_idx]} Instalando paquetes..."
        )
        return True

    def get_widget(self):
        return self.widget
