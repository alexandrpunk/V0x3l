# Steps 2-3: kernel y GPU

from voidforge.steps.base import BaseStep


class KernelStep(BaseStep):
    number = 2
    title = "Instalando Kernel XanMod"
    category = "drivers"

    def run(self) -> bool:
        ok = True

        if not __import__("os").path.exists("/etc/apt/sources.list.d/xanmod-release.list"):
            ok &= self.runner.ui.run_cmd("xanmod key",
                "wget", "-qO-", "https://dl.xanmod.org/archive.key",
                sudo=False)

            ok &= self.runner.ui.run_cmd("xanmod key import",
                "bash", "-c",
                "wget -qO- https://dl.xanmod.org/archive.key | "
                "gpg --dearmor -vo /etc/apt/keyrings/xanmod-archive-keyring.gpg",
                sudo=True)

            import subprocess
            codename = subprocess.run(
                ["lsb_release", "-sc"],
                capture_output=True, text=True
            ).stdout.strip()

            ok &= self.runner.ui.run_cmd("xanmod repo",
                "bash", "-c",
                f'echo "deb [signed-by=/etc/apt/keyrings/xanmod-archive-keyring.gpg] '
                f'https://deb.xanmod.org {codename} main non-free" | '
                "tee /etc/apt/sources.list.d/xanmod-release.list",
                sudo=True)

            ok &= self.runner.ui.run_cmd("nala update", "nala", "update", sudo=True)

        # Verificar si ya esta instalado
        import subprocess
        current_kernel = subprocess.run(
            ["uname", "-r"], capture_output=True, text=True
        ).stdout

        if "xanmod" not in current_kernel:
            ok &= self.runner.ui.run_cmd("install xanmod",
                "nala", "install", "-y", "linux-xanmod-x64v3", sudo=True)
            ok &= self.runner.ui.run_cmd("install dkms",
                "nala", "install", "--no-install-recommends", "-y",
                "dkms", "libelf-dev", "clang", "lld", "llvm", sudo=True)

        return ok


class GPUStep(BaseStep):
    number = 3
    title = "Detectando GPU NVIDIA e instalando drivers"
    category = "drivers"

    def run(self) -> bool:
        ok = True

        # Detectar GPU
        import subprocess
        lspci = subprocess.run(
            ["lspci", "-nn"], capture_output=True, text=True
        ).stdout.lower()

        has_nvidia = "nvidia" in lspci
        has_intel = "vga" in lspci and "intel" in lspci

        if not has_nvidia:
            import os
            os.environ["HAS_NVIDIA_GPU"] = "0"
            return True

        ok &= self.runner.ui.run_cmd("nala update", "nala", "update", sudo=True)

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

        # Habilitar servicios suspend/resume
        for svc in ("nvidia-suspend", "nvidia-resume", "nvidia-hibernate"):
            self.runner.ui.run_cmd(f"enable {svc}",
                "systemctl", "enable", svc, sudo=True)

        import os
        os.environ["HAS_NVIDIA_GPU"] = "1"
        os.environ["HAS_NVIDIA_INTEL"] = "1" if has_intel else "0"

        return ok
