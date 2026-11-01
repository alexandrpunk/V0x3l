# V0x3l App - urwid event loop y logica principal

import os
import shutil
import sys
import urwid
from v0x3l.config import PALETTE, TOTAL_STEPS, VERSION, LOG_FILE, PROJECT_NAME, TARGET_HOME
from v0x3l.shell import run, log
from v0x3l.runner import StepRunner
from v0x3l.ui.menu import MainMenu
from v0x3l.ui.progress import ProgressScreen
from v0x3l.ui.execution_screen import ExecutionScreen
from v0x3l.ui.layout import V0x3lLayout
from v0x3l.ui.dialogs import (message_dialog, error_dialog, report_dialog,
                              success_dialog, confirm_dialog)


class V0x3lApp:
    """Aplicacion principal con event loop urwid."""

    def __init__(self):
        self.loop = None
        self.layout = V0x3lLayout()
        self.exec_screen: ExecutionScreen | None = None
        self.runner = StepRunner(self, self)
        self._register_steps()
        self.current_progress: ProgressScreen | None = None
        self._modal = False
        self._success = False
        self._report_open = False

    # ===================== Shell callbacks =====================

    def run_cmd(self, desc: str, *args, sudo=False, timeout=None, capture_output=True) -> bool:
        # Default 30 min: previene hangs infinitos (mirror caido, DNS, etc.)
        # sin cortar installs grandes legitimos.
        if timeout is None:
            timeout = 1800
        def on_line(line: str):
            if self.current_progress:
                self.current_progress.show_command(desc)
                self.current_progress.feed_line(line)
        def on_tick():
            if self.current_progress:
                self.current_progress.update_spinner()
            if self.loop:
                # refrescar screen_size (resiste garble por resize durante el bloqueo)
                self.loop.screen_size = self.loop.screen.get_cols_rows()
                self.loop.draw_screen()
        return run(desc, *args, sudo=sudo, on_line=on_line, on_tick=on_tick,
                   timeout=timeout, capture_output=capture_output)

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
            except OSError:
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
            print(f"  {chr(27)}[1;37m(6){chr(27)}[0m Comprobar la instalacion")
            print(f"  {chr(27)}[1;37m(7){chr(27)}[0m Salir")
            print(f"\n  {chr(27)}[2;37mSelecciona una opcion [1-7]:{chr(27)}[0m")
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
                self._run_checks()
            elif choice == "7":
                break
            else:
                print("  Opcion no valida")


    def _unhandled_key(self, key):
        # Pantalla de exito: solo R (reiniciar) y S/Q (salir)
        if self._success:
            if key in ("r", "R"):
                self._on_reboot_pressed()
            elif key in ("s", "S", "q", "Q"):
                raise urwid.ExitMainLoop()
            return
        # Informe del doctor: se cierra con q o Esc
        if self._report_open:
            if key in ("q", "Q", "esc", "escape"):
                self._show_menu()
            return
        # Con un dialogo abierto solo actuan sus botones
        if self._modal:
            return
        # Atajos numericos directos sin navegar con flechas
        if key in ("1", "2", "3", "4", "5", "6", "7"):
            self._on_menu_choice(key)
            return
        if key in ("q", "Q"):
            raise urwid.ExitMainLoop()

    def _show_menu(self):
        self._modal = False
        self._success = False
        self._report_open = False
        menu = MainMenu(on_choice=self._on_menu_choice)
        self.layout.show_menu(menu.get_widget())

    def _on_menu_choice(self, key: str):
        actions = {
            "1": self._run_all,
            "2": self._run_resume,
            "3": self._run_specific,
            "4": self._run_range,
            "5": self._show_status,
            "6": self._run_checks,
            "7": lambda: exit_app(self.loop),
        }
        action = actions.get(key)
        if action:
            action()

    def _run_checks(self):
        """Comprobacion de la instalacion (utilidad del doctor)."""
        from v0x3l.doctor import format_report, run_checks, summarize

        checks = run_checks()
        ok, warn, fail = summarize(checks)
        log(f"CHECK: {len(checks)} comprobaciones - "
            f"{ok} ok, {warn} avisos, {fail} fallos")
        report = format_report(checks)
        if self.loop:
            self._show_report("Comprobacion de la instalacion", report)
        else:
            print("\n" + report + "\n")

    def _show_report(self, title: str, text: str):
        """Muestra un informe largo con scroll."""
        self._modal = True
        self._report_open = True
        self.layout.set_header(title)
        self.layout.set_footer("flechas para desplazar \u2502 Cerrar")
        self.layout.set_body(urwid.Overlay(
            report_dialog(title, text, self._show_menu),
            urwid.SolidFill(" "),
            align="center", width=("relative", 80),
            valign="middle", height=("relative", 85),
        ))
        if self.loop:
            self.loop.draw_screen()

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
        self._modal = False
        self._success = False
        self._report_open = False
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
        self._modal = True

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

        # Forzar render de la pantalla de progreso antes del comando bloqueante
        if self.loop:
            self.loop.draw_screen()

        log(f"=== Paso {step.number}/{TOTAL_STEPS}: {step.title} ===")

        try:
            ok = step.run()
        except Exception as e:
            log(f"EXCEPCION no controlada en paso {step.number} ({step.title}): {e}")
            status = "failed"
            if self.exec_screen:
                self.exec_screen.set_step_status(step.number, status)
            self.layout.show_result(False, f"Paso {step.number}")
            if self.loop:
                self.loop.draw_screen()
            log(f"FAIL: Paso {step.number} - {step.title}")
            self.current_progress = None
            return False

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
            log(f"FAIL: Paso {step.number} - {step.title} | ver LOG_FILE={LOG_FILE} para CMD/RESULT previos")

        self.current_progress = None
        return ok

    def on_all_done(self):
        """Todos los pasos completados: pantalla de exito con opcion de reiniciar."""
        log("OK: instalacion completada (todos los pasos)")
        if not self.loop:
            self._text_success()
            return
        self.loop.draw_screen()
        self.loop.set_alarm_in(0.5, lambda loop, data: self._show_success())

    def _show_success(self):
        """Pantalla de exito tras completar todos los pasos."""
        self._success = True
        self._modal = True
        self.layout.set_header("Instalacion completada")
        self.layout.set_footer("R Reiniciar \u2502 S Salir")
        msg = ("\n  Todos los pasos se completaron correctamente.\n\n"
               "  Reinicia para aplicar kernel, drivers, grupos y sesion grafica.\n")
        dialog = success_dialog(
            "Instalacion completada", msg,
            on_reboot=self._on_reboot_pressed,
            on_exit=lambda: exit_app(self.loop),
            log_path=LOG_FILE,
        )
        self.layout.set_body(urwid.Overlay(
            dialog, urwid.SolidFill(" "),
            align="center", width=("relative", 70),
            valign="middle", height=("relative", 55),
        ))
        if self.loop:
            self.loop.draw_screen()

    def _on_reboot_pressed(self):
        """Pide confirmacion antes de reiniciar el sistema."""
        def do_reboot():
            if self._reboot_system():
                raise urwid.ExitMainLoop()
            self._show_message(
                "\n  No se pudo reiniciar automaticamente.\n\n"
                "  Ejecuta manualmente:  sudo reboot\n",
                "Reinicio no disponible")

        dialog = confirm_dialog(
            "Reiniciar sistema",
            "\u00bfReiniciar el sistema ahora?\n  La instalacion ya termino.",
            on_yes=do_reboot, on_no=self._show_success)
        self.layout.set_body(urwid.Overlay(
            dialog, urwid.SolidFill(" "),
            align="center", width=("relative", 56),
            valign="middle", height=("relative", 40),
        ))
        if self.loop:
            self.loop.draw_screen()

    def _reboot_system(self) -> bool:
        """Solicita un reinicio. Devuelve True si el comando fue aceptado."""
        log("USER: reinicio del sistema solicitado")
        try:
            return run("reboot", "systemctl", "reboot", sudo=True)
        except Exception as e:
            log(f"ERROR reboot: {type(e).__name__}: {e}")
            return False

    def _text_success(self):
        """Pantalla de exito en modo texto (sin TTY/urwid)."""
        print(f"\n  {chr(27)}[1;32m{chr(9670)} Instalacion completada{chr(27)}[0m\n")
        print("  Todos los pasos se completaron correctamente.")
        print(f"  Log: {LOG_FILE}\n")
        try:
            ans = input("  \u00bfReiniciar el sistema ahora? [s/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if ans in ("s", "si", "s\u00ed", "y", "yes"):
            if not self._reboot_system():
                print("\n  No se pudo reiniciar. Ejecuta manualmente: sudo reboot\n")

    def _show_error(self, failed_step: int):
        """Muestra dialogo de error cuando un paso falla."""
        self._modal = True

        # Copiar log al home del usuario
        home_dir = TARGET_HOME
        log_dest = f"{home_dir}/v0x3l-error.log"

        try:
            shutil.copy(LOG_FILE, log_dest)
        except OSError:
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
