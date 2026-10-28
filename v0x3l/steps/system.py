# Step 3: Configuracion (polkit + xdg-ufw + red + servicios + TLP)

import os
import subprocess
from v0x3l.steps.base import BaseStep
from v0x3l.config import TLP_CONF_NAME, CURSOR_THEME_NAME, TARGET_USER, TARGET_HOME


class ConfigurationStep(BaseStep):
    number = 3
    title = "Configuracion"
    category = "system"

    def run(self) -> bool:
        ok = True
        user = TARGET_USER
        home = TARGET_HOME

        # ---- Polkit automontaje ----
        rule_path = "/etc/polkit-1/rules.d/90-udisks2-automount.rules"
        if not os.path.exists(rule_path):
            os.makedirs("/etc/polkit-1/rules.d", exist_ok=True)
            rule = ('polkit.addRule(function(action, subject) {\n'
                    '    if ((action.id == "org.freedesktop.udisks2.filesystem-mount"'
                    ' || action.id == "org.freedesktop.udisks2.filesystem-mount-system")'
                    ' && subject.isInGroup("plugdev")) {\n'
                    '        return polkit.Result.YES;\n    }\n});\n')
            with open(rule_path, "w") as f:
                f.write(rule)

        # ---- xdg-user-dirs ----
        if not os.path.exists(f"{home}/Documentos") and not os.path.exists(
                f"{home}/Documents"):
            subprocess.run(["sudo", "-u", user, "-H", "xdg-user-dirs-update"],
                           capture_output=True)

        # ---- UFW ----
        result = subprocess.run(["ufw", "status"],
                                capture_output=True, text=True)
        if "active" not in result.stdout:
            ok &= self.runner.ui.run_cmd("ufw default deny",
                "ufw", "default", "deny", "incoming", sudo=True)
            ok &= self.runner.ui.run_cmd("ufw default allow",
                "ufw", "default", "allow", "outgoing", sudo=True)
            ok &= self.runner.ui.run_cmd("ufw enable",
                "bash", "-c", "echo y | ufw enable", sudo=True)
            ok &= self.runner.ui.run_cmd("ufw allow ssh",
                "ufw", "allow", "ssh", sudo=True)

        # ---- Red + NetworkManager ----
        self.runner.ui.run_cmd("mask wait-online",
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

        self.runner.ui.run_cmd("enable NetworkManager",
            "systemctl", "enable", "--now", "NetworkManager", sudo=True)

        netplan_file = "/etc/netplan/01-netcfg.yaml"
        if not os.path.exists(netplan_file):
            # Validar iface: solo caracteres seguros para YAML (evita parse
            # errors si la deteccion captura basura con espacios o comas)
            import re
            if iface and not re.match(r'^[a-zA-Z0-9_-]+$', iface):
                iface = ""
            with open(netplan_file, "w") as f:
                f.write("network:\n  version: 2\n  renderer: NetworkManager\n")
                if iface:
                    f.write(f"  ethernets:\n    {iface}:\n      dhcp4: true\n")
            ok &= self.runner.ui.run_cmd("netplan apply",
                "netplan", "apply", sudo=True)

        # ---- Servicios ----
        for svc in ("udisks2.service", "bluetooth.service"):
            ok &= self.runner.ui.run_cmd(f"enable {svc}",
                "systemctl", "enable", "--now", svc, sudo=True)

        ok &= self.runner.ui.run_cmd("enable linger",
            "loginctl", "enable-linger", user, sudo=True)

        self.runner.ui.run_cmd("enable pipewire",
            "sudo", "-u", user, "-H", "bash", "-c",
            'export XDG_RUNTIME_DIR="/run/user/$(id -u)"; '
            'export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"; '
            "systemctl --user enable pipewire.socket wireplumber.service",
            sudo=False)

        env_dir = f"{home}/.config/environment.d"
        env_file = f"{env_dir}/wayland.conf"
        if not os.path.exists(env_file):
            os.makedirs(env_dir, exist_ok=True)
            with open(env_file, "w") as f:
                f.write(f"GDK_BACKEND=wayland\nQT_QPA_PLATFORM=wayland\n"
                        "SDL_VIDEODRIVER=wayland\nMOZ_ENABLE_WAYLAND=1\n"
                        f"XCURSOR_THEME={CURSOR_THEME_NAME}\n"
                        "XDG_CURRENT_DESKTOP=Umbriel\nXDG_SESSION_TYPE=wayland\n")

        # ── Cursor theme default ──
        cursor_dir = "/usr/share/icons/default"
        if not os.path.exists(f"{cursor_dir}/index.theme"):
            os.makedirs(cursor_dir, exist_ok=True)
            with open(f"{cursor_dir}/index.theme", "w") as f:
                f.write(f"[Icon Theme]\nName=Default\nInherits={CURSOR_THEME_NAME}\n")

        # ---- Asegurar ownership de ~/.config al usuario ----
        # Los writes como root pueden dejar ~/.config root-owned. Se deja
        # ownership recursivo al usuario real.
        if user and os.geteuid() == 0 and os.path.isdir(f"{home}/.config"):
            subprocess.run(["chown", "-R", f"{user}:", f"{home}/.config"],
                           capture_output=True)

        # ---- TLP ----
        tlp_conf = f"/etc/tlp.d/{TLP_CONF_NAME}"
        if not os.path.exists(tlp_conf):
            os.makedirs("/etc/tlp.d", exist_ok=True)
            config = ("TLP_ENABLE=1\nCPU_SCALING_GOVERNOR_ON_AC=powersave\n"
                      "CPU_SCALING_GOVERNOR_ON_BAT=powersave\n"
                      "CPU_ENERGY_PERF_POLICY_ON_AC=balance_performance\n"
                      "CPU_ENERGY_PERF_POLICY_ON_BAT=power\n"
                      "CPU_MAX_PERF_ON_AC=100\nCPU_MAX_PERF_ON_BAT=80\n"
                      "CPU_BOOST_ON_AC=1\nCPU_BOOST_ON_BAT=0\n"
                      "PCIE_ASPM_ON_AC=powersave\n"
                      "PCIE_ASPM_ON_BAT=powersave\n"
                      "USB_AUTOSUSPEND=1\nWIFI_PWR_ON_AC=off\n"
                      "WIFI_PWR_ON_BAT=on\nSOUND_POWER_SAVE_ON_AC=1\n"
                      "SOUND_POWER_SAVE_ON_BAT=1\n")
            with open(tlp_conf, "w") as f:
                f.write(config)
            self.runner.ui.run_cmd("enable tlp",
                "systemctl", "enable", "tlp", sudo=True)

        logind = "/etc/systemd/logind.conf"
        replacements = {"HandleLidSwitch": "suspend",
                        "HandleLidSwitchExternalPower": "suspend",
                        "HandleLidSwitchDocked": "ignore",
                        "PowerKeyAction": "poweroff"}
        for key, val in replacements.items():
            # Patron ^#?\{key}=: matchea lineas comentadas (#Key=) Y
            # descomentadas (Key=). Antes solo matcheaba comentadas -> no-op
            # en re-runs donde la linea ya estaba descomentada.
            subprocess.run(["sed", "-i",
                            f"s/^#?{key}=.*/{key}={val}/", logind],
                           capture_output=True)
        umbriel_dir = os.path.join(home, ".config", "umbriel")
        umbriel_config = os.path.join(umbriel_dir, "config.toml")
        umbriel_config = f"{umbriel_dir}/config.toml"
        if user and not os.path.exists(umbriel_config):
            os.makedirs(umbriel_dir, exist_ok=True)
            config_toml = (
                "# Configuracion generada por V0x3l\n"
                "# Layout: floating (solicitado)\n"
                '[layout]\nmode = "floating"\n\n'
                "# Autostart de Noctalia dentro de Umbriel\n"
                "# Documentacion: https://docs.noctalia.dev/noctalia/getting-started/running-the-shell/\n"
                "[general]\nautostart = [\"noctalia-shell\", \"kitty\"]\n"
            )
            with open(umbriel_config, "w") as f:
                f.write(config_toml)
            if os.geteuid() == 0:
                subprocess.run(["chown", "-R", f"{user}:", umbriel_dir],
                               capture_output=True)

        # ── Configuracion sysc-greet para Umbriel ──
        # Se crea una sesion personalizada para greetd con Umbriel como
        # compositor de login y se habilita el servicio greetd.
        # Ruta de configuracion de greetd: /etc/greetd/config.toml
        greetd_dir = "/etc/greetd"
        greetd_conf = f"{greetd_dir}/config.toml"
        os.makedirs(greetd_dir, exist_ok=True)
        greetd_toml = (
            "[terminal]\n"
            "vt = 1\n\n"
            "[default_session]\n"
            "command = \"umbriel\"\n"
            "user = \"greeter\"\n"
        )
        with open(greetd_conf, "w") as f:
            f.write(greetd_toml)

        if user:
            subprocess.run(["useradd", "-M", "-d", "/var/lib/greeter",
                            "-G", "video,render,input", "-s",
                            "/usr/sbin/nologin", "greeter"],
                           capture_output=True)
            for dir_path in ("/var/cache/sysc-greet",
                             "/var/lib/greeter/Pictures/wallpapers",
                             "/var/lib/greeter/.cache",
                             "/var/lib/greeter/.config",
                             "/var/lib/greeter/.local/state"):
                os.makedirs(dir_path, exist_ok=True)
            subprocess.run(["chown", "-R", "greeter:greeter",
                            "/var/cache/sysc-greet", "/var/lib/greeter"],
                           capture_output=True)
            subprocess.run(["chmod", "755", "/var/lib/greeter"],
                           capture_output=True)

        # greetd puede no tener unit file aun si sysc-greet se instalo
        # recientemente o el paquete no lo incluye; no es fatal para el paso.
        greetd_ok = self.runner.ui.run_cmd("enable greetd",
            "systemctl", "enable", "--now", "greetd.service", sudo=True)
        if not greetd_ok:
            log("WARN greetd.service no esta disponible; se habilitara "
                "manualmente o en el siguiente arranque")


        return ok
