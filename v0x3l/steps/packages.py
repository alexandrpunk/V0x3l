# Step 2: Software (mega-install + stack Dux/DMS 2.x + flatpak)

import shutil
import os
import subprocess
from v0x3l.shell import log

from v0x3l.steps.base import BaseStep
from v0x3l.config import TARGET_USER



class SoftwareStep(BaseStep):
    number = 2
    title = "Software"
    category = "packages"

    def run(self) -> bool:
        ok = True

        # ── Mega-install de paquetes + stack Dux (DMS 2.x) ──
        # El stack de Dux entra en la MISMA transaccion apt (docs:
        # https://duxlabs.dev/docs/dms/installation#ubuntu — PPAs duxlabs/*
        # agregados en Step 0):
        #   dms        — Dux Shell (deps: quickshell, danksearch, dgop,
        #                matugen, cava, accountsservice, qt6 modules)
        #   dms-greeter — greeter de greetd (docs dms-greeter/installation)
        #   dankcalendar — widget de calendario con integracion nativa
        #   hyprland   — compositor (Ubuntu trae 0.56.2 ≥ 0.55 requerido)
        #   kitty      — terminal (config via `dms setup --terminal kitty`)
        #   cliphist   — clipboard manager que arranca la config Dux de
        #                Hyprland (wl-paste --watch cliphist store)
        #   acl        — prerrequisito del theme sync de dms-greeter
        # greetd/quickshell/wl-clipboard y demas deps: los resuelve apt solo.
        # ── Mega-install de paquetes base ──
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

        DUXTAPE = ["hyprland", "kitty", "cliphist", "acl",
                   "dms", "dms-greeter", "dankcalendar"]
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


        # ── Configuracion del stack Dux (post-install via paquetes) ──
        # Docs: https://duxlabs.dev/docs/dms/cli-setup (headless) y
        #       https://duxlabs.dev/docs/dms-greeter/installation
        #
        # 1) `dms-greeter install` (como root): instala greetd si falta y
        #    maneja configuracion, permisos y enablement del servicio
        #    automaticamente. NO arranca greetd en el momento (la doc dice
        #    "To start the greeter immediately: sudo systemctl start greetd"
        #    — deliberadamente no lo hacemos: tomaria el TTY/seat y mataria
        #    la sesion del instalador; arranca solo tras el reboot final).
        # 2) `dms setup headless` (como TARGET_USER via runuser, ejemplo
        #    literal de la doc): deploya configs Dux de Hyprland (lua) +
        #    kitty y bindea dms.service a hyprland-session.target. `dms` se
        #    niega a correr como root. --skip-existing: idempotente.
        # 3) `dms-greeter sync` (como TARGET_USER, best-effort): theme sync
        #    per-user del greeter (symlinks a settings/wallpapers del user).
        #    Prerrequisitos cubiertos antes: acl en el mega-install y usuario
        #    en grupo greeter via usermod (comando documentado en la seccion
        #    Multi-user systems).
        if not TARGET_USER:
            log("ERROR dms: no se pudo resolver el usuario destino "
                "(SUDO_USER/logname); la configuracion de Dux requiere un "
                "usuario no-root")
            ok = False
        else:
            dms_installed = subprocess.run(
                ["command", "-v", "dms"], capture_output=True
            ).returncode == 0
            if not dms_installed:
                log("WARN dms: binario 'dms' no disponible (paquete dms no "
                    "instalado en el PPA); se omite configuracion de Dux")
                ok = False
            ok &= self.runner.ui.run_cmd("dms-greeter install",
                "dms-greeter", "install", sudo=True)

            # `dms setup headless` bindea dms.service a hyprland-session.target
            # via systemctl --user, y `dms-greeter sync` tambien usa unidades
            # de usuario. Corridos desde root sin sesion activa del usuario no
            # hay bus de usuario (XDG_RUNTIME_DIR/DBUS_SESSION_BUS_ADDRESS), asi
            # que el bindeo systemd cae al fallback. Replicamos el entorno de
            # usuario: enable-linger + arrancar user@UID + exports (mismo
            # patron que system.py usa para pipewire). El linger ya lo activa
            # Step 3, pero este step puede correr standalone/range.
            ok &= self.runner.ui.run_cmd("ensure user session bus",
                "bash", "-c",
                'u="$1"; uid=$(id -u "$u"); '
                'loginctl enable-linger "$u" 2>/dev/null || true; '
                'systemctl start "user@$uid" 2>/dev/null || true; '
                'export XDG_RUNTIME_DIR="/run/user/$uid"; '
                'export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$uid/bus"; '
                'runuser -u "$u" -- env XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR" '
                'DBUS_SESSION_BUS_ADDRESS="$DBUS_SESSION_BUS_ADDRESS" '
                'dms setup headless --compositor hyprland --terminal kitty '
                '--skip-existing',
                "dms-setup", TARGET_USER, sudo=True)

            # Grupos: input (Hyprland necesita /dev/input), greeter (theme
            # sync: "sudo usermod -aG greeter <username>")
            ok &= self.runner.ui.run_cmd("add input+greeter groups",
                "usermod", "-aG", "input,greeter", TARGET_USER, sudo=True)

            # Theme sync per-user (best-effort: si falla, el greeter igual
            # funciona con tema por defecto; no bloquea la instalacion).
            # Mismo entorno de bus de usuario que dms setup.
            sync_ok = self.runner.ui.run_cmd("dms-greeter sync",
                "bash", "-c",
                'u="$1"; uid=$(id -u "$u"); '
                'export XDG_RUNTIME_DIR="/run/user/$uid"; '
                'export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$uid/bus"; '
                'runuser -u "$u" -- env XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR" '
                'DBUS_SESSION_BUS_ADDRESS="$DBUS_SESSION_BUS_ADDRESS" '
                'dms-greeter sync',
                "dms-sync", TARGET_USER, sudo=True)
            if not sync_ok:
                log("WARN dms-greeter sync fallo (no fatal): el greeter "
                    "usara tema por defecto; re-ejecutar tras login")

            # ~/.config pudo quedar root-owned (otros comandos root del
            # instalador pueden tocarlo). Solo chown si existe para no
            # fallar cuando dms no se instaló (sin .config creado).
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
