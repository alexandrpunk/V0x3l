# Step 3: Configuracion (polkit + xdg-ufw + red + servicios + TLP)

import os
import subprocess
from voidforge.steps.base import BaseStep


class ConfigurationStep(BaseStep):
    number = 3
    title = "Configuracion"
    category = "system"

    def run(self) -> bool:
        ok = True
        user = os.environ.get("SUDO_USER", os.environ.get("USER", ""))
        home = f"/home/{user}" if user else "/root"

        # ── Polkit automontaje ──
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

        # ── xdg-user-dirs ──
        if not os.path.exists(f"{home}/Documentos") and not os.path.exists(
                f"{home}/Documents"):
            subprocess.run(["sudo", "-u", user, "xdg-user-dirs-update"],
                           capture_output=True)

        # ── UFW ──
        result = subprocess.run(["ufw", "status"],
                                capture_output=True, text=True)
        if "active" not in result.stdout:
            self.runner.ui.run_cmd("ufw default deny",
                "ufw", "default", "deny", "incoming", sudo=True)
            self.runner.ui.run_cmd("ufw default allow",
                "ufw", "default", "allow", "outgoing", sudo=True)
            self.runner.ui.run_cmd("ufw enable",
                "bash", "-c", "echo y | ufw enable", sudo=True)
            self.runner.ui.run_cmd("ufw allow ssh",
                "ufw", "allow", "ssh", sudo=True)

        # ── Red + NetworkManager ──
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
            with open(netplan_file, "w") as f:
                f.write("network:\n  version: 2\n  renderer: NetworkManager\n")
                if iface:
                    f.write(f"  ethernets:\n    {iface}:\n      dhcp4: true\n")
            self.runner.ui.run_cmd("netplan apply",
                "netplan", "apply", sudo=True)

        # ── Servicios ──
        for svc in ("udisks2.service", "bluetooth.service"):
            self.runner.ui.run_cmd(f"enable {svc}",
                "systemctl", "enable", "--now", svc, sudo=True)

        self.runner.ui.run_cmd("enable linger",
            "loginctl", "enable-linger", user, sudo=True)

        self.runner.ui.run_cmd("enable pipewire",
            "sudo", "-u", user, "bash", "-c",
            'export XDG_RUNTIME_DIR="/run/user/$(id -u)"; '
            "systemctl --user enable pipewire.socket wireplumber.service",
            sudo=False)

        env_dir = f"{home}/.config/environment.d"
        env_file = f"{env_dir}/wayland.conf"
        if not os.path.exists(env_file):
            os.makedirs(env_dir, exist_ok=True)
            with open(env_file, "w") as f:
                f.write("GDK_BACKEND=wayland\nQT_QPA_PLATFORM=wayland\n"
                        "SDL_VIDEODRIVER=wayland\nMOZ_ENABLE_WAYLAND=1\n"
                        "XDG_CURRENT_DESKTOP=niri\nXDG_SESSION_TYPE=wayland\n")

        # ── TLP ──
        tlp_conf = "/etc/tlp.d/01-voidforge.conf"
        if not os.path.exists(tlp_conf):
            os.makedirs("/etc/tlp.d", exist_ok=True)
            config = ("TLP_ENABLE=1\nCPU_SCALING_GOVERNOR_ON_AC=powersave\n"
                      "CPU_SCALING_GOVERNOR_ON_BAT=powersave\n"
                      "CPU_ENERGY_PERF_POLICY_ON_AC=balance_performance\n"
                      "CPU_ENERGY_PERF_POLICY_ON_BAT=power\n"
                      "CPU_MAX_PERF_ON_AC=100\nCPU_MAX_PERF_ON_BAT=80\n"
                      "CPU_BOOST_ON_AC=1\nCPU_BOOST_ON_BAT=0\n"
                      "PCIE_ASPM_ON_AC=powersupersave\n"
                      "PCIE_ASPM_ON_BAT=powersupersave\n"
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
            subprocess.run(["sed", "-i",
                            f"s/^#{key}=.*/{key}={val}/", logind],
                           capture_output=True)

        return ok
