# Steps de configuracion del sistema: 5-7, 9-10

import os
import subprocess
from voidforge.steps.base import BaseStep


class PolkitStep(BaseStep):
    number = 5
    title = "Configurando polkit automontaje"
    category = "system"

    def run(self) -> bool:
        rule_path = "/etc/polkit-1/rules.d/90-udisks2-automount.rules"
        if os.path.exists(rule_path):
            return True

        os.makedirs("/etc/polkit-1/rules.d", exist_ok=True)
        rule = '''polkit.addRule(function(action, subject) {
    if ((action.id == "org.freedesktop.udisks2.filesystem-mount" ||
         action.id == "org.freedesktop.udisks2.filesystem-mount-system") &&
        subject.isInGroup("plugdev")) {
        return polkit.Result.YES;
    }
});
'''
        with open(rule_path, "w") as f:
            f.write(rule)
        return True


class XdgUfwStep(BaseStep):
    number = 6
    title = "Configurando xdg-user-dirs y UFW"
    category = "system"

    def run(self) -> bool:
        ok = True
        user = os.environ.get("SUDO_USER", os.environ.get("USER", ""))
        home = f"/home/{user}" if user else "/root"

        # xdg-user-dirs
        if not os.path.exists(f"{home}/Documentos") and not os.path.exists(
                f"{home}/Documents"):
            subprocess.run(
                ["sudo", "-u", user, "xdg-user-dirs-update"],
                capture_output=True)

        # UFW
        result = subprocess.run(
            ["ufw", "status"], capture_output=True, text=True
        )
        if "active" not in result.stdout:
            self.runner.ui.run_cmd("ufw default deny",
                "ufw", "default", "deny", "incoming", sudo=True)
            self.runner.ui.run_cmd("ufw default allow",
                "ufw", "default", "allow", "outgoing", sudo=True)
            self.runner.ui.run_cmd("ufw enable",
                "bash", "-c", "echo y | ufw enable", sudo=True)
            self.runner.ui.run_cmd("ufw allow ssh",
                "ufw", "allow", "ssh", sudo=True)

        return ok


class NetworkStep(BaseStep):
    number = 7
    title = "Configurando red y optimizando boot"
    category = "system"

    def run(self) -> bool:
        ok = True

        # Desactivar systemd-networkd-wait-online
        self.runner.ui.run_cmd("mask wait-online",
            "systemctl", "mask", "systemd-networkd-wait-online.service",
            sudo=True)

        # Detectar interfaz activa
        iface = ""
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True, text=True
        )
        if result.stdout:
            parts = result.stdout.split()
            if len(parts) >= 5:
                iface = parts[4]

        if not iface:
            result = subprocess.run(
                ["ip", "-o", "link", "show"],
                capture_output=True, text=True
            )
            for line in result.stdout.splitlines():
                for prefix in ("en", "eth"):
                    if prefix in line:
                        iface = line.split(":")[1].strip()
                        break
                if iface:
                    break

        # Habilitar NetworkManager
        self.runner.ui.run_cmd("enable NetworkManager",
            "systemctl", "enable", "--now", "NetworkManager", sudo=True)

        # Netplan
        netplan_file = "/etc/netplan/01-netcfg.yaml"
        if not os.path.exists(netplan_file):
            with open(netplan_file, "w") as f:
                f.write("network:\n  version: 2\n  renderer: NetworkManager\n")
                if iface:
                    f.write(f"  ethernets:\n    {iface}:\n      dhcp4: true\n")

            self.runner.ui.run_cmd("netplan apply",
                "netplan", "apply", sudo=True)

        return ok


class ServicesStep(BaseStep):
    number = 9
    title = "Habilitando servicios y entorno Wayland"
    category = "system"

    def run(self) -> bool:
        ok = True
        user = os.environ.get("SUDO_USER", os.environ.get("USER", ""))
        home = f"/home/{user}" if user else "/root"

        # Servicios del sistema
        for svc in ("udisks2.service", "bluetooth.service"):
            self.runner.ui.run_cmd(f"enable {svc}",
                "systemctl", "enable", "--now", svc, sudo=True)

        # Linger para usuario
        self.runner.ui.run_cmd("enable linger",
            "loginctl", "enable-linger", user, sudo=True)

        # Pipewire
        self.runner.ui.run_cmd("enable pipewire",
            "sudo", "-u", user, "bash", "-c",
            'export XDG_RUNTIME_DIR="/run/user/$(id -u)"; '
            "systemctl --user enable pipewire.socket wireplumber.service",
            sudo=False)

        # Wayland env
        env_dir = f"{home}/.config/environment.d"
        env_file = f"{env_dir}/wayland.conf"
        if not os.path.exists(env_file):
            os.makedirs(env_dir, exist_ok=True)
            with open(env_file, "w") as f:
                f.write("GDK_BACKEND=wayland\n")
                f.write("QT_QPA_PLATFORM=wayland\n")
                f.write("SDL_VIDEODRIVER=wayland\n")
                f.write("MOZ_ENABLE_WAYLAND=1\n")
                f.write("XDG_CURRENT_DESKTOP=niri\n")
                f.write("XDG_SESSION_TYPE=wayland\n")

        return ok


class TLPStep(BaseStep):
    number = 10
    title = "Configurando optimizacion energetica (TLP)"
    category = "system"

    def run(self) -> bool:
        ok = True

        tlp_conf = "/etc/tlp.d/01-voidforge.conf"
        if not os.path.exists(tlp_conf):
            os.makedirs("/etc/tlp.d", exist_ok=True)
            config = """TLP_ENABLE=1
CPU_SCALING_GOVERNOR_ON_AC=powersave
CPU_SCALING_GOVERNOR_ON_BAT=powersave
CPU_ENERGY_PERF_POLICY_ON_AC=balance_performance
CPU_ENERGY_PERF_POLICY_ON_BAT=power
CPU_MIN_PERF_ON_AC=0
CPU_MAX_PERF_ON_AC=100
CPU_MIN_PERF_ON_BAT=0
CPU_MAX_PERF_ON_BAT=80
CPU_BOOST_ON_AC=1
CPU_BOOST_ON_BAT=0
PCIE_ASPM_ON_AC=powersupersave
PCIE_ASPM_ON_BAT=powersupersave
USB_AUTOSUSPEND=1
WIFI_PWR_ON_AC=off
WIFI_PWR_ON_BAT=on
SOUND_POWER_SAVE_ON_AC=1
SOUND_POWER_SAVE_ON_BAT=1
"""
            with open(tlp_conf, "w") as f:
                f.write(config)

            self.runner.ui.run_cmd("enable tlp",
                "systemctl", "enable", "tlp", sudo=True)

        # logind.conf
        logind = "/etc/systemd/logind.conf"
        replacements = {
            "HandleLidSwitch": "suspend",
            "HandleLidSwitchExternalPower": "suspend",
            "HandleLidSwitchDocked": "ignore",
            "PowerKeyAction": "poweroff",
        }
        for key, val in replacements.items():
            subprocess.run(
                ["sed", "-i",
                 f's/^#{key}=.*/{key}={val}/',
                 logind],
                capture_output=True)

        return ok
