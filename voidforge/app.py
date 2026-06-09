# VoidForge App - urwid event loop y logica principal

import urwid
from voidforge.config import PALETTE, TOTAL_STEPS, VERSION, LOG_FILE
from voidforge.shell import run, log
from voidforge.runner import StepRunner
from voidforge.ui.menu import MainMenu
from voidforge.ui.progress import ProgressScreen
from voidforge.ui.layout import VoidForgeLayout
from voidforge.ui.dialogs import message_dialog
from voidforge.ui.banner import get_banner_text


class VoidForgeApp:
    """Aplicacion principal con event loop urwid."""

    def __init__(self):
        self.loop = None
        self.layout = VoidForgeLayout()
        self.runner = StepRunner(self, self)
        self._register_steps()
        self.current_progress: ProgressScreen | None = None
        self.spinner_handle = None

    # ===================== Shell callbacks =====================

    def run_cmd(self, desc: str, *args, sudo=False, timeout=None) -> bool:
        """Ejecuta un comando, mostrando salida en el progress screen."""
        def on_line(line: str):
            if self.current_progress:
                self.current_progress.feed_line(line)
        return run(desc, *args, sudo=sudo, on_line=on_line, timeout=timeout)

    # ===================== UI =====================

    def run(self):
        """Inicia el event loop de urwid."""
        self.loop = urwid.MainLoop(
            self.layout.get_widget(),
            palette=PALETTE,
            unhandled_input=self._unhandled_key,
        )
        self._show_menu()
        self.loop.run()

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
            "3": lambda: self._show_message(
                "Proximamente.", "Paso especifico"),
            "4": lambda: self._show_message(
                "Proximamente.", "Rango de pasos"),
            "5": self._show_status,
            "6": lambda: exit_app(self.loop),
        }
        action = actions.get(key)
        if action:
            action()

    def _run_all(self):
        self.runner.run_all(resume=False)

    def _run_resume(self):
        self.runner.run_all(resume=True)

    def _show_status(self):
        status = self.runner.get_checkpoint_status()
        msg = (f"  {status}\n\n"
               f"  Log: {LOG_FILE}\n"
               f"  Versión: {VERSION}\n"
               f"  Pasos: {TOTAL_STEPS}")
        self._show_message(msg, "Estado actual")

    def _show_message(self, text: str, title: str = "VoidForge"):
        def close():
            self._show_menu()
        dialog = message_dialog(title, text, close)
        overlay = urwid.Overlay(
            dialog,
            self.layout.get_widget(),
            align="center", width=("relative", 60),
            valign="middle", height=("relative", 55),
        )
        self.layout.set_body(overlay)

    # ===================== Ejecucion de steps =====================

    def run_step(self, step) -> bool:
        """Ejecuta un step con UI de progreso."""
        self.current_progress = ProgressScreen(
            step.number, TOTAL_STEPS, step.title
        )
        self.layout.show_progress(step.number, TOTAL_STEPS, step.title)
        self.layout.set_body(self.current_progress.get_widget())

        # Iniciar animacion del spinner
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

        # Mostrar resultado
        msg = "Completado" if ok else "Fallado"
        if self.current_progress:
            self.current_progress.show_result(ok, msg)
        self.layout.show_result(ok, f"Paso {step.number} - {msg}")

        if ok:
            self.runner.save_checkpoint(step.number)
            log(f"OK: Paso {step.number} - {step.title}")
        else:
            log(f"FAIL: Paso {step.number} - {step.title}")

        # Pausa breve para que el usuario vea el resultado
        if self.loop:
            self.loop.set_alarm_in(1.5, lambda loop, data: self._show_menu())

        self.current_progress = None
        return ok

    def _tick_spinner(self, loop, data):
        if self.current_progress:
            self.current_progress.update_spinner()
        self.spinner_handle = loop.set_alarm_in(0.15, self._tick_spinner)

    # ===================== Registro de steps =====================

    def _register_steps(self):
        """Importa y registra todos los steps."""
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
