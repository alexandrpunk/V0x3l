#!/usr/bin/env python3
# VoidForge UI Demo — muestra la interfaz sin modificar el sistema
# Uso: python3 demo_ui.py

import sys
import os
import time
import random

# Asegurar que el modulo voidforge esta en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Silenciar logging durante el demo
os.environ["LOG_FILE"] = "/dev/null"

import urwid
from voidforge.config import PALETTE, VERSION, TOTAL_STEPS
from voidforge.ui.menu import MainMenu
from voidforge.ui.progress import ProgressScreen
from voidforge.ui.dialogs import message_dialog


# ── Datos simulados de instalacion ──

NALA_OUTPUT_SIMULATION = [
    # Lineas simuladas de nala install
    "Leyendo lista de paquetes... Hecho",
    "Creando arbol de dependencias... Hecho",
    "Leyendo informacion de estado... Hecho",
    "Los paquetes indicados adicionales se instalaran:",
    "  libwayland-client0 libwayland-server0 libegl1 libgl1-mesa-dri",
    "Se instalaran 77 paquetes nuevos (45.8 MB para descargar)",
    "",
    "Descargando...",
    "Get:1 http://archive.ubuntu.com noble/main amd64 libwayland-client0 (0.8 MB) [1%]",
    "Get:2 http://archive.ubuntu.com noble/main amd64 libwayland-server0 (0.4 MB) [3%]",
    "Get:3 http://archive.ubuntu.com noble/main amd64 libegl1 (0.2 MB) [5%]",
    "Get:4 http://archive.ubuntu.com noble/main amd64 libgl1-mesa-dri (8.2 MB) [10%]",
    "Get:5 http://archive.ubuntu.com noble/main amd64 mesa-vulkan-drivers (4.1 MB) [15%]",
    "Get:6 http://archive.ubuntu.com noble/main amd64 xwayland (1.5 MB) [18%]",
    "Get:7 http://archive.ubuntu.com noble/main amd64 nautilus (2.3 MB) [22%]",
    "Get:8 http://archive.ubuntu.com noble/main amd64 gvfs-backends (1.1 MB) [25%]",
    "Get:9 http://archive.ubuntu.com noble/main amd64 pipewire (3.6 MB) [30%]",
    "Get:10 http://archive.ubuntu.com noble/main amd64 wireplumber (0.9 MB) [33%]",
    "Get:11 http://archive.ubuntu.com noble/main amd64 bluez (5.2 MB) [38%]",
    "Get:12 http://archive.ubuntu.com noble/main amd64 flatpak (6.8 MB) [45%]",
    "Get:13 http://archive.ubuntu.com noble/main amd64 fonts-powerline (0.3 MB) [47%]",
    "Get:14 http://archive.ubuntu.com noble/main amd64 tlp (1.8 MB) [50%]",
    "Get:15 http://archive.ubuntu.com noble/main amd64 neovim (4.2 MB) [55%]",
    "Get:16 http://archive.ubuntu.com noble/main amd64 tmux (0.8 MB) [58%]",
    "Get:17 http://archive.ubuntu.com noble/main amd64 fastfetch (0.4 MB) [60%]",
    "Get:18 http://archive.ubuntu.com noble/main amd64 ufw (0.7 MB) [63%]",
    "Get:19 http://archive.ubuntu.com noble/main amd64 ubuntu-restricted-extras (2.9 MB) [68%]",
    "Get:20 http://archive.ubuntu.com noble/main amd64 ffmpegthumbnailer (1.1 MB) [72%]",
    "Fetched 45.8 MB in 12s (3.8 MB/s)",
    "",
    "Extrayendo plantillas de los paquetes... 100%",
    "",
    "(Leyendo la base de datos... 1%",
    "Extrayendo libwayland-client0 (1/77)...",
    "Extrayendo libwayland-server0 (2/77)...",
    "Extrayendo libegl1 (3/77)...",
    "Extrayendo libgl1-mesa-dri (4/77)...",
    "Extrayendo mesa-vulkan-drivers (5/77)...",
    "Extrayendo xwayland (6/77)...",
    "Extrayendo nautilus (7/77)...",
    "Extrayendo gvfs-backends (8/77)...",
    "Extrayendo pipewire (9/77)...",
    "Extrayendo wireplumber (10/77)...",
    "Extrayendo flatpak (11/77)...",
    "Extrayendo neovim (12/77)...",
    "Extrayendo tmux (13/77)...",
    "Extrayendo fastfetch (14/77)...",
    "Extrayendo ufw (15/77)...",
    "Extrayendo ubuntu-restricted-extras (16/77)...",
    "",
    "Configurando libwayland-client0 (17/77)...",
    "Configurando libwayland-server0 (18/77)...",
    "Configurando libegl1 (19/77)...",
    "Configurando libgl1-mesa-dri (20/77)...",
    "Configurando mesa-vulkan-drivers (21/77)...",
    "Configurando xwayland (22/77)...",
    "Configurando nautilus (23/77)...",
    "Configurando pipewire (24/77)...",
    "Configurando wireplumber (25/77)...",
    "Configurando flatpak (26/77)...",
    "Configurando neovim (27/77)...",
    "Configurando ufw (28/77)...",
    "Configurando ubuntu-restricted-extras (29/77)...",
    "",
    "Procesando disparadores para libc-bin (2.31-0ubuntu9)...",
    "Procesando disparadores for man-db (2.9.4-2)...",
    "",
    "nala install correcto",
]

FLATPAK_OUTPUT_SIMULATION = [
    "Looking for matches...",
    "Starting download of 1 item (45.2 MB)",
    "Downloading: org.gnome.Papers (45%)",
    "Downloading: org.gnome.Papers (78%)",
    "Downloading: org.gnome.Papers (100%)",
    "Starting to install...",
    "Installing: org.gnome.Papers (1/3)",
    "Installing: net.nokyan.Resources (2/3)",
    "Installing: org.gnome.Showtime (3/3)",
    "Installation complete.",
]

SUMMARY_LINES = [
    "+ Kernel: XanMod Edge",
    "+ Wayland + Nautilus + PipeWire",
    "+ Flatpak con Flathub + Apps",
    "+ Oh My Zsh + tema agnoster",
    "+ Iconos: Colloid catppuccin green",
    "+ Temas: Plymouth + GRUB Vimix",
    "+ Firewall: UFW activo",
    "+ TLP configurado para laptops",
]


# ── App Demo ──

class DemoApp:
    """Demo de la interfaz VoidForge."""

    def __init__(self):
        self.loop = None
        self.progress = None
        self.spinner_handle = None
        self.simulator_handle = None

    def run(self):
        self.loop = urwid.MainLoop(
            urwid.SolidFill(" "),
            palette=PALETTE,
            unhandled_input=self._unhandled_key,
        )
        self._show_menu()
        self.loop.run()

    def _unhandled_key(self, key):
        if key in ("q", "Q", "esc"):
            raise urwid.ExitMainLoop()

    def _show_menu(self):
        menu = MainMenu(on_choice=self._on_choice)
        self._set_widget(menu.get_widget())

    def _set_widget(self, widget):
        if self.loop:
            self.loop.widget = widget

    def _on_choice(self, key):
        if key == "1":
            self._simulate_all_steps()
        elif key == "3":
            self._simulate_flatpak()
        elif key == "6":
            raise urwid.ExitMainLoop()
        else:
            self._show_message(
                "Demo disponible:\n  [1] Instalacion completa\n  [3] Flatpak install\n  [6] Salir",
                "Info"
            )

    # ── Simulacion de pasos ──

    def _simulate_all_steps(self):
        self._run_simulated_step(0, 2, "Preparando entorno...",
            ["Installing nala", "Installing git", "Installing curl"],
            delay=0.3, total=15)

    def _simulate_flatpak(self):
        self._show_progress(8, 15, "Configurando Flatpak")
        self._feed_lines_slowly(FLATPAK_OUTPUT_SIMULATION, 0.2, callback=lambda: self._show_result(True))

    def _run_simulated_step(self, step, duration, title, lines, delay=0.2, total=15):
        self._show_progress(step, total, title)
        self._feed_lines_slowly(lines, delay, callback=lambda: self._step_done(step))

    def _show_progress(self, num, total, title):
        self.progress = ProgressScreen(num, total, title)
        self._set_widget(self.progress.get_widget())
        self.progress.show_command("Simulando...")
        self.spinner_handle = self.loop.set_alarm_in(0.15, self._tick_spinner)

    def _tick_spinner(self, loop, data):
        if self.progress:
            self.progress.update_spinner()
        self.spinner_handle = self.loop.set_alarm_in(0.15, self._tick_spinner)

    def _feed_lines_slowly(self, lines, delay, callback=None):
        self._line_index = 0
        self._sim_lines = lines
        self._sim_callback = callback
        self._sim_delay = delay
        self._feed_next_line()

    def _feed_next_line(self, loop=None, data=None):
        if self._line_index >= len(self._sim_lines):
            if self._sim_callback:
                self._sim_callback()
            return
        line = self._sim_lines[self._line_index]
        self._line_index += 1
        if self.progress:
            self.progress.feed_line(line)
        self.simulator_handle = self.loop.set_alarm_in(self._sim_delay, self._feed_next_line)

    def _step_done(self, step):
        import random
        ok = random.random() > 0.1
        self.progress.show_result(ok, f"Paso {step} completado")
        if self.spinner_handle:
            try:
                self.loop.remove_alarm(self.spinner_handle)
            except Exception:
                pass
            self.spinner_handle = None
        if step < 4:
            # Simular paso de packages con monitor
            self.loop.set_alarm_in(1.0, lambda l, d: self._simulate_mega_step())
        elif step == 4:
            self.loop.set_alarm_in(1.0, lambda l, d: self._simulate_final_steps())
        else:
            self.loop.set_alarm_in(1.0, lambda l, d: self._show_summary())

    def _simulate_mega_step(self):
        """Simula el paso 4 (mega install) con el monitor de paquetes."""
        self._show_progress(4, 15, "Instalando paquetes del sistema")
        self.progress.use_package_monitor()
        self.progress.show_command("nala install paquetes...")
        self._feed_lines_slowly(NALA_OUTPUT_SIMULATION, 0.08, callback=lambda: self._step_done(4))

    def _simulate_final_steps(self):
        """Simula pasos rapidos 5-14."""
        steps = [
            (5, "Configurando polkit automontaje"),
            (6, "Configurando xdg-user-dirs y UFW"),
            (7, "Configurando red"),
            (8, "Configurando Flatpak"),
            (9, "Habilitando servicios"),
            (10, "Configurando TLP"),
            (11, "Configurando Oh My Zsh"),
            (12, "Instalando LazyVim"),
            (13, "Instalando Colloid icons"),
            (14, "Configurando Plymouth y GRUB"),
        ]
        self._sim_remaining_steps = steps
        self._sim_remaining_idx = 0
        self._run_next_remaining()

    def _run_next_remaining(self):
        if self._sim_remaining_idx >= len(self._sim_remaining_steps):
            self._show_summary()
            return
        num, title = self._sim_remaining_steps[self._sim_remaining_idx]
        self._sim_remaining_idx += 1
        self._show_progress(num, 15, title)
        lines = [f"Configurando {title.split(':')[1].strip()}...", "Hecho."]
        delay = 0.15 if num != 8 else 0.3
        self.progress.use_package_monitor() if num == 8 else None
        lines = NALA_OUTPUT_SIMULATION[:8] + NALA_OUTPUT_SIMULATION[-3:] if num == 8 else lines
        self._feed_lines_slowly(lines, delay, callback=self._run_next_remaining)

    def _show_summary(self):
        if self.spinner_handle:
            try:
                self.loop.remove_alarm(self.spinner_handle)
            except Exception:
                pass
            self.spinner_handle = None
        msg = "Instalacion completada!\n\n"
        for line in SUMMARY_LINES:
            msg += f"  {line}\n"
        msg += f"\nLog: /tmp/voidforge.log"
        self._show_message(msg, "VoidForge - Listo!")

    def _show_message(self, text, title="VoidForge"):
        def close():
            self._show_menu()
        dialog = message_dialog(title, text, close)
        overlay = urwid.Overlay(
            dialog,
            self.loop.widget if self.loop else urwid.SolidFill(" "),
            align="center", width=("relative", 60),
            valign="middle", height=("relative", 50),
        )
        self._set_widget(overlay)

    def _show_result(self, ok):
        self.progress.show_result(ok, "Completado")
        self.loop.set_alarm_in(1.5, lambda l, d: self._show_menu())


if __name__ == "__main__":
    print("VoidForge UI Demo - Presiona Q o ESC para salir")
    print("Selecciona [1] para instalacion simulada con monitor de paquetes")
    time.sleep(2)
    DemoApp().run()
