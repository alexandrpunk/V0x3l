# Step 3: Configuracion (polkit + xdg-ufw + red + servicios + TLP)

import os
import subprocess
from v0x3l.steps.base import BaseStep
from v0x3l.config import TLP_CONF_NAME, CURSOR_THEME_NAME, TARGET_USER, TARGET_HOME
from v0x3l.shell import log


class ConfigurationStep(BaseStep):
    number = 3
    title = "Configuracion"
    category = "system"

    def run(self) -> bool:
        ok = True
        user = TARGET_USER
        home = TARGET_HOME

        # ---- Helpers para operaciones robustas ----
        def run_nonfatal(desc: str, *args, **kwargs) -> bool:
            """Ejecuta comando no crítico; loggea warning si falla pero no rompe ok."""
            try:
                result = self.runner.ui.run_cmd(desc, *args, **kwargs)
                if not result:
                    log(f"WARN {desc}: comando fallo (no fatal)")
                return result
            except Exception as e:
                log(f"WARN {desc}: excepcion {type(e).__name__}: {e}")
                return False

        def run_critical(desc: str, *args, **kwargs) -> bool:
            """Ejecuta comando crítico; falla ok si falla."""
            try:
                result = self.runner.ui.run_cmd(desc, *args, **kwargs)
                if not result:
                    log(f"ERROR {desc}: comando fallo (critico)")
                return result
            except Exception as e:
                log(f"ERROR {desc}: excepcion {type(e).__name__}: {e}")
                return False

        def write_file_if_missing(path: str, content: str, mode: int = 0o644) -> bool:
            """Escribe archivo solo si no existe; retorna True si escrito, False si ya existía."""
            try:
                if not os.path.exists(path):
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, "w") as f:
                        f.write(content)
                    os.chmod(path, mode)
                    log(f"INFO escrito: {path}")
                    return True
                return False
            except Exception as e:
                log(f"ERROR escribiendo {path}: {type(e).__name__}: {e}")
                return False

        def ensure_user_ownership(path: str) -> bool:
            """Asegura ownership al usuario real; no crítico."""
            if user and os.geteuid() == 0 and os.path.exists(path):
                try:
                    subprocess.run(
                        ["chown", "-R", f"{user}:", path], capture_output=True, check=False
                    )
                    return True
                except Exception:
                    pass
            return True

        # ---- Polkit automontaje ----
        rule_path = "/etc/polkit-1/rules.d/90-udisks2-automount.rules"
        write_file_if_missing(rule_path, (
            'polkit.addRule(function(action, subject) {\n'
            '    if ((action.id == "org.freedesktop.udisks2.filesystem-mount"'
            ' || action.id == "org.freedesktop.udisks2.filesystem-mount-system")'
            ' && subject.isInGroup("plugdev")) {\n'
            '        return polkit.Result.YES;\n    }\n});\n'
        ), mode=0o644)

        # ---- xdg-user-dirs ----
        if not os.path.exists(f"{home}/Documentos") and not os.path.exists(
                f"{home}/Documents"):
            run_nonfatal("xdg-user-dirs-update",
                "sudo", "-u", user, "-H", "xdg-user-dirs-update", sudo=False)

        # ---- UFW ----
        result = subprocess.run(["ufw", "status"], capture_output=True, text=True)
        if "active" not in result.stdout:
            ok &= run_critical("ufw default deny",
                "ufw", "default", "deny", "incoming", sudo=True)
            ok &= run_critical("ufw default allow",
                "ufw", "default", "allow", "outgoing", sudo=True)
            ok &= run_critical("ufw enable",
                "bash", "-c", "echo y | ufw enable", sudo=True)
            ok &= run_critical("ufw allow ssh",
                "ufw", "allow", "ssh", sudo=True)

        # ---- Red + NetworkManager ----
        run_nonfatal("mask wait-online",
            "systemctl", "mask", "systemd-networkd-wait-online.service",
            sudo=True)

        iface = ""
        r = subprocess.run(["ip", "route", "show", "default"],
                           capture_output=True, text=True)
        if r.stdout:
            parts = r.stdout.split()
            if len(parts) >= 5:
                iface = parts[4]
        if not iface:
            r = subprocess.run(["ip", "-o", "link", "show"],
                                capture_output=True, text=True)
            for ln in r.stdout.splitlines():
                for pfx in ("en", "eth"):
                    if pfx in ln:
                        iface = ln.split(":")[1].strip()
                        break
                if iface:
                    break

        run_critical("enable NetworkManager",
            "systemctl", "enable", "--now", "NetworkManager", sudo=True)

        # Netplan mínimo: solo renderer NetworkManager.
        # No se fuerzan interfaces porque el nombre detectado
        # (ej. wlp3s0) puede no casar con el device type real y
        # netplan apply rechaza cambiar el tipo de una interfaz existente.
        netplan_file = "/etc/netplan/01-netcfg.yaml"
        if write_file_if_missing(netplan_file, (
            "network:\n  version: 2\n  renderer: NetworkManager\n"
        ), mode=0o600):
            ok &= run_critical("netplan apply", "netplan", "apply", sudo=True)

        # ---- Servicios básicos ----
        for svc in ("udisks2.service", "bluetooth.service"):
            ok &= run_critical(f"enable {svc}",
                "systemctl", "enable", "--now", svc, sudo=True)

        ok &= run_critical("enable linger",
            "loginctl", "enable-linger", user, sudo=True)

        # Pipewire user services
        run_nonfatal("enable pipewire user",
            "sudo", "-u", user, "-H", "bash", "-c",
            'export XDG_RUNTIME_DIR="/run/user/$(id -u)"; '
            'export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"; '
            "systemctl --user enable pipewire.socket wireplumber.service",
            sudo=False)

        # Variables de entorno Wayland
        env_dir = f"{home}/.config/environment.d"
        env_file = f"{env_dir}/wayland.conf"
        write_file_if_missing(env_file, (
            "GDK_BACKEND=wayland\nQT_QPA_PLATFORM=wayland\n"
            "SDL_VIDEODRIVER=wayland\nMOZ_ENABLE_WAYLAND=1\n"
            f"XCURSOR_THEME={CURSOR_THEME_NAME}\n"
            "XDG_CURRENT_DESKTOP=Umbriel\nXDG_SESSION_TYPE=wayland\n"
        ))
        ensure_user_ownership(f"{home}/.config")

        # ---- Cursor theme default ----
        cursor_dir = "/usr/share/icons/default"
        write_file_if_missing(f"{cursor_dir}/index.theme", (
            f"[Icon Theme]\nName=Default\nInherits={CURSOR_THEME_NAME}\n"
        ))

        # ---- TLP ----
        tlp_conf = f"/etc/tlp.d/{TLP_CONF_NAME}"
        if write_file_if_missing(tlp_conf, (
            "TLP_ENABLE=1\nCPU_SCALING_GOVERNOR_ON_AC=powersave\n"
            "CPU_SCALING_GOVERNOR_ON_BAT=powersave\n"
            "CPU_ENERGY_PERF_POLICY_ON_AC=balance_performance\n"
            "CPU_ENERGY_PERF_POLICY_ON_BAT=power\n"
            "CPU_MAX_PERF_ON_AC=100\nCPU_MAX_PERF_ON_BAT=80\n"
            "CPU_BOOST_ON_AC=1\nCPU_BOOST_ON_BAT=0\n"
            "PCIE_ASPM_ON_AC=powersave\n"
            "PCIE_ASPM_ON_BAT=powersave\n"
            "USB_AUTOSUSPEND=1\nWIFI_PWR_ON_AC=off\n"
            "WIFI_PWR_ON_BAT=on\nSOUND_POWER_SAVE_ON_AC=1\n"
            "SOUND_POWER_SAVE_ON_BAT=1\n"
        )):
            run_critical("enable tlp", "systemctl", "enable", "tlp", sudo=True)

        # ---- Logind config ----
        logind = "/etc/systemd/logind.conf"
        replacements = {
            "HandleLidSwitch": "suspend",
            "HandleLidSwitchExternalPower": "suspend",
            "HandleLidSwitchDocked": "ignore",
            "PowerKeyAction": "poweroff"
        }
        for key, val in replacements.items():
            run_nonfatal(f"logind {key}",
                "sed", "-i", f"s/^#?{key}=.*/{key}={val}/", logind,
                sudo=True)

        # ---- Configuración de Umbriel para Noctalia ----
        umbriel_dir = os.path.join(home, ".config", "umbriel")
        umbriel_config = os.path.join(umbriel_dir, "config.toml")
        if user and write_file_if_missing(umbriel_config, (
            "# Configuracion generada por V0x3l\n"
            "# Layout: floating (solicitado)\n"
            '[layout]\nmode = "floating"\n\n'
            "# Autostart de Noctalia dentro de Umbriel (Noctalia v5 usa ejecutable 'noctalia')\n"
            "# Documentacion: https://docs.noctalia.dev/noctalia/getting-started/running-the-shell/\n"
            "# Documentacion integracion Umbriel: https://docs.noctalia.dev/noctalia/compositor-settings/umbriel/\n"
            "[general]\nautostart = [\"noctalia\", \"kitty\"]\n\n"
            "# Configuracion de apariencia recomendada para integracion Noctalia\n"
            "[appearance]\nprefer_no_csd = true\nborder_width = 2\ncorner_radius = 10\n\n"
            "[appearance.blur]\nenabled = true\noptimized = true\npasses = 2\nradius = 3\nnoise = 0.02\nbrightness = 0.9\ncontrast = 0.9\nsaturation = 1.1\n\n"
            "# Window rules para settings de Noctalia\n"
            "# Blur all windows\n"
            "[[window_rule]]\nblur = true\nblur_optimized = true\n\n"
            "# Float Noctalia settings window\n"
            "[[window_rule]]\nmatch = \"title:Noctalia Settings\"\nfloat = true\n"
        )):
            ensure_user_ownership(umbriel_dir)

        # Verificación post-escritura: validar config.toml
        if os.path.exists(umbriel_config):
            try:
                subprocess.run(
                    ["sudo", "-u", user, "-H", "umbriel", "config", "validate", umbriel_config],
                    capture_output=True, check=False
                )
            except Exception:
                pass

        # ── Configuracion ly (display manager) + seatd para Umbriel ──
        # ly es un display manager TUI que NO usa systemd; se instala y
        # arranca de forma independiente. seatd SÍ necesita systemd para
        # dar acceso a dispositivos de asiento (input/GPU) sin root.
        if user:
            run_nonfatal("usermod seat group",
                "usermod", "-aG", "seat", user, sudo=True)

        ok_seatd = run_critical("enable seatd",
            "systemctl", "enable", "--now", "seatd.service", sudo=True)
        if not ok_seatd:
            log("WARN seatd.service no disponible; ly podria no tener "
                "acceso a input/GPU sin root")

        # Sesion de usuario de Umbriel para que ly sepa arrancarla tras
        # el login (ly lee /usr/share/wayland-sessions y xsessions).
        if user:
            umbriel_session = "/usr/share/wayland-sessions/umbriel.desktop"
            write_file_if_missing(umbriel_session, (
                "[Desktop Entry]\n"
                "Name=Umbriel\n"
                "Comment=Umbriel Wayland compositor\n"
                "Exec=umbriel\n"
                "Type=Application\n"
            ), mode=0o644)

        # ---- Verificaciones finales (smoke tests) ----
        def verify_service_active(svc: str) -> bool:
            """Verifica si un servicio systemd está activo."""
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", svc],
                    capture_output=True, text=True, timeout=5
                )
                return result.returncode == 0 and "active" in result.stdout
            except Exception:
                return False

        # Verificaciones no fatales, solo informativas
        if not verify_service_active("seatd.service"):
            log("WARN seatd.service no está activo tras habilitar")

        if not verify_service_active("NetworkManager.service"):
            log("WARN NetworkManager.service no está activo")

        if not verify_service_active("udisks2.service"):
            log("WARN udisks2.service no está activo")

        if not verify_service_active("bluetooth.service"):
            log("WARN bluetooth.service no está activo")

        # Verificar netplan config válida
        if os.path.exists(netplan_file):
            try:
                subprocess.run(
                    ["netplan", "generate"], capture_output=True, check=False
                )
            except Exception:
                pass

        # Verificar que umbriel config es válida
        if os.path.exists(umbriel_config):
            try:
                subprocess.run(
                    ["umbriel", "config", "validate"],
                    capture_output=True, check=False
                )
            except Exception:
                pass

        return ok