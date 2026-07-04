# Step 1: Rendimiento y drivers (kernel XanMod + GPU NVIDIA)

import os
import subprocess
from v0x3l.steps.base import BaseStep


class PerformanceStep(BaseStep):
    number = 1
    title = "Rendimiento y drivers"
    category = "drivers"

    def run(self) -> bool:
        ok = True

        # ── Kernel XanMod ──
        if not os.path.exists("/etc/apt/sources.list.d/xanmod-release.list"):
            self.runner.ui.run_cmd("xanmod key", "bash", "-c",
                "wget -qO- https://dl.xanmod.org/archive.key | "
                "gpg --dearmor -vo "
                "/etc/apt/keyrings/xanmod-archive-keyring.gpg",
                sudo=True)

            codename = subprocess.run(
                ["lsb_release", "-sc"],
                capture_output=True, text=True
            ).stdout.strip()

            self.runner.ui.run_cmd("xanmod repo", "bash", "-c",
                f'echo "deb [signed-by=/etc/apt/keyrings/xanmod-archive-keyring.gpg] '
                f'https://deb.xanmod.org {codename} main non-free" | '
                "tee /etc/apt/sources.list.d/xanmod-release.list",
                sudo=True)
            self.runner.ui.run_cmd("nala update",
                "nala", "update", sudo=True)

        current_kernel = subprocess.run(
            ["uname", "-r"], capture_output=True, text=True
        ).stdout

        if "xanmod" not in current_kernel:
            ok &= self.runner.ui.run_cmd("install xanmod",
                "nala", "install", "-y", "linux-xanmod-edge-x64v3", sudo=True)
            ok &= self.runner.ui.run_cmd("install dkms",
                "nala", "install", "--no-install-recommends", "-y",
                "dkms", "libelf-dev", "clang", "lld", "llvm", sudo=True)

        # ── GPU NVIDIA ──
        lspci = subprocess.run(
            ["lspci", "-nn"], capture_output=True, text=True
        ).stdout.lower()

        has_nvidia = "nvidia" in lspci
        has_intel = "vga" in lspci and "intel" in lspci

        if not has_nvidia:
            os.environ["HAS_NVIDIA_GPU"] = "0"
            return ok

        self.runner.ui.run_cmd("nala update",
            "nala", "update", sudo=True)

        if has_intel:
            ok &= self.runner.ui.run_cmd("install nvidia+prime",
                "nala", "install", "-y",
                "nvidia-driver-595-open", "nvidia-prime", "nvidia-settings",
                sudo=True)
            self.runner.ui.run_cmd("prime-select",
                "prime-select", "on-demand", sudo=True)
        else:
            ok &= self.runner.ui.run_cmd("install nvidia",
                "nala", "install", "-y",
                "nvidia-driver-595-open", "nvidia-settings",
                sudo=True)

        for svc in ("nvidia-suspend", "nvidia-resume", "nvidia-hibernate"):
            self.runner.ui.run_cmd(f"enable {svc}",
                "systemctl", "enable", svc, sudo=True)

        os.environ["HAS_NVIDIA_GPU"] = "1"
        if has_intel:
            os.environ["HAS_NVIDIA_INTEL"] = "1"

        return ok
