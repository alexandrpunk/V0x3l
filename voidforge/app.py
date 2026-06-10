# VoidForge App - urwid event loop y logica principal

import urwid
from voidforge.config import PALETTE, TOTAL_STEPS, VERSION, LOG_FILE
from voidforge.shell import run, log
from voidforge.runner import StepRunner
from voidforge.ui.menu import MainMenu
from voidforge.ui.progress import ProgressScreen
from voidforge.ui.execution_screen import ExecutionScreen
from voidforge.ui.layout import VoidForgeLayout
from voidforge.ui.dialogs import message_dialog
from voidforge.ui.banner import get_banner_text


class VoidForgeApp:
    """Aplicacion principal con event loop urwid."""

    def __init__(self):
        self.loop = None
        self.layout = VoidForgeLayout()
        self.exec_screen: ExecutionScreen | None = None
        self.runner = StepRunner(self, self)
        self._register_steps()
        self.current_progress: ProgressScreen | None = None
        self.spinner_handle = None

    # ===================== Shell callbacks =====================

    def run_cmd(self, desc: str, *args, sudo=False, timeout=None) -> bool:
        def on_line(line: str):
            if self.current_progress:
                self.current_progress.feed_line(line)
        return run(desc, *args, sudo=sudo, on_line=on_line, timeout=timeout)

    # ===================== UI =====================

    def run(self):
        import asyncio
        event_loop = None
        try:
            event_loop = urwid.AsyncioEventLoop(loop=asyncio.new_event_loop())
        except Exception:
            try:
                event_loop = urwid.SelectEventLoop()
            except Exception:
                event_loop = None

        kwargs = {
            "widget": self.layout.get_widget(),
            "palette": PALETTE,
            "unhandled_input": self._unhandled_key,
        }
        if event_loop:
            kwargs["event_loop"] = event_loop
        else:
            print("  [WARN] No se pudo crear event loop, usando default")
            import sys
            sys.stdout.flush()

        self.loop = urwid.MainLoop(**kwargs)
        self._show_menu()
        try:
            self.loop.run()
        except urwid.ExitMainLoop:
            raise
        except Exception as e:
            print(f"\n  [ERR] Error en la interfaz: {e}")
            raise

    def _unhandled_key(self, key):
        if key in ("q", "Q"):
            raise urwid.ExitMainLoop()

    def _show_menu(self):
        menu = MainMenu(on_choice=self._on_menu_choice)
        self.layout.show_menu(menu.get_widget())

    def _on_menu_choice(self, key: str):
        actions = {
            "1": self._run_all,
            "2": self._run_resume,
            "3": lambda: self._show_message("Proximamente.", "Paso especifico"),
            "4": lambda: self._show_message("Proximamente.", "Rango de pasos"),
            "5": self._show_status,
            "6": lambda: exit_app(self.loop),
        }
        action = actions.get(key)
        if action:
            action()

    def _run_all(self):
        self._prepare_execution()
        self.runner.run_all(resume=False)

    def _run_resume(self):
        self._prepare_execution()
        self.runner.run_all(resume=True)

    def _prepare_execution(self):
        """Prepara la pantalla de ejecucion con los pasos."""
        self.exec_screen = ExecutionScreen()
        # Marcar todos como pending
        for i in range(TOTAL_STEPS + 1):
            self.exec_screen.set_step_status(i, "pending")
        self.layout.show_execution(self.exec_screen.get_widget())

    def _show_status(self):
        status = self.runner.get_checkpoint_status()
        msg = (f"  {status}\n\n"
               f"  Log: {LOG_FILE}\n"
               f"  Version: {VERSION}\n"
               f"  Pasos: {TOTAL_STEPS}")
        self._show_message(msg, "Estado actual")

    def _show_message(self, text: str, title: str = "VoidForge"):
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

    # ===================== Ejecucion de steps =====================

    def run_step(self, step) -> bool:
        """Ejecuta un step con UI de progreso en split panel."""
        # Marcar paso como running en el panel izquierdo
        if self.exec_screen:
            self.exec_screen.set_step_status(step.number, "running")

        # Crear progress screen y ponerlo en el panel derecho
        self.current_progress = ProgressScreen(
            step.number, TOTAL_STEPS, step.title
        )
        if self.exec_screen:
            self.exec_screen.set_output(self.current_progress.get_widget())

        self.layout.set_header(f"Paso {step.number}/{TOTAL_STEPS} - {step.title}")

        # Iniciar animacion spinner
        self.spinner_handle = self.loop.set_alarm_in(
            0.15, self._tick_spinner
        ) if self.loop else None

        log(f"=== Paso {step.number}/{TOTAL_STEPS}: {step.title} ===")

        ok = step.run()

        # Detener spinner
        if self.spinner_handle and self.loop:
            try:
                self.loop.remove_alarm(self.spinner_handle)
            except Exception:
                pass
            self.spinner_handle = None

        # Actualizar estado del paso
        status = "done" if ok else "failed"
        if self.exec_screen:
            self.exec_screen.set_step_status(step.number, status)

        self.layout.show_result(ok, f"Paso {step.number}")

        if ok:
            self.runner.save_checkpoint(step.number)
            log(f"OK: Paso {step.number} - {step.title}")
        else:
            log(f"FAIL: Paso {step.number} - {step.title}")

        self.current_progress = None
        return ok

    def on_all_done(self):
        """Called when all steps complete."""
        if self.loop:
            self.loop.set_alarm_in(1.5, lambda loop, data: self._show_menu())

    def _tick_spinner(self, loop, data):
        if self.current_progress:
            self.current_progress.update_spinner()
        self.spinner_handle = loop.set_alarm_in(0.15, self._tick_spinner)

    # ===================== Registro de steps =====================

    def _register_steps(self):
        from voidforge.steps.core import BootstrapStep, SystemPrepStep
        from voidforge.steps.drivers import KernelStep, GPUStep
        from voidforge.steps.packages import MegaInstallStep, FlatpakStep, ShellStep, EditorStep
        from voidforge.steps.system import PolkitStep, XdgUfwStep, NetworkStep, ServicesStep, TLPStep
        from voidforge.steps.theming import IconsStep, BootThemeStep
        from voidforge.steps.final import DMSStep

        all_steps = [
            BootstrapStep, SystemPrepStep,
            KernelStep, GPUStep,
            MegaInstallStep, FlatpakStep, ShellStep, EditorStep,
            PolkitStep, XdgUfwStep, NetworkStep, ServicesStep, TLPStep,
            IconsStep, BootThemeStep,
            DMSStep,
        ]

        for step_cls in all_steps:
            step = step_cls(self.runner)
            self.runner.register_step(step)


def exit_app(loop=None):
    raise urwid.ExitMainLoop()
