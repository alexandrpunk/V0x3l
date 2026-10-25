# Step 2: Software (mega-install + stack Dux/DMS 2.x + flatpak)

import shutil
import os
import subprocess
from v0x3l.shell import log
from v0x3l.steps.base import BaseStep
from v0x3l.config import TARGET_USER, TARGET_HOME



class SoftwareStep(BaseStep):
    number = 2
    title = "Software"
    category = "packages"

    def run(self) -> bool:
        ok = True

        # ── Mega-install de paquetes base ──
        # El stack Dux se instala en una transaccion separada mas abajo.
        #   dms        — Dux Shell (deps: quickshell, danksearch, dgop,
        #                matugen, cava, accountsservice, qt6 modules)
        #   ly         — greeter TUI del sistema, desde butterrepo
        #   dankcalendar — widget de calendario con integracion nativa
        #   hyprland   — compositor desde ppa:cppiber/hyprland
        #   cliphist   — clipboard manager usado por la config Dux
        #   acl        — prerrequisito para integracion de permisos
        # Kitty se instala despues mediante el instalador binario oficial
        # (https://sw.kovidgoyal.net/kitty/binary/), como TARGET_USER.
        # Paquetes del sistema (sistema base + flatpak). Esta transaccion es
        # independiente del stack Dux: si algun paquete Dux no esta disponible
        # en el PPA, el paso no falla entero y flatpak se instala igual.
        ok &= self.runner.ui.run_cmd("mega-install base",
            "nala", "install", "--no-install-recommends", "-y",
            "wayland-protocols", "libwayland-dev", "libegl1",
            "libgl1-mesa-dri", "mesa-vulkan-drivers", "xwayland",
            "nautilus", "gvfs-backends", "gvfs-fuse", "udisks2", "polkitd",
            "ntfs-3g", "exfatprogs", "libglib2.0-bin",
            "neovim", "tmux", "fastfetch", "geany",
            "nwg-look", "dialog", "apt-utils",
            "libheif-plugin-libde265", "ufw", "gnome-sushi", "xdg-user-dirs",
            "pipewire", "wireplumber", "libpipewire-0.3-0",
            "libwireplumber-0.5-0",
            "dbus-user-session", "dbus-x11", "network-manager", "libnm0",
            "xdg-desktop-portal-wlr", "xdg-dbus-proxy",
            "bluez", "bluez-tools", "pipewire-pulse",
            "ubuntu-restricted-extras", "gstreamer1.0-plugins-bad",
            "gstreamer1.0-libav", "ffmpegthumbnailer",
            "floorp", "flatpak", "tlp", "tlp-rdw", "fonts-powerline", "fonts-noto", "fonts-noto-mono",
            "cups-pk-helper", "kimageformat-plugins",
            sudo=True)

        DUXTAPE = ["hyprland", "cliphist", "acl",
                   "dms", "ly", "dankcalendar"]
        if not self.runner.ui.run_cmd("install Dux stack",
                "nala", "install", "--no-install-recommends", "-y",
                *DUXTAPE, sudo=True):
            # Fallback paquete por paquete: si uno falta en el PPA, no
            # dejamos de instalar los demas ni romper el paso 2.
            log("WARN Dux stack: instalacion grupal fallo; probando "
                "paquete por paquete")
            for pkg in DUXTAPE:
                ok &= self.runner.ui.run_cmd(f"install {pkg}",
                    "nala", "install", "--no-install-recommends", "-y",
                    pkg, sudo=True)


        # ── Kitty oficial (ultima version estable) ──
        # Docs: https://sw.kovidgoyal.net/kitty/binary/
        # El instalador instala en ~/.local/kitty.app del usuario destino;
        # nunca debe ejecutarse como root. Se crean symlinks para kitty y
        # kitten en /usr/local/bin (PATH del sistema, visible a Hyprland/Dux)
        # y se instala la integracion desktop en el HOME del usuario.
        kitty_home = TARGET_HOME
        kitty_ok = False
        if not TARGET_USER:
            log("WARN kitty: no se pudo resolver TARGET_USER; se omite "
                "la instalacion para no ejecutarla como root")
        else:
            kitty_ok = self.runner.ui.run_cmd("install Kitty oficial",
                "runuser", "-u", TARGET_USER, "--", "env",
                f"HOME={kitty_home}", "bash", "-c",
                "set -eu; "
                "curl -fL https://sw.kovidgoyal.net/kitty/installer.sh | "
                "sh /dev/stdin; "
                "mkdir -p \"$HOME/.local/bin\" \"$HOME/.local/share/applications\"; "
                "ln -sf \"$HOME/.local/kitty.app/bin/kitty\" \"$HOME/.local/bin/kitty\"; "
                "ln -sf \"$HOME/.local/kitty.app/bin/kitten\" \"$HOME/.local/bin/kitten\"; "
                "cp \"$HOME/.local/kitty.app/share/applications/kitty.desktop\" "
                "\"$HOME/.local/share/applications/kitty.desktop\"; "
                "cp \"$HOME/.local/kitty.app/share/applications/kitty-open.desktop\" "
                "\"$HOME/.local/share/applications/kitty-open.desktop\"; "
                "kitty_root=\"$(readlink -f \"$HOME/.local/kitty.app\")\"; "
                "sed -i \"s|Icon=kitty|Icon=$kitty_root/share/icons/hicolor/256x256/apps/kitty.png|g; "
                "s|Exec=kitty|Exec=$kitty_root/bin/kitty|g\" "
                "\"$HOME/.local/share/applications/kitty\"*.desktop; "
                "mkdir -p \"$HOME/.config\"; "
                "printf '%s\\n' kitty.desktop > \"$HOME/.config/xdg-terminals.list\"",
                "kitty-install", TARGET_USER, sudo=True)
            ok &= kitty_ok

            if kitty_ok:
                ok &= self.runner.ui.run_cmd("link Kitty in system PATH",
                    "ln", "-sf", f"{kitty_home}/.local/kitty.app/bin/kitty",
                    "/usr/local/bin/kitty", sudo=True)
                ok &= self.runner.ui.run_cmd("link kitten in system PATH",
                    "ln", "-sf", f"{kitty_home}/.local/kitty.app/bin/kitten",
                    "/usr/local/bin/kitten", sudo=True)

        if not kitty_ok:
            log("WARN kitty: instalacion oficial fallo; se omite setup "
                "de Dux que requiere terminal kitty")
        ok &= kitty_ok


        # ── Configuracion del stack Dux (post-install via paquetes) ──
        # Docs: https://duxlabs.dev/docs/dms/cli-setup (headless)
        # Greeter: ly (desde butterrepo, ya agregado en Step 0).
        #
        # 1) `dms setup headless` (como TARGET_USER via runuser, ejemplo
        #    literal de la doc): deploya configs Dux de Hyprland (lua) +
        #    kitty y bindea dms.service a hyprland-session.target. `dms` se
        #    niega a correr como root. --skip-existing: idempotente.
        # 2) `ly` como greeter del sistema: habilitar el servicio ly
        #    (systemctl enable ly). Ly es un greeter minimalista TUI que no
        #    requiere configuracion de greetd ni temas complejos.
        # 3) Grupos: input (Hyprland necesita /dev/input).
        if not TARGET_USER:
            log("ERROR dms: no se pudo resolver el usuario destino "
                "(SUDO_USER/logname); la configuracion de Dux requiere un "
                "usuario no-root")
            ok = False
        else:
            dms_installed = shutil.which("dms") is not None
            if not dms_installed:
                log("WARN dms: binario 'dms' no disponible (paquete dms no "
                    "instalado en el PPA); se omite configuracion de Dux")
                ok = False
            else:
                ok &= self.runner.ui.run_cmd("ensure user session bus",
                    "bash", "-c",
                    'u="$1"; uid=$(id -u "$u"); '
                    'home=$(getent passwd "$u" | cut -d: -f6); '
                    'loginctl enable-linger "$u" 2>/dev/null || true; '
                    'systemctl start "user@$uid" 2>/dev/null || true; '
                    'export XDG_RUNTIME_DIR="/run/user/$uid"; '
                    'export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$uid/bus"; '
                    'runuser -u "$u" -- env HOME="$home" '
                    'PATH="$home/.local/bin:$PATH" '
                    'XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR" '
                    'DBUS_SESSION_BUS_ADDRESS="$DBUS_SESSION_BUS_ADDRESS" '
                    'dms setup headless --compositor hyprland --terminal kitty '
                    '--skip-existing',
                    "dms-setup", TARGET_USER, sudo=True)

                # Habilitar ly como greeter del sistema
                ok &= self.runner.ui.run_cmd("enable ly greeter",
                    "systemctl", "enable", "ly", sudo=True)

                # Grupos: input (Hyprland necesita /dev/input)
                ok &= self.runner.ui.run_cmd("add input group",
                    "usermod", "-aG", "input", TARGET_USER, sudo=True)

            # ~/.config pudo quedar root-owned (otros comandos root del
            # instalador pueden tocarlo). Solo chown si existe.
            home = os.path.expanduser(f"~{TARGET_USER}")
            config_dir = f"{home}/.config"
            if os.path.isdir(config_dir):
                ok &= self.runner.ui.run_cmd("fix ~/.config owner",
                    "chown", "-R", f"{TARGET_USER}:", config_dir,
                    sudo=True)

        # ── Flatpak: 1 remote + 1 transaccion para todas las apps ──
        # Antes: 3 `flatpak list` + hasta 3 `flatpak install` separados.
        # flatpak install acepta varios refs en una sola transaccion y es
        # idempotente (las ya instaladas se reportan y no se re-descargan).
        FLATHUB_APPS = ("org.gnome.Papers", "net.nokyan.Resources",
                        "org.gnome.Showtime")
        if not shutil.which("flatpak"):
            # Flatpak es opcional: no fallar si no esta disponible en el
            # entorno de ejecucion.
            log("INFO flatpak no instalado; se omite la configuracion de flatpak")
        else:
            remotes = subprocess.run(["flatpak", "remotes"],
                                     capture_output=True, text=True).stdout
            if "flathub" not in remotes:
                ok &= self.runner.ui.run_cmd("add flathub",
                    "flatpak", "remote-add", "--if-not-exists", "flathub",
                    "https://dl.flathub.org/repo/flathub.flatpakrepo",
                    sudo=True)

            installed = subprocess.run(
                ["flatpak", "list", "--app", "--columns=application"],
                capture_output=True, text=True).stdout
            pending = [a for a in FLATHUB_APPS if a not in installed]
            if pending:
                ok &= self.runner.ui.run_cmd(
                    f"flatpak install {' '.join(pending)}",
                    "flatpak", "install", "--system", "-y", "flathub", *pending,
                    sudo=True)

        override_path = "/etc/flatpak/overrides/global"
        if not os.path.exists(override_path):
            os.makedirs("/etc/flatpak/overrides", exist_ok=True)
            with open(override_path, "w") as f:
                f.write("[Context]\nfilesystems=xdg-run/gvfs:host;host:ro;\n")

        return ok
