# V0x3l App - urwid event loop y logica principal

import os
import sys
import urwid
from v0x3l.config import PALETTE, TOTAL_STEPS, VERSION, LOG_FILE, PROJECT_NAME
from v0x3l.shell import run, log
from v0x3l.runner import StepRunner
from v0x3l.ui.menu import MainMenu
from v0x3l.ui.progress import ProgressScreen
from v0x3l.ui.execution_screen import ExecutionScreen
from v0x3l.ui.layout import V0x3lLayout
from v0x3l.ui.dialogs import message_dialog, error_dialog


class V0x3lApp:
    """Aplicacion principal con event loop urwid."""

    def __init__(self):
        self.loop = None
        self.layout = V0x3lLayout()
        self.exec_screen: ExecutionScreen | None = None
        self.runner = StepRunner(self, self)
        self._register_steps()
        self.current_progress: ProgressScreen | None = None
        self.spinner_handle = None

    # ===================== Shell callbacks =====================

    def run_cmd(self, desc: str, *args, sudo=False, timeout=None, capture_output=True) -> bool:
        def on_line(line: str):
            if self.current_progress:
                self.current_progress.show_command(desc)
                self.current_progress.update_spinner()
                self.current_progress.feed_line(line)
            if self.loop:
                self.loop.draw_screen()
        return run(desc, *args, sudo=sudo, on_line=on_line, timeout=timeout,
                   capture_output=capture_output)

    def run_raw_cmd(self, *args, sudo=False) -> bool:
        """Ejecuta comando con terminal real (libera urwid temporalmente).

        Detiene la pantalla raw de urwid, ejecuta el comando con stdin/stdout
        heredados del terminal, y restaura urwid al terminar.
        """
        import subprocess
        import time
        # Mostrar mensaje antes de liberar el terminal
        if self.current_progress:
            self.current_progress.show_command("Liberando terminal para comando interactivo...")
        if self.loop:
            self.loop.draw_screen()
            time.sleep(0.2)
            self.loop.screen.stop()
        try:
            cmd = list(args)
            if sudo and os.geteuid() != 0:
                cmd = ["sudo"] + cmd
            ret = subprocess.call(cmd)
            return ret == 0
        finally:
            if self.loop:
                self.loop.screen.start()
                # Forzar refresco completo para limpiar residuos del comando
                self.loop.draw_screen()

    # ===================== UI =====================

    def run(self):
        # Sin TTY real (pipe, stdout redirigido) -> modo texto
        if not os.isatty(0):
            self._fallback_text_mode()
            return

        # TTY real -> urwid
        import asyncio
        event_loop = None
        try:
            event_loop = urwid.AsyncioEventLoop(loop=asyncio.new_event_loop())
        except Exception:
            try:
                event_loop = urwid.SelectEventLoop()
            except Exception:
                event_loop = None

        self._show_menu()

        kwargs = {
            "widget": self.layout.get_widget(),
            "palette": PALETTE,
            "unhandled_input": self._unhandled_key,
        }
        if event_loop:
            kwargs["event_loop"] = event_loop

        self.loop = urwid.MainLoop(**kwargs)
        try:
            self.loop.run()
        except (urwid.ExitMainLoop, KeyboardInterrupt):
            return
        except Exception as e:
            print(f"\n  [WARN] urwid no disponible en este terminal: {e}")
            self._fallback_text_mode()

    def _fallback_text_mode(self):
        """Menu de texto ANSI como fallback cuando urwid no funciona."""
        # Si stdin es pipe, leer de /dev/tty
        if not sys.stdin.isatty():
            try:
                sys.stdin = open("/dev/tty", "r")
            except Exception:
                pass
        print()
        while True:
            print(f"\n  {chr(27)}[1;32m{chr(9670)} {PROJECT_NAME}{chr(27)}[0m")
            print(f"  {chr(27)}[2;37m{chr(9472) * 60}{chr(27)}[0m")
            print()
            print(f"  {chr(27)}[1;37m(1){chr(27)}[0m Instalacion completa (pasos 0-5)")
            print(f"  {chr(27)}[1;37m(2){chr(27)}[0m Reanudar desde ultimo checkpoint")
            print(f"  {chr(27)}[1;37m(3){chr(27)}[0m Ejecutar paso especifico")
            print(f"  {chr(27)}[1;37m(4){chr(27)}[0m Ejecutar rango de pasos")
            print(f"  {chr(27)}[1;37m(5){chr(27)}[0m Ver estado actual")
            print(f"  {chr(27)}[1;37m(6){chr(27)}[0m Salir")
            print(f"\n  {chr(27)}[2;37mSelecciona una opcion [1-6]:{chr(27)}[0m")
            try:
                choice = input().strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if choice == "1":
                self._run_all()
            elif choice == "2":
                self._run_resume()
            elif choice == "3":
                self._run_specific()
            elif choice == "4":
                self._run_range()
            elif choice == "5":
                self._show_status()
            elif choice == "6":
                break
            else:
                print("  Opcion no valida")


    def _unhandled_key(self, key):
        # Atajos numericos directos sin navegar con flechas
        if key in ("1", "2", "3", "4", "5", "6"):
            self._on_menu_choice(key)
            return
        if key in ("q", "Q"):
            raise urwid.ExitMainLoop()

    def _show_menu(self):
        menu = MainMenu(on_choice=self._on_menu_choice)
        self.layout.show_menu(menu.get_widget())

    def _on_menu_choice(self, key: str):
        actions = {
            "1": self._run_all,
            "2": self._run_resume,
            "3": self._run_specific,
            "4": self._run_range,
            "5": self._show_status,
            "6": lambda: exit_app(self.loop),
        }
        action = actions.get(key)
        if action:
            action()

    def _run_all(self):
        self._prepare_execution()
        ok, failed_step = self.runner.run_all(resume=False)
        if not ok and failed_step is not None:
            self._show_error(failed_step)

    def _run_resume(self):
        self._prepare_execution()
        ok, failed_step = self.runner.run_all(resume=True)
        if not ok and failed_step is not None:
            self._show_error(failed_step)

    def _run_specific(self):
        step_num = input("  Numero de paso (0-5): ").strip()
        try:
            num = int(step_num)
            self._prepare_execution()
            self.runner.run_single(num)
        except ValueError:
            print("  Numero invalido")

    def _run_range(self):
        rng = input("  Rango (ej: 5-10): ").strip()
        try:
            start, end = rng.split("-")
            self._prepare_execution()
            self.runner.run_range(int(start.strip()), int(end.strip()))
        except (ValueError, IndexError):
            print("  Rango invalido. Usa formato: 5-10")

    def _prepare_execution(self):
        """Prepara la pantalla de ejecucion con los pasos."""
        self.exec_screen = ExecutionScreen()
        # Marcar todos como pending
        for i in range(TOTAL_STEPS + 1):
            self.exec_screen.set_step_status(i, "pending")
        self.layout.show_execution(self.exec_screen.get_widget())
        if self.loop:
            self.loop.draw_screen()

    def _show_status(self):
        status = self.runner.get_checkpoint_status()
        msg = (f"  {status}\n\n"
               f"  Log: {LOG_FILE}\n"
               f"  Version: {VERSION}\n"
               f"  Pasos: {TOTAL_STEPS}")
        self._show_message(msg, "Estado actual")

    def _show_message(self, text: str, title: str = None):
        if title is None:
            title = PROJECT_NAME
        def close():
            self._show_menu()
            if self.loop:
                self.loop.draw_screen()
        dialog = message_dialog(title, text, close)
        overlay = urwid.Overlay(
            dialog,
            urwid.SolidFill(" "),
            align="center", width=("relative", 60),
            valign="middle", height=("relative", 55),
        )
        self.layout.set_body(overlay)
        if self.loop:
            self.loop.draw_screen()

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
        self.current_progress.show_command("Preparando...")
        if self.exec_screen:
            self.exec_screen.set_output(self.current_progress.get_widget())

        self.layout.set_header(f"\u25B6 {step.title}  \u2502  Paso {step.number}/{TOTAL_STEPS}")

        # Iniciar animacion spinner
        self.spinner_handle = self.loop.set_alarm_in(
            0.15, self._tick_spinner
        ) if self.loop else None

        # Forzar render de la pantalla de progreso antes del comando bloqueante
        if self.loop:
            self.loop.draw_screen()

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

        # Forzar render del resultado del paso
        if self.loop:
            self.loop.draw_screen()

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
            self.loop.draw_screen()
            self.loop.set_alarm_in(1.5, lambda loop, data: self._show_menu())

    def _tick_spinner(self, loop, data):
        if self.current_progress:
            self.current_progress.update_spinner()
        self.spinner_handle = loop.set_alarm_in(0.15, self._tick_spinner)

    def _show_error(self, failed_step: int):
        """Muestra dialogo de error cuando un paso falla."""
        import shutil
        from v0x3l.config import LOG_FILE

        # Copiar log al home del usuario
        user = os.environ.get("SUDO_USER", os.environ.get("USER", ""))
        home_dir = f"/home/{user}" if user and os.path.exists(f"/home/{user}") else os.path.expanduser("~")
        log_dest = f"{home_dir}/v0x3l-error.log"

        try:
            shutil.copy(LOG_FILE, log_dest)
        except Exception:
            log_dest = LOG_FILE

        msg = (f"\n  Error en paso {failed_step}\n\n"
               f"  Se detuvo la instalacion debido a un fallo.\n\n"
               f"  Revisa el log para mas detalles.")

        def close():
            self._show_menu()
            if self.loop:
                self.loop.draw_screen()

        dialog = error_dialog("Error de instalacion", msg, log_dest, close)
        overlay = urwid.Overlay(
            dialog,
            urwid.SolidFill(" "),
            align="center", width=("relative", 60),
            valign="middle", height=("relative", 40),
        )
        self.layout.set_body(overlay)
        if self.loop:
            self.loop.draw_screen()

    # ===================== Registro de steps =====================

    def _register_steps(self):
        from v0x3l.steps.core import PreparationStep
        from v0x3l.steps.drivers import PerformanceStep
        from v0x3l.steps.packages import SoftwareStep
        from v0x3l.steps.system import ConfigurationStep
        from v0x3l.steps.theming import AppearanceStep
        from v0x3l.steps.final import DesktopStep

        all_steps = [
            PreparationStep,
            PerformanceStep,
            SoftwareStep,
            ConfigurationStep,
            AppearanceStep,
            DesktopStep,
        ]

        for step_cls in all_steps:
            step = step_cls(self.runner)
            self.runner.register_step(step)


def exit_app(loop=None):
    raise urwid.ExitMainLoop()
