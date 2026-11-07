# Step 3: Configuracion (polkit + xdg-ufw + red + servicios + TLP)

import os
import re
import shutil
import subprocess
from v0x3l.steps.base import BaseStep
from v0x3l.config import (TLP_CONF_NAME, CURSOR_THEME_NAME, TARGET_USER,
                          TARGET_HOME, UMBRIEL_CONFIG_TEMPLATE,
                          NOCTALIA_SHELL_CFG)
from v0x3l.shell import log


# ---- Umbriel: config base ------------------------------------------------
# Se parte del config EMPAQUETADO de Umbriel (/usr/share/umbriel/config.toml):
# ya trae el set completo de keybinds por defecto (lanzador Noctalia, cerrar
# ventana, workspaces, medios) y va versionado junto al binario. Umbriel
# REEMPLAZA ese set cuando el usuario define [keybinds], asi que un config
# minimo los borra. Solo aplicamos las preferencias de V0x3l por encima.
UMBRIEL_PACKAGED = "/usr/share/umbriel/config.toml"
UMBRIEL_VALID_MODES = ("scrolling", "dwindle", "master", "stacking")
# (seccion, clave, valor TOML ya formateado)
UMBRIEL_PREFS = (
    ("layout", "mode", '"stacking"'),          # ventanas flotantes
    ("general", "autostart", '["noctalia"]'),  # sin kitty al arrancar
    ("general", "xwayland", "true"),           # XWayland cuando se necesite
    # El cheatsheet de atajos ya no se abre en cada arranque (default true);
    # se muestra y se cierra con Mod+F2 o `umbriel msg cheatsheet-toggle`.
    ("general", "show_cheatsheet", "false"),
    # Los clientes que negocian decoracion usan la barra de Umbriel en vez de
    # dibujar su propio headerbar (default true; se fija por si el config
    # empaquetado o una edicion previa lo desactivo).
    ("appearance", "prefer_no_csd", "true"),
    # Barra de titulo con los tres botones en el borde de la ventana. El
    # default es mode = "off" (sin barra); "forced" la dibuja tambien para
    # clientes que prefieren CSD, que es justo lo que faltaba.
    ("appearance.title_bar", "mode", '"forced"'),
    # Layout macOS: los tres botones a la izquierda del titulo. La lista va
    # "desde el titulo hacia el borde", asi que el ultimo (close) queda en el
    # extremo izquierdo: [close][minimize][maximize] Titulo.
    ("appearance.title_bar", "button_position", '"left"'),
    ("appearance.title_bar", "buttons", '["maximize", "minimize", "close"]'),
    ("appearance.title_bar", "button_size", "12"),
    ("appearance.title_bar", "button_corner_radius", "100"),
    ("appearance.title_bar", "button_glyph", '"hover"'),
    # Alt+Tab abre el selector de ventanas de Noctalia (con previsualizacion)
    # limitado al workspace actual; mientras se mantiene Alt, Tab/Shift+Tab
    # recorren la lista y al soltar se enfoca la elegida. repeat = false para
    # no relanzar el selector con cada autorepeat.
    ("keybinds", '"Alt+Tab"',
     '{ action = "spawn noctalia msg window-switcher hold current", repeat = false }'),
    ("keybinds", '"Alt+Shift+Tab"',
     '{ action = "spawn noctalia msg window-switcher hold current", repeat = false }'),
    ("keybinds", '"Mod+F2"', '{ action = "cheatsheet-toggle", repeat = false }'),
    # Cursor del compositor: en Wayland lo fija Umbriel, no GTK.
    ("input.cursor", "theme", f'"{CURSOR_THEME_NAME}"'),
    ("input.cursor", "size", "24"),
)

# ── Aplicaciones por defecto ──
# xdg-open, Thunar y Noctalia resuelven "abrir con" por ~/.config/mimeapps.list
# (INI, sin espacios alrededor del '='). Los tipos van explicitos porque
# mimeapps.list no admite comodines.
DEFAULT_MIME_APPS = (
    # Navegador: Floorp (repo oficial que anade el paso 0)
    ("text/html", "floorp.desktop"),
    ("x-scheme-handler/http", "floorp.desktop"),
    ("x-scheme-handler/https", "floorp.desktop"),
    # Editor de texto plano
    ("text/plain", "mousepad.desktop"),
    # Visor de imagenes
    ("image/png", "viewnior.desktop"),
    ("image/jpeg", "viewnior.desktop"),
    ("image/gif", "viewnior.desktop"),
    ("image/webp", "viewnior.desktop"),
    ("image/bmp", "viewnior.desktop"),
    ("image/tiff", "viewnior.desktop"),
    # PDF
    ("application/pdf", "qpdfview.desktop"),
    # Video: Cine (Flatpak del sistema que instala el paso 2)
    ("video/mp4", "io.github.diegopvlk.Cine.desktop"),
    ("video/x-matroska", "io.github.diegopvlk.Cine.desktop"),
    ("video/webm", "io.github.diegopvlk.Cine.desktop"),
    ("video/x-msvideo", "io.github.diegopvlk.Cine.desktop"),
    ("video/quicktime", "io.github.diegopvlk.Cine.desktop"),
    ("video/mpeg", "io.github.diegopvlk.Cine.desktop"),
    ("video/ogg", "io.github.diegopvlk.Cine.desktop"),
    ("video/x-flv", "io.github.diegopvlk.Cine.desktop"),
    ("video/x-m4v", "io.github.diegopvlk.Cine.desktop"),
    ("video/3gpp", "io.github.diegopvlk.Cine.desktop"),
    ("video/mp2t", "io.github.diegopvlk.Cine.desktop"),
)


def set_ini_key(text: str, section: str, key: str, value: str) -> str:
    """Fija `key=value` en [section]; formato mimeapps.list (sin espacios)."""
    lines = text.splitlines()
    header = f"[{section}]"
    start = next((i for i, l in enumerate(lines) if l.strip() == header), None)
    if start is None:
        body = text.rstrip()
        prefix = f"{body}\n\n" if body else ""
        return f"{prefix}{header}\n{key}={value}\n"
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].strip().startswith("[")), len(lines))
    for i in range(start + 1, end):
        if re.match(rf"^{re.escape(key)}\s*=", lines[i].strip()):
            lines[i] = f"{key}={value}"
            break
    else:
        lines.insert(start + 1, f"{key}={value}")
    return "\n".join(lines) + "\n"


def apply_default_apps(home: str) -> bool:
    """Marca navegador/editor/imagenes/PDF/video por defecto en mimeapps.list."""
    path = os.path.join(home, ".config", "mimeapps.list")
    try:
        text = ""
        if os.path.exists(path):
            with open(path) as f:
                text = f.read()
        for mime, desktop in DEFAULT_MIME_APPS:
            text = set_ini_key(text, "Default Applications", mime,
                               f"{desktop};")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text)
        log(f"INFO apps: {len(DEFAULT_MIME_APPS)} tipos MIME por defecto en "
            f"{path}")
        return True
    except OSError as e:
        log(f"ERROR apps: {path}: {type(e).__name__}: {e}")
        return False


def configure_thunar_terminal(home: str) -> bool:
    """Registra kitty como terminal predeterminada de Thunar/exo.

    Thunar 4.20 lanza "Abrir terminal aqui" como
    `exo-open --working-directory %f --launch TerminalEmulator`. exo lee
    ~/.config/xfce4/helpers.rc SIN cabecera de seccion: sin
    xfce4-mime-helper (lo normal en este stack) resuelve el valor con
    g_find_program_in_path, y con el helper instalado lo usa como id de
    ~/.local/share/xfce4/helpers/<id>.desktop. Se cubren ambos casos, asi que
    la accion deja de caer en xfce4-terminal (que no esta instalado).
    """
    path = os.path.join(home, ".config", "xfce4", "helpers.rc")
    try:
        text = ""
        if os.path.exists(path):
            with open(path) as f:
                text = f.read()
        lines = [l for l in text.splitlines()
                 if not re.match(r"^\s*TerminalEmulator\s*=", l)]
        lines.append("TerminalEmulator=kitty")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")

        helper_dir = os.path.join(home, ".local", "share", "xfce4", "helpers")
        helper = os.path.join(helper_dir, "kitty.desktop")
        os.makedirs(helper_dir, exist_ok=True)
        with open(helper, "w") as f:
            f.write(
                "[Desktop Entry]\n"
                "Version=1.0\n"
                "Type=X-XFCE-Helper\n"
                "Name=kitty\n"
                "Icon=kitty\n"
                "X-XFCE-Category=TerminalEmulator\n"
                f"X-XFCE-Binaries={home}/.local/kitty.app/bin/kitty;\n"
                "X-XFCE-Commands=%B;\n"
                "X-XFCE-CommandsWithParameter=%B %s;\n"
            )
        log(f"INFO thunar: kitty como terminal predeterminada ({path})")
        return True
    except OSError as e:
        log(f"ERROR thunar: {path}: {type(e).__name__}: {e}")
        return False


def apply_noctalia_switcher(home: str) -> bool:
    """Configura el selector de ventanas de Noctalia (Alt+Tab).

    Se escribe en un fragmento *.toml propio (no en settings.toml, que
    gestiona la GUI en ~/.local/state/noctalia/): el selector recorre solo el
    workspace actual del monitor y usa orden MRU como un Alt+Tab clasico.
    """
    path = os.path.join(home, ".config", "noctalia", NOCTALIA_SHELL_CFG)
    content = (
        "# Generado por V0x3l; se reescribe en cada ejecucion del instalador.\n"
        "[shell.window_switcher]\n"
        "current_workspace_only = true\n"
        "show_all_outputs = false\n"
        "mru = true\n"
    )
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        log(f"INFO noctalia: selector de ventanas configurado ({path})")
        return True
    except OSError as e:
        log(f"ERROR noctalia: {path}: {type(e).__name__}: {e}")
        return False


def section_key(text: str, section: str, key: str):
    """Valor de `key` dentro de [section], ignorando comentarios y subsecciones."""
    cur, value = None, None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("[") and not line.startswith("[["):
            cur = line.strip("[]").strip()
        elif cur == section:
            m = re.match(rf'^{re.escape(key)}\s*=\s*(.+)$', line)
            if m:
                value = m.group(1).strip()
    return value


def set_section_key(text: str, section: str, key: str, value: str) -> str:
    """Fija `key = value` en [section]: reemplaza si existe, si no inserta tras el header."""
    lines = text.splitlines()
    header = f"[{section}]"
    start = next((i for i, l in enumerate(lines) if l.strip() == header), None)
    if start is None:
        return f"{text.rstrip()}\n\n{header}\n{key} = {value}\n"
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].strip().startswith("[") and not lines[i].strip().startswith("[[")),
               len(lines))
    for i in range(start + 1, end):
        if re.match(rf'^{re.escape(key)}\s*=', lines[i].strip()):
            lines[i] = f"{key} = {value}"
            break
    else:
        lines.insert(start + 1, f"{key} = {value}")
    return "\n".join(lines) + "\n"


def seed_umbriel_config(dest: str,
                        packaged: str = UMBRIEL_PACKAGED,
                        template: str = UMBRIEL_CONFIG_TEMPLATE) -> bool:
    """Genera el config desde el empaquetado (version-correcto) o el template vendorizado."""
    src = packaged if os.path.isfile(packaged) else template
    try:
        with open(src) as f:
            text = f.read()
    except Exception as e:
        log(f"ERROR umbriel config: origen {src}: {type(e).__name__}: {e}")
        return False
    for section, key, value in UMBRIEL_PREFS:
        text = set_section_key(text, section, key, value)
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w") as f:
            f.write(text)
        log(f"INFO umbriel config generado desde {src} -> {dest}")
        return True
    except Exception as e:
        log(f"ERROR umbriel config: escribiendo {dest}: {type(e).__name__}: {e}")
        return False


def umbriel_needs_reseed(path: str) -> bool:
    """True si el config existente usa un layout invalido o no define atajos."""
    try:
        with open(path) as f:
            text = f.read()
    except Exception:
        return True
    mode = (section_key(text, "layout", "mode") or "").strip('"')
    if mode and mode not in UMBRIEL_VALID_MODES:
        return True
    return "[keybinds]" not in text


def apply_umbriel_prefs(path: str) -> bool:
    """Aplica UMBRIEL_PREFS sobre un config existente sin regenerarlo.

    Necesario para que una preferencia nueva (p. ej. [input.cursor]) llegue a
    instalaciones ya hechas sin descartar el resto del archivo del usuario.
    """
    try:
        with open(path) as f:
            text = f.read()
    except OSError:
        return False
    for section, key, value in UMBRIEL_PREFS:
        text = set_section_key(text, section, key, value)
    try:
        with open(path, "w") as f:
            f.write(text)
        log(f"INFO umbriel config: preferencias aplicadas en {path}")
        return True
    except OSError as e:
        log(f"ERROR umbriel config: escribiendo {path}: {e}")
        return False


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
        # La lógica vive a nivel de modulo (UMBRIEL_PREFS): se parte del config
        # empaquetado de Umbriel y solo se aplican las preferencias de V0x3l.
        umbriel_dir = os.path.join(home, ".config", "umbriel")
        umbriel_config = os.path.join(umbriel_dir, "config.toml")

        if user:
            os.makedirs(umbriel_dir, exist_ok=True)
            if os.path.exists(umbriel_config):
                if umbriel_needs_reseed(umbriel_config):
                    try:
                        shutil.copy2(umbriel_config, umbriel_config + ".bak")
                        log(f"INFO umbriel config: backup en {umbriel_config}.bak")
                    except Exception:
                        pass
                    ok &= seed_umbriel_config(umbriel_config)
                elif apply_umbriel_prefs(umbriel_config):
                    log("INFO umbriel config: existente valido, preferencias aplicadas")
                else:
                    log("WARN umbriel config: no se pudieron aplicar las preferencias")
            else:
                ok &= seed_umbriel_config(umbriel_config)
            ensure_user_ownership(umbriel_dir)

        # ---- Aplicaciones por defecto (mimeapps.list) ----
        # Floorp (navegador), mousepad (texto plano), viewnior (imagenes),
        # qpdfview (PDF) y Cine (video).
        if user:
            if apply_default_apps(home):
                ensure_user_ownership(os.path.join(home, ".config",
                                                   "mimeapps.list"))
            else:
                log("WARN apps: no se pudieron fijar las aplicaciones por defecto")

        # ---- Thunar: kitty como terminal + selector de ventanas (Alt+Tab) ----
        if user:
            ok &= configure_thunar_terminal(home)
            ok &= apply_noctalia_switcher(home)
            ensure_user_ownership(os.path.join(home, ".config", "xfce4"))
            ensure_user_ownership(os.path.join(home, ".config", "noctalia"))
            ensure_user_ownership(os.path.join(home, ".local", "share",
                                               "xfce4"))

        # Verificación post-escritura: validar config.toml
        if os.path.exists(umbriel_config):
            try:
                subprocess.run(
                    ["sudo", "-u", user, "-H", "umbriel", "config",
                     "validate", "-c", umbriel_config],
                    capture_output=True, check=False
                )
            except Exception:
                pass

        # ── Configuracion ly (display manager) + seatd para Umbriel ──
        # ly es un display manager TUI que NO usa systemd; se instala y
        # arranca de forma independiente. seatd SÍ necesita systemd para
        # dar acceso a dispositivos de asiento (input/GPU) sin root.
        if user:
            run_nonfatal("ensure seat group exists",
                "bash", "-c", "getent group seat >/dev/null || groupadd -r seat", sudo=True)
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