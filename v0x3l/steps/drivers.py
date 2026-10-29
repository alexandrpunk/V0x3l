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

        # ---- Helpers ----
        def run_critical(desc: str, *args, **kwargs) -> bool:
            try:
                result = self.runner.ui.run_cmd(desc, *args, **kwargs)
                if not result:
                    print(f"ERROR {desc}: comando fallo (critico)")
                return result
            except Exception as e:
                print(f"ERROR {desc}: excepcion {type(e).__name__}: {e}")
                return False

        def run_nonfatal(desc: str, *args, **kwargs) -> bool:
            try:
                result = self.runner.ui.run_cmd(desc, *args, **kwargs)
                if not result:
                    print(f"WARN {desc}: comando fallo (no fatal)")
                return result
            except Exception as e:
                print(f"WARN {desc}: excepcion {type(e).__name__}: {e}")
                return False

        def _which(cmd: str) -> bool:
            try:
                subprocess.run(["which", cmd], capture_output=True, check=True)
                return True
            except Exception:
                return False

        # ── Kernel XanMod (repo agregado en Step 0) ──
        current_kernel = subprocess.run(
            ["uname", "-r"], capture_output=True, text=True
        ).stdout

        if "xanmod" not in current_kernel:
            ok &= run_critical("install xanmod + dkms toolchain",
                "nala", "install", "--no-install-recommends", "-y",
                "linux-xanmod-edge-x64v3",
                "dkms", "libelf-dev", "clang", "lld", "llvm", sudo=True)

            # Verificar instalación
            if not _which("dkms"):
                print("WARN dkms no instalado; módulos kernel pueden no compilar")

        # ── GPU detection ──
        # Filtrar SOLO lineas VGA/3D/display (antes buscaba "intel" en todo el
        # output de lspci, que incluye NICs, Wi-Fi, etc. -> falsos positivos).
        try:
            lspci = subprocess.run(
                ["lspci", "-nn"], capture_output=True, text=True
            ).stdout.lower()
            gpu_lines = [line for line in lspci.splitlines()
                         if any(tok in line for tok in ("vga", "3d", "display"))]
            has_nvidia = any("nvidia" in line for line in gpu_lines)
            has_intel = any("intel" in line for line in gpu_lines)
        except FileNotFoundError:
            # lspci no disponible (pciutils no instalado): asumir nada
            has_nvidia = os.environ.get("HAS_NVIDIA_GPU", "0") == "1"
            has_intel = os.environ.get("HAS_NVIDIA_INTEL", "0") == "1"

        if not has_nvidia:
            os.environ["HAS_NVIDIA_GPU"] = "0"
            return ok

        os.environ["HAS_NVIDIA_GPU"] = "1"

        ok &= run_critical("nala update", "nala", "update", sudo=True)

        # Detectar versión de driver recomendada
        # Primero intentar ubuntu-drivers
        driver_pkgs = ["nvidia-driver-560"]
        try:
            result = subprocess.run(
                ["ubuntu-drivers", "devices"], capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and result.stdout:
                # Parsear salida para driver recomendado
                for line in result.stdout.splitlines():
                    if "nvidia-driver-" in line and "recommended" in line:
                        parts = line.split()
                        for p in parts:
                            if p.startswith("nvidia-driver-"):
                                driver_pkgs = [p]
                                break
        except Exception:
            pass

        ok &= run_critical("install nvidia drivers",
            "nala", "install", "--no-install-recommends", "-y",
            *driver_pkgs, sudo=True)

        # Configurar nvidia-suspend para suspend/resume
        nvidia_suspend_src = "/lib/systemd/system-sleep/nvidia-suspend.sh"
        if os.path.exists(nvidia_suspend_src):
            ok &= run_nonfatal("enable nvidia-suspend",
                "systemctl", "enable", "nvidia-suspend", "nvidia-hibernate",
                "nvidia-resume", sudo=True)

        # Verificar instalación de drivers
        try:
            subprocess.run(["nvidia-smi"], capture_output=True, check=True)
            print("INFO nvidia-smi: GPU detectada correctamente")
        except Exception:
            print("WARN nvidia-smi fallo; revisar drivers NVIDIA")

        return ok