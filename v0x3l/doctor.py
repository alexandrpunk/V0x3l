# Comprobacion post-instalacion: verifica que todo lo que instala V0x3l siga
# presente. Solo lee (no modifica nada) y puede ejecutarse sin root:
#
#     python3 -m v0x3l --check
#
# El informe tambien esta disponible desde el menu de la TUI (opcion 7).

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass

from v0x3l.config import (
    CURSOR_THEME_NAME, ICON_THEME_NAME, JUNO_THEME_NAME,
    PLYMOUTH_THEME_NAME, TARGET_HOME, TARGET_USER, TLP_CONF_NAME,
)
from v0x3l.steps.packages import (EXTRA_PACKAGES, MEGA_PACKAGES,
                                  UMBRIEL_PACKAGES)
from v0x3l.steps.system import section_key
from v0x3l.steps.theming import (
    GRUB_DEFAULT_CONF, GRUB_THEMES, GRUB_THEME_INSTALL_DIR,
    PLYMOUTH_DEFAULT_LINK, PLYMOUTH_THEMES, SYSTEM_ICONS, SYSTEM_THEMES,
)

OK, WARN, FAIL = "ok", "warn", "fail"

MARK = {OK: "[ok]   ", WARN: "[aviso]", FAIL: "[FALLA]"}

ICON_VARIANTS = ("Pure", "Pure-Dark", "Pure-Light")
DOTFILES = ((".config/kitty", "kitty"), (".config/tmux", "tmux"),
            (".config/fastfetch", "fastfetch"))
WAYLAND_SESSION = "/usr/share/wayland-sessions/umbriel.desktop"
POLKIT_RULE = "/etc/polkit-1/rules.d/90-udisks2-automount.rules"
NETPLAN_FILE = "/etc/netplan/01-netcfg.yaml"
CURSOR_DEFAULT = f"{SYSTEM_ICONS}/default/index.theme"


@dataclass
class Check:
    """Resultado de una comprobacion individual."""

    group: str
    name: str
    status: str
    detail: str = ""
    hint: str = ""


# ── Helpers ────────────────────────────────────────────────────────────────

def _read(path: str) -> str:
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return ""


def _cmd(*args: str, timeout: int = 10) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True,
                                timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout if result.returncode == 0 else ""


def _package_installed(name: str) -> bool:
    out = _cmd("dpkg-query", "-W", "-f=${Status}", name)
    return "install ok installed" in out


def _unit_active(unit: str) -> str:
    return _cmd("systemctl", "is-active", unit, timeout=5).strip()


def _user_in_group(user: str, group: str) -> bool:
    return group in _cmd("id", "-nG", user).split()


def _gsettings_get(schema: str, key: str) -> str:
    return _cmd("gsettings", "get", schema, key).strip().strip("'\"")


def _has_nvidia() -> bool:
    lspci = shutil.which("lspci")
    if not lspci:
        return False
    out = _cmd(lspci, "-nn").lower()
    return any("nvidia" in line for line in out.splitlines()
               if any(k in line for k in ("vga", "3d", "display")))


# ── Comprobaciones ─────────────────────────────────────────────────────────

def _check_hardware() -> list[Check]:
    out = [Check("Rendimiento", "kernel XanMod",
                 OK if "xanmod" in os.uname().release else WARN,
                 os.uname().release,
                 "se usa el kernel de la distribucion (no es un fallo)")]
    if _has_nvidia():
        has_smi = bool(shutil.which("nvidia-smi"))
        out.append(Check("Rendimiento", "driver NVIDIA (nvidia-smi)",
                         OK if has_smi else FAIL, "",
                         "sudo nala install nvidia-driver-<serie>"))
        modprobe = "/etc/modprobe.d/nvidia.conf"
        out.append(Check("Rendimiento", "modprobe nvidia",
                         OK if os.path.exists(modprobe) else WARN, modprobe,
                         "lo escribe el paso 1 en sistemas con NVIDIA"))
    return out


def _check_software(home: str) -> list[Check]:
    out = []
    for pkg in (*UMBRIEL_PACKAGES, *MEGA_PACKAGES):
        installed = _package_installed(pkg)
        out.append(Check("Software", pkg, OK if installed else FAIL,
                         "" if installed else "no instalado",
                         f"sudo nala install {pkg}"))
    for pkg in EXTRA_PACKAGES:
        installed = _package_installed(pkg)
        out.append(Check("Software", pkg, OK if installed else WARN,
                         "" if installed else "no instalado",
                         f"sudo nala install {pkg}"))

    kitty_bin = os.path.join(home, ".local", "kitty.app", "bin", "kitty")
    out.append(Check("Software", "kitty (aplicacion)",
                     OK if os.path.exists(kitty_bin) else FAIL, kitty_bin,
                     "vuelve a ejecutar el paso 2"))
    link = shutil.which("kitty")
    out.append(Check("Software", "kitty en PATH", OK if link else FAIL,
                     link or "", "sudo ln -sf ~/.local/kitty.app/bin/kitty "
                                 "/usr/local/bin/kitty"))

    if shutil.which("flatpak"):
        remotes = _cmd("flatpak", "remotes").split()
        out.append(Check("Software", "flatpak remotes", OK if remotes else WARN,
                         " ".join(dict.fromkeys(remotes)),
                         "flatpak remote-add --if-not-exists flathub "
                         "https://flathub.org/repo/flathub.flatpakrepo"))

    # gnome-sushi tiene 'Depends: nautilus' y arrastraba GNOME Files a un
    # sistema cuyo gestor de archivos es Thunar.
    nautilus = _package_installed("nautilus")
    out.append(Check("Software", "sin Nautilus (se usa Thunar)",
                     WARN if nautilus else OK,
                     "nautilus instalado" if nautilus else "",
                     "sudo apt purge gnome-sushi && sudo apt autoremove --purge"))
    return out


def _check_system(home: str, user: str) -> list[Check]:
    out = []

    state = _unit_active("seatd.service")
    out.append(Check("Sistema", "seatd.service",
                     OK if state == "active" else FAIL, state,
                     "sudo systemctl enable --now seatd.service"))
    out.append(Check("Sistema", f"usuario en grupo seat",
                     OK if _user_in_group(user, "seat") else FAIL, user,
                     f"sudo usermod -aG seat {user} (reloguea despues)"))
    out.append(Check("Sistema", "sesion Umbriel para ly",
                     OK if os.path.exists(WAYLAND_SESSION) else FAIL,
                     WAYLAND_SESSION, "vuelve a ejecutar el paso 3"))
    out.append(Check("Sistema", "regla polkit automontaje",
                     OK if os.path.exists(POLKIT_RULE) else WARN, POLKIT_RULE,
                     "vuelve a ejecutar el paso 3"))

    cfg = os.path.join(home, ".config", "umbriel", "config.toml")
    text = _read(cfg)
    if not text:
        out.append(Check("Sistema", "config de Umbriel", FAIL, cfg,
                         "vuelve a ejecutar el paso 3"))
    else:
        mode = (section_key(text, "layout", "mode") or "").strip('"')
        out.append(Check("Sistema", "Umbriel: layout flotante",
                         OK if mode == "stacking" else FAIL, mode or "(sin definir)",
                         "layout.mode debe ser 'stacking' (flotante)"))
        out.append(Check("Sistema", "Umbriel: atajos de teclado",
                         OK if "[keybinds]" in text else FAIL, "",
                         "sin [keybinds] Umbriel usa un set minimo"))
        cursor = (section_key(text, "input.cursor", "theme") or "").strip('"')
        out.append(Check("Sistema", "Umbriel: tema de cursor",
                         OK if cursor == CURSOR_THEME_NAME else FAIL,
                         cursor or "(sin definir)",
                         f"input.cursor.theme debe ser {CURSOR_THEME_NAME}"))
        autostart = (section_key(text, "general", "autostart") or "")
        out.append(Check("Sistema", "Umbriel: autostart sin kitty",
                         OK if "kitty" not in autostart else WARN, autostart,
                         "kitty en autostart abre una terminal al entrar"))

    out.append(Check("Sistema", "config TLP",
                     OK if os.path.exists(f"/etc/tlp.d/{TLP_CONF_NAME}") else WARN,
                     f"/etc/tlp.d/{TLP_CONF_NAME}", "vuelve a ejecutar el paso 3"))
    out.append(Check("Sistema", "netplan",
                     OK if os.path.exists(NETPLAN_FILE) else WARN, NETPLAN_FILE,
                     "vuelve a ejecutar el paso 3"))
    env_file = os.path.join(home, ".config", "environment.d", "wayland.conf")
    out.append(Check("Sistema", "variables Wayland",
                     OK if os.path.exists(env_file) else WARN, env_file,
                     "vuelve a ejecutar el paso 3"))
    out.append(Check("Sistema", "cursor por defecto (X11)",
                     OK if CURSOR_THEME_NAME in _read(CURSOR_DEFAULT) else WARN,
                     CURSOR_DEFAULT, "vuelve a ejecutar el paso 3"))

    for unit in ("NetworkManager.service", "udisks2.service", "ufw.service",
                 "tlp.service"):
        state = _unit_active(unit)
        out.append(Check("Sistema", unit, OK if state == "active" else WARN,
                         state or "inactivo", f"sudo systemctl enable --now {unit}"))
    return out


def _check_appearance(home: str) -> list[Check]:
    out = []

    cursors = f"{SYSTEM_ICONS}/{CURSOR_THEME_NAME}"
    out.append(Check("Apariencia", f"cursores {CURSOR_THEME_NAME}",
                     OK if os.path.isdir(cursors) else FAIL, cursors,
                     "vuelve a ejecutar el paso 4"))
    for variant in ICON_VARIANTS:
        path = f"{SYSTEM_ICONS}/{variant}"
        out.append(Check("Apariencia", f"iconos {variant}",
                         OK if os.path.isdir(path) else FAIL, path,
                         "vuelve a ejecutar el paso 4"))
    juno = f"{SYSTEM_THEMES}/{JUNO_THEME_NAME}"
    out.append(Check("Apariencia", f"tema GTK {JUNO_THEME_NAME}",
                     OK if os.path.isdir(juno) else FAIL, juno,
                     "vuelve a ejecutar el paso 4"))

    plymouth_file = f"{PLYMOUTH_THEMES}/{PLYMOUTH_THEME_NAME}"
    out.append(Check("Apariencia", "tema Plymouth",
                     OK if os.path.isfile(
                         f"{plymouth_file}/{PLYMOUTH_THEME_NAME}.plymouth")
                     else FAIL, plymouth_file, "vuelve a ejecutar el paso 4"))
    link = os.path.realpath(PLYMOUTH_DEFAULT_LINK)
    out.append(Check("Apariencia", "Plymouth por defecto",
                     OK if link.startswith(plymouth_file) else FAIL,
                     link if os.path.exists(PLYMOUTH_DEFAULT_LINK) else "(sin enlace)",
                     f"sudo plymouth-set-default-theme {PLYMOUTH_THEME_NAME} -R"))

    grub_theme_txt = f"{GRUB_THEMES}/{GRUB_THEME_INSTALL_DIR}/theme.txt"
    out.append(Check("Apariencia", "tema GRUB",
                     OK if os.path.isfile(grub_theme_txt) else FAIL,
                     grub_theme_txt, "vuelve a ejecutar el paso 4"))
    grub_conf = _read(GRUB_DEFAULT_CONF)
    active = re.search(r"^\s*GRUB_THEME=(.*)$", grub_conf, re.M)
    out.append(Check("Apariencia", "GRUB_THEME activo",
                     OK if active and grub_theme_txt in active.group(1) else FAIL,
                     active.group(1).strip() if active else "(sin definir)",
                     "sudo update-grub tras fijar GRUB_THEME"))
    out.append(Check("Apariencia", "arranque con 'splash'",
                     OK if re.search(r"^GRUB_CMDLINE_LINUX_DEFAULT=.*\bsplash\b",
                                     grub_conf, re.M) else WARN, "",
                     "sin 'splash' Plymouth no se dibuja"))

    for rel, label in ((".config/gtk-3.0/settings.ini", "GTK3 settings.ini"),
                       (".config/gtk-4.0/settings.ini", "GTK4 settings.ini")):
        path = os.path.join(home, rel)
        content = _read(path)
        ok = "gtk-theme-name" in content and JUNO_THEME_NAME in content
        out.append(Check("Apariencia", label, OK if ok else FAIL, path,
                         "vuelve a ejecutar el paso 4"))

    theme = _gsettings_get("org.gnome.desktop.interface", "gtk-theme")
    icons = _gsettings_get("org.gnome.desktop.interface", "icon-theme")
    cursor = _gsettings_get("org.gnome.desktop.interface", "cursor-theme")
    if not (theme or icons):
        out.append(Check("Apariencia", "temas activos (gsettings)", WARN,
                         "sin sesion D-Bus",
                         "ejecuta la comprobacion dentro de la sesion grafica"))
    else:
        for label, value, expected in (("gtk-theme", theme, JUNO_THEME_NAME),
                                       ("icon-theme", icons, ICON_THEME_NAME),
                                       ("cursor-theme", cursor, CURSOR_THEME_NAME)):
            out.append(Check("Apariencia", f"gsettings {label}",
                             OK if value == expected else WARN, value or "(vacio)",
                             f"gsettings set org.gnome.desktop.interface "
                             f"{label} {expected}"))
    return out


def _check_environment(home: str) -> list[Check]:
    out = []
    for rel, label in DOTFILES:
        path = os.path.join(home, rel)
        out.append(Check("Entorno", f"dotfile {label}",
                         OK if os.path.exists(path) else WARN, path,
                         "vuelve a ejecutar el paso 5"))

    nvim = os.path.join(home, ".config", "nvim")
    ok_nvim = (os.path.exists(os.path.join(nvim, "init.lua"))
               and os.path.isdir(os.path.join(nvim, "lua")))
    out.append(Check("Entorno", "LazyVim", OK if ok_nvim else WARN, nvim,
                     "vuelve a ejecutar el paso 5"))

    omp = next((p for p in (os.path.join(home, ".local", "bin", "omp"),
                            os.path.join(home, ".bun", "bin", "omp"),
                            "/usr/local/bin/omp") if os.path.exists(p)), "")
    out.append(Check("Entorno", "omp (harness)", OK if omp else FAIL, omp,
                     "curl -fsSL https://omp.sh/install | sh"))
    agent = os.path.join(home, ".omp", "agent")
    out.append(Check("Entorno", "harness omp desplegado",
                     OK if os.path.isdir(agent) else WARN, agent,
                     "vuelve a ejecutar el paso 5"))
    return out


def run_checks(home: str | None = None, user: str | None = None) -> list[Check]:
    """Ejecuta todas las comprobaciones. Solo lectura."""
    home = home or TARGET_HOME
    user = user or TARGET_USER
    checks: list[Check] = []
    checks += _check_hardware()
    checks += _check_software(home)
    checks += _check_system(home, user)
    checks += _check_appearance(home)
    checks += _check_environment(home)
    return checks


def summarize(checks: list[Check]) -> tuple[int, int, int]:
    """Devuelve (ok, avisos, fallos)."""
    counts = {OK: 0, WARN: 0, FAIL: 0}
    for check in checks:
        counts[check.status] = counts.get(check.status, 0) + 1
    return counts[OK], counts[WARN], counts[FAIL]


def format_report(checks: list[Check]) -> str:
    """Informe en texto plano (TUI y CLI)."""
    ok, warn, fail = summarize(checks)
    lines = ["Comprobacion de la instalacion", ""]
    group = ""
    for check in checks:
        if check.group != group:
            group = check.group
            lines.append(f"{group}")
        line = f"  {MARK.get(check.status, '[?]    ')} {check.name}"
        if check.detail:
            line += f": {check.detail}"
        lines.append(line)
        if check.status != OK and check.hint:
            lines.append(f"           -> {check.hint}")
        if check.status == FAIL:
            lines.append("")
    lines.append("")
    lines.append(f"Resumen: {ok} ok, {warn} avisos, {fail} fallos")
    return "\n".join(lines)
