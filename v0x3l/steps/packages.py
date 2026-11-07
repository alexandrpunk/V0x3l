# Step 2: Software (mega-install + stack Noctalia/Umbriel/ly + flatpak)

import shutil
import os
import subprocess
from v0x3l.shell import log
from v0x3l.steps.base import BaseStep
from v0x3l.config import TARGET_USER, TARGET_HOME, BIN_DIR


# Fuente unica de verdad de lo que instala el paso: la usan el propio paso y
# v0x3l/doctor.py para comprobar que no falto nada.
MEGA_PACKAGES = (
    "wayland-protocols", "libwayland-dev", "libegl1",
    "libgl1-mesa-dri", "mesa-vulkan-drivers", "xwayland",
    "thunar", "thunar-volman", "thunar-archive-plugin", "thunar-vcs-plugin",
    "polkitd", "seatd", "ly", "udisks2", "gvfs", "gvfs-backends",
    "ntfs-3g", "exfatprogs", "libglib2.0-bin",
    "unzip", "neovim", "tmux", "fastfetch",
    "plymouth", "plymouth-themes", "gtk-update-icon-cache",
    "nwg-look", "dialog", "apt-utils",
    "unattended-upgrades", "apparmor", "wget", "nano", "htop",
    "libheif-plugin-libde265", "ufw", "tumbler", "xdg-user-dirs",
    "viewnior", "qpdfview", "xarchiver", "awww", "mousepad",
    "pipewire", "wireplumber", "libpipewire-0.3-0",
    "libwireplumber-0.5-0",
    "dbus-user-session", "dbus-x11", "network-manager", "libnm0",
    "xdg-desktop-portal-wlr", "xdg-dbus-proxy",
    "bluez", "bluez-tools", "pipewire-pulse",
    "ubuntu-restricted-extras", "gstreamer1.0-plugins-bad",
    "gstreamer1.0-libav", "ffmpegthumbnailer",
    "floorp", "flatpak", "tlp", "tlp-rdw",
    "libgtk-4-1", "libadwaita-1-0",
)

# Compositor + shell + portal XDG.
UMBRIEL_PACKAGES = ("noctalia", "umbriel", "xdg-desktop-portal-umbriel")

# Extras no criticos: su descarga (SourceForge, en el caso de las fuentes)
# puede fallar y no debe abortar la instalacion.
EXTRA_PACKAGES = ("ttf-mscorefonts-installer",)


class SoftwareStep(BaseStep):
    number = 2
    title = "Software"
    category = "packages"

    def run(self) -> bool:
        ok = True
        # ── Reparar estado roto de dpkg/apt (herencia de ejecuciones previas) ──
        self.runner.ui.run_cmd("apt fix-broken (pre-mega)",
            "apt", "install", "--fix-broken", "-y", sudo=True)


        # ── EULA de ttf-mscorefonts-installer ──
        # Sin el preseed, nala/apt abre un dialogo debconf interactivo en la
        # TUI y la transaccion queda colgada.
        self.runner.ui.run_cmd("preseed mscorefonts EULA", "bash", "-c",
            "echo 'ttf-mscorefonts-installer "
            "msttcorefonts/accepted-mscorefonts-eula select true' | "
            "debconf-set-selections", sudo=True)

        # ── Mega-install de paquetes base ──
        # Paquetes del sistema (sistema base + flatpak). Si la transaccion grupal
        # falla (held broken packages, conflictos de dependencia), se intentan
        # instalar uno por uno.
        if not self.runner.ui.run_cmd("mega-install base",
                "nala", "install", "--no-install-recommends", "-y",
                *MEGA_PACKAGES, sudo=True):
            log("WARN mega-install fallo (held broken packages?); instalando "
                "paquete por paquete")
            failed_pkgs = []
            for pkg in MEGA_PACKAGES:
                if not self.runner.ui.run_cmd(f"install {pkg}",
                        "nala", "install", "--no-install-recommends", "-y",
                        pkg, sudo=True):
                    failed_pkgs.append(pkg)
                    ok = False
            if failed_pkgs:
                log(f"ERROR paquetes no instalados: {', '.join(failed_pkgs)}")
        # ── Noctalia + Umbriel ──
        # Repositorio oficial Noctalia: compositor Umbriel, shell Noctalia
        # y portal XDG para Umbriel.
        umbriel_pkgs = UMBRIEL_PACKAGES
        if not self.runner.ui.run_cmd("install noctalia + umbriel",
                "nala", "install", "--no-install-recommends", "-y",
                *umbriel_pkgs, sudo=True):
            log("WARN Noctalia/Umbriel: instalacion grupal fallo; probando "
                "paquete por paquete")
            for pkg in umbriel_pkgs:
                ok &= self.runner.ui.run_cmd(f"install {pkg}",
                    "nala", "install", "--no-install-recommends", "-y",
                    pkg, sudo=True)


        # Extras no criticos (fuentes MS core). Si falla la descarga, se
        # registra y la instalacion continua.
        for pkg in EXTRA_PACKAGES:
            if not self.runner.ui.run_cmd(f"install {pkg}",
                    "nala", "install", "-y", pkg, sudo=True):
                log(f"WARN {pkg}: no se pudo instalar (descarga); "
                    f"reintentar: sudo apt install {pkg}")

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

        # ── xdg-mime-gui (gestor grafico de apps por defecto) ──
        # Binario precompilado en assets/bin/. Solo se copia a /usr/local/bin.
        mime_bin = "/usr/local/bin/xdg-mime-gui"
        if not os.path.exists(mime_bin):
            mime_src = os.path.join(str(BIN_DIR), "xdg-mime-gui")
            mime_desktop_src = os.path.join(str(BIN_DIR),
                "io.github.tomas_barros1.DefaultApps.desktop")
            if os.path.isfile(mime_src):
                ok &= self.runner.ui.run_cmd("install xdg-mime-gui",
                    "install", "-Dm755", mime_src, mime_bin, sudo=True)
                ok &= self.runner.ui.run_cmd("install xdg-mime-gui desktop",
                    "install", "-Dm644", mime_desktop_src,
                    "/usr/local/share/applications/"
                    "io.github.tomas_barros1.DefaultApps.desktop",
                    sudo=True)
                log("INFO xdg-mime-gui instalado (binario precompilado)")
            else:
                log("WARN xdg-mime-gui: binario precompilado no encontrado "
                    "en assets/bin/")
        else:
            log("INFO xdg-mime-gui ya instalado; se omite")

        # ── Flatpak: 1 remote + 1 transaccion para todas las apps ──
        # Antes: 3 `flatpak list` + hasta 3 `flatpak install` separados.
        # flatpak install acepta varios refs en una sola transaccion y es
        # idempotente (las ya instaladas se reportan y no se re-descargan).
        FLATHUB_APPS = ("net.nokyan.Resources",
                        "io.github.diegopvlk.Cine", "org.atheme.audacious")
        if not (shutil.which("flatpak") or os.path.exists("/usr/bin/flatpak")):
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