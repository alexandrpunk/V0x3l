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

        # ── Kernel XanMod (repo agregado en Step 0) ──
        current_kernel = subprocess.run(
            ["uname", "-r"], capture_output=True, text=True
        ).stdout

        if "xanmod" not in current_kernel:
            ok &= self.runner.ui.run_cmd("install xanmod",
                "nala", "install", "-y", "linux-xanmod-edge-x64v3", sudo=True)
            ok &= self.runner.ui.run_cmd("install dkms",
                "nala", "install", "--no-install-recommends", "-y",
                "dkms", "libelf-dev", "clang", "lld", "llvm", sudo=True)

        # ── GPU detection ──
        # Filtrar SOLO lineas VGA/3D/display (antes buscaba "intel" en todo el
        # output de lspci, que incluye NICs, Wi-Fi, etc. → falsos positivos).
        lspci = subprocess.run(
            ["lspci", "-nn"], capture_output=True, text=True
        ).stdout.lower()
        gpu_lines = [l for l in lspci.splitlines()
                     if any(x in l for x in ("vga", "3d", "display"))]

        has_nvidia = any("nvidia" in l for l in gpu_lines)
        has_intel = any("intel" in l for l in gpu_lines)

        if not has_nvidia:
            os.environ["HAS_NVIDIA_GPU"] = "0"
            return ok

        ok &= self.runner.ui.run_cmd("nala update",
            "nala", "update", sudo=True)

        if has_intel:
            ok &= self.runner.ui.run_cmd("install nvidia+prime",
                "nala", "install", "-y",
                "nvidia-driver-595-open", "nvidia-prime", "nvidia-settings",
                sudo=True)
            ok &= self.runner.ui.run_cmd("prime-select",
                "prime-select", "on-demand", sudo=True)
        else:
            ok &= self.runner.ui.run_cmd("install nvidia",
                "nala", "install", "-y",
                "nvidia-driver-595-open", "nvidia-settings",
                sudo=True)

        for svc in ("nvidia-suspend", "nvidia-resume", "nvidia-hibernate"):
            ok &= self.runner.ui.run_cmd(f"enable {svc}",
                "systemctl", "enable", svc, sudo=True)

        os.environ["HAS_NVIDIA_GPU"] = "1"
        if has_intel:
            os.environ["HAS_NVIDIA_INTEL"] = "1"

        return ok
