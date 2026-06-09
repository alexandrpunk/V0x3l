#!/usr/bin/env python3
# VoidForge UI Demo
# Uso: python3 demo_ui.py

import sys
import os
import time
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["LOG_FILE"] = "/dev/null"

import urwid
from voidforge.config import PALETTE, VERSION, TOTAL_STEPS
from voidforge.ui.menu import MainMenu
from voidforge.ui.progress import ProgressScreen
from voidforge.ui.execution_screen import ExecutionScreen
from voidforge.ui.layout import VoidForgeLayout
from voidforge.ui.steps_list import StepsList
from voidforge.ui.dialogs import message_dialog
from voidforge.ui.banner import get_banner_text


NALA_OUTPUT_SIMULATION = [
    "Leyendo lista de paquetes... Hecho",
    "Creando arbol de dependencias... Hecho",
    "Descargando...",
    "Get:1 libwayland-client0 (0.8 MB) [1%]",
    "Get:2 libegl1 (0.2 MB) [5%]",
    "Get:3 libgl1-mesa-dri (8.2 MB) [10%]",
    "Get:4 xwayland (1.5 MB) [18%]",
    "Get:5 nautilus (2.3 MB) [22%]",
    "Get:6 pipewire (3.6 MB) [30%]",
    "Get:7 bluez (5.2 MB) [38%]",
    "Get:8 flatpak (6.8 MB) [45%]",
    "Get:9 neovim (4.2 MB) [55%]",
    "Fetched 45.8 MB in 12s (3.8 MB/s)", "",
    "Extrayendo paquetes... 100%", "",
    "Extrayendo libwayland-client0 (1/30)...",
    "Extrayendo pipewire (9/30)...",
    "Extrayendo flatpak (11/30)...",
    "Configurando libwayland (17/30)...",
    "Configurando pipewire (24/30)...",
    "Configurando flatpak (26/30)...",
    "Procesando disparadores...",
    "nala install correcto",
]

SUMMARY_LINES = [
    "+ Kernel: XanMod Edge",
    "+ Wayland + Nautilus + PipeWire",
    "+ Flatpak + Oh My Zsh + LazyVim",
    "+ Plymouth + GRUB Vimix",
    "+ TLP + UFW configurados",
]


class DemoApp:
    def __init__(self):
        self.loop = None
        self.layout = VoidForgeLayout()
        self.exec_screen: ExecutionScreen | None = None
        self.progress = None
        self.spinner_handle = None
        self.simulator_handle = None

    def run(self):
        import asyncio
        try:
            ev = urwid.AsyncioEventLoop(loop=asyncio.new_event_loop())
        except Exception:
            ev = None

        banner_text = get_banner_text()
        self.layout.set_body(
            urwid.Pile([urwid.Text(banner_text, align="center")])
        )
        kwargs = {
            "widget": self.layout.get_widget(),
            "palette": PALETTE,
            "unhandled_input": self._unhandled_key,
        }
        if ev:
            kwargs["event_loop"] = ev
        self.loop = urwid.MainLoop(**kwargs)
        self._show_menu()
        self.loop.run()

    def _unhandled_key(self, key):
        if key in ("q", "Q", "esc"):
            raise urwid.ExitMainLoop()

    def _show_menu(self):
        menu = MainMenu(on_choice=self._on_choice)
        self.layout.show_menu(menu.get_widget())

    def _on_choice(self, key):
        if key == "1":
            self._simulate_all()
        elif key == "3":
            self._simulate_flatpak()
        elif key == "6":
            raise urwid.ExitMainLoop()
        else:
            self._show_msg(
                "Demo:\n  [1] Completa\n  [3] Flatpak\n  [6] Salir",
                "Info"
            )

    # ── Simulacion ──

    def _simulate_all(self):
        self.exec_screen = ExecutionScreen()
        for i in range(TOTAL_STEPS + 1):
            self.exec_screen.set_step_status(i, "pending")
        self.layout.show_execution(self.exec_screen.get_widget())

        # Simular steps rapidos
        steps_data = StepsList.default_titles()
        for num in range(TOTAL_STEPS + 1):
            self._simulate_step(num, steps_data[num])

        self.layout.show_result(True, "Instalacion completada")
        self.loop.set_alarm_in(2.0, lambda l, d: self._show_summary())

    def _simulate_step(self, num: int, title: str):
        self.exec_screen.set_step_status(num, "running")
        self.layout.set_header(f"Paso {num}/{TOTAL_STEPS} - {title}")

        self.progress = ProgressScreen(num, TOTAL_STEPS, title)
        self.exec_screen.set_output(self.progress.get_widget())
        self.spinner_handle = self.loop.set_alarm_in(0.1, self._tick_spinner)
        self.loop.draw_screen()

        # Simular output
        if num == 4:
            self.progress.use_package_monitor()
            for line in NALA_OUTPUT_SIMULATION:
                self.progress.feed_line(line)
                time.sleep(0.04)
        elif num == 8:
            self.progress.use_package_monitor()
            for line in NALA_OUTPUT_SIMULATION[:6] + ["Install complete."]:
                self.progress.feed_line(line)
                time.sleep(0.05)
        else:
            for line in [f"Ejecutando {title}...", "Hecho."]:
                self.progress.feed_line(line)
                time.sleep(0.1)

        if self.spinner_handle:
            try:
                self.loop.remove_alarm(self.spinner_handle)
            except Exception:
                pass
            self.spinner_handle = None

        ok = random.random() > 0.05
        self.progress.show_result(ok, f"Paso {num}")
        self.exec_screen.set_step_status(num, "done" if ok else "failed")
        self.layout.show_result(ok, f"Paso {num}")
        self.loop.draw_screen()
        time.sleep(0.2)

    def _simulate_flatpak(self):
        self.exec_screen = ExecutionScreen()
        self.layout.show_execution(self.exec_screen.get_widget())
        num, title = 8, "Flatpak + apps"
        self.exec_screen.set_step_status(num, "running")
        self.layout.set_header(f"Paso {num}/{TOTAL_STEPS} - {title}")

        self.progress = ProgressScreen(num, TOTAL_STEPS, title)
        self.progress.use_package_monitor()
        self.exec_screen.set_output(self.progress.get_widget())
        self.spinner_handle = self.loop.set_alarm_in(0.1, self._tick_spinner)

        flatpak_lines = [
            "Looking for matches...",
            "Downloading: org.gnome.Papers (45%)",
            "Downloading: org.gnome.Papers (78%)",
            "Downloading: org.gnome.Papers (100%)",
            "Installing: org.gnome.Papers (1/3)",
            "Installing: net.nokyan.Resources (2/3)",
            "Installing: org.gnome.Showtime (3/3)",
            "Install complete.",
        ]
        for line in flatpak_lines:
            self.progress.feed_line(line)
            time.sleep(0.15)
            self.loop.draw_screen()

        if self.spinner_handle:
            try:
                self.loop.remove_alarm(self.spinner_handle)
            except Exception:
                pass
            self.spinner_handle = None

        self.progress.show_result(True, "Flatpak completado")
        self.exec_screen.set_step_status(num, "done")
        self.layout.show_result(True, "Flatpak")
        self.loop.draw_screen()
        time.sleep(1)
        self._show_menu()

    def _tick_spinner(self, loop, data):
        if self.progress:
            self.progress.update_spinner()
        self.spinner_handle = loop.set_alarm_in(0.1, self._tick_spinner)

    def _show_summary(self):
        msg = "Instalacion completada!\n\n"
        for line in SUMMARY_LINES:
            msg += f"  {line}\n"
        msg += f"\n  Log: /tmp/voidforge.log"
        self._show_msg(msg, "VoidForge - Listo!")

    def _show_msg(self, text, title="VoidForge"):
        def close():
            self._show_menu()
        dialog = message_dialog(title, text, close)
        overlay = urwid.Overlay(
            dialog,
            urwid.SolidFill(" "),
            align="center", width=("relative", 60),
            valign="middle", height=("relative", 55),
        )
        self.layout.set_body(overlay)


if __name__ == "__main__":
    print("VoidForge Demo - Interfaz con split panel")
    print("[1] Demo completa | [6] Salir")
    time.sleep(1.5)
    DemoApp().run()
