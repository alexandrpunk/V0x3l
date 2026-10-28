# Step 2: Software (mega-install + stack Noctalia/Umbriel/sysc-greet + flatpak)

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
        # Paquetes del sistema (sistema base + flatpak). Esta transaccion es
        # independiente del stack Noctalia/Umbriel: si algun paquete no esta
        # disponible, el paso no falla entero y flatpak se instala igual.
        ok &= self.runner.ui.run_cmd("mega-install base",
            "nala", "install", "--no-install-recommends", "-y",
            "wayland-protocols", "libwayland-dev", "libegl1",
            "libgl1-mesa-dri", "mesa-vulkan-drivers", "xwayland",
            "thunar", "thunar-volman", "gvfs-backends", "gvfs-fuse", "udisks2", "polkitd",
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

        # ── Noctalia + Umbriel ──
        # Repositorio oficial Noctalia: compositor Umbriel, shell Noctalia
        # y portal XDG para Umbriel.
        umbriel_pkgs = ["noctalia", "umbriel", "xdg-desktop-portal-umbriel"]
        if not self.runner.ui.run_cmd("install noctalia + umbriel",
                "nala", "install", "--no-install-recommends", "-y",
                *umbriel_pkgs, sudo=True):
            log("WARN Noctalia/Umbriel: instalacion grupal fallo; probando "
                "paquete por paquete")
            for pkg in umbriel_pkgs:
                ok &= self.runner.ui.run_cmd(f"install {pkg}",
                    "nala", "install", "--no-install-recommends", "-y",
                    pkg, sudo=True)

        # ── sysc-greet ──
        # Paquete oficial v1.3.0 amd64 del greeter de greetd.
        sysc_greet_deb = "/tmp/sysc-greet_1.3.0_amd64.deb"
        if not os.path.exists(sysc_greet_deb):
            ok &= self.runner.ui.run_cmd("download sysc-greet deb",
                "bash", "-c",
                "set -euo pipefail; "
                "wget -q https://github.com/Nomadcxx/sysc-greet/releases/download/v1.3.0/"
                "sysc-greet_1.3.0_amd64.deb -O /tmp/sysc-greet_1.3.0_amd64.deb",
                sudo=True)
        if os.path.exists(sysc_greet_deb):
            installed = self.runner.ui.run_cmd("install sysc-greet deb",
                "apt", "install", "-y", sysc_greet_deb, sudo=True)
            ok &= installed
            if installed:
                os.remove(sysc_greet_deb)
        else:
            log("ERROR sysc-greet: no se pudo descargar el paquete .deb")
            ok = False

        # Umbriel es el compositor; Noctalia el shell. Su repo se agrega en
        # Step 0; aqui solo se instalan los paquetes.
        # ── Kitty oficial (ultima version estable) ──
        # Docs: https://sw.kovidgoyal.net/kitty/binary/
        # El instalador instala en ~/.local/kitty.app del usuario destino;
        # nunca debe ejecutarse como root. Se crean symlinks para kitty y
        # kitten en /usr/local/bin (PATH del sistema).
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
                "test -x \"$HOME/.local/kitty.app/bin/kitty\"; "
                "test -x \"$HOME/.local/kitty.app/bin/kitten\"; "
                "mkdir -p \"$HOME/.local/bin\" \"$HOME/.local/share/applications\"; "
                "ln -sf \"$HOME/.local/kitty.app/bin/kitty\" \"$HOME/.local/bin/kitty\"; "
                "ln -sf \"$HOME/.local/kitty.app/bin/kitten\" \"$HOME/.local/bin/kitten\"; "
                "for desktop in \"$HOME/.local/kitty.app/share/applications/kitty.desktop\" "
                "\"$HOME/.local/kitty.app/share/applications/kitty-open.desktop\"; do "
                "test -f \"$desktop\"; cp \"$desktop\" \"$HOME/.local/share/applications/\"; done; "
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

        # ── Flatpak: 1 remote + 1 transaccion para todas las apps ──
        # Antes: 3 `flatpak list` + hasta 3 `flatpak install` separados.
        # flatpak install acepta varios refs en una sola transaccion y es
        # idempotente (las ya instaladas se reportan y no se re-descargan).
        FLATHUB_APPS = ("org.gnome.Papers", "net.nokyan.Resources",
                        "io.github.diegopvlk.Cine", "org.atheme.audacious")
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
