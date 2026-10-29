# Step 1: Rendimiento y drivers (kernel XanMod + GPU NVIDIA + Optimus)

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

        def write_file_if_missing(path: str, content: str, mode: int = 0o644) -> bool:
            try:
                if not os.path.exists(path):
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, "w") as f:
                        f.write(content)
                    os.chmod(path, mode)
                    print(f"INFO escrito: {path}")
                    return True
                return False
            except Exception as e:
                print(f"ERROR escribiendo {path}: {type(e).__name__}: {e}")
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

            if not _which("dkms"):
                print("WARN dkms no instalado; modulos kernel pueden no compilar")

        # ── GPU detection ──
        # Filtrar SOLO lineas VGA/3D/display (evita falsos positivos en lspci).
        try:
            lspci = subprocess.run(
                ["lspci", "-nn"], capture_output=True, text=True
            ).stdout.lower()
            gpu_lines = [line for line in lspci.splitlines()
                         if any(tok in line for tok in ("vga", "3d", "display"))]
            has_nvidia = any("nvidia" in line for line in gpu_lines)
            has_intel = any("intel" in line for line in gpu_lines)
            has_amd = any("amd" in line or "ati" in line for line in gpu_lines)
        except FileNotFoundError:
            has_nvidia = os.environ.get("HAS_NVIDIA_GPU", "0") == "1"
            has_intel = os.environ.get("HAS_INTEL_GPU", "0") == "1"
            has_amd = os.environ.get("HAS_AMD_GPU", "0") == "1"

        # Optimus = NVIDIA + Intel/AMD integrado
        is_optimus = has_nvidia and (has_intel or has_amd)

        if not has_nvidia:
            os.environ["HAS_NVIDIA_GPU"] = "0"
            os.environ["HAS_OPTIMUS"] = "0"
            return ok

        os.environ["HAS_NVIDIA_GPU"] = "1"
        os.environ["HAS_OPTIMUS"] = "1" if is_optimus else "0"

        if is_optimus:
            print(f"INFO Optimus detectado: NVIDIA + {'Intel' if has_intel else 'AMD'} iGPU")

        ok &= run_critical("nala update", "nala", "update", sudo=True)

        # ── Detectar driver NVIDIA recomendado ──
        driver_pkgs = ["nvidia-driver-560"]  # fallback
        try:
            result = subprocess.run(
                ["ubuntu-drivers", "devices"], capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.splitlines():
                    if "nvidia-driver-" in line and "recommended" in line:
                        parts = line.split()
                        for p in parts:
                            if p.startswith("nvidia-driver-"):
                                driver_pkgs = [p]
                                print(f"INFO driver NVIDIA recomendado: {p}")
                                break
        except Exception:
            pass

        # ── Paquetes base NVIDIA ──
        base_nvidia = [
            *driver_pkgs,
            "nvidia-settings",
            "nvidia-prime",           # PRIME offload (Intel -> NVIDIA)
            "libnvidia-compute-*",    # compute para CUDA/ComfyUI
            "libvdpau1", "libva2",    # VA-API/VDPAU para video
        ]

        if is_optimus:
            # Para Optimus en Wayland: optimus-manager (mejor que nvidia-prime solo)
            base_nvidia.extend([
                "optimus-manager",           # Gestor GPU switching
                "optimus-manager-qt",        # GUI opcional
            ])

        ok &= run_critical("install nvidia drivers + optimus",
            "nala", "install", "--no-install-recommends", "-y",
            *base_nvidia, sudo=True)

        # ── Configuración Optimus para Wayland ──
        if is_optimus:
            # 1) Kernel parameter: nvidia-drm.modeset=1 (obligatorio para Wayland)
            grub_file = "/etc/default/grub"
            run_nonfatal("grub nvidia-drm.modeset=1",
                "sed", "-i",
                's/^GRUB_CMDLINE_LINUX_DEFAULT="/GRUB_CMDLINE_LINUX_DEFAULT="nvidia-drm.modeset=1 /',
                grub_file, sudo=True)

            # 2) Añadir resume= para hibernación si hay swap
            try:
                swap_uuid = subprocess.run(
                    ["findmnt", "-no", "UUID", "/dev/mapper/cryptswap"],
                    capture_output=True, text=True, check=False
                ).stdout.strip()
                if not swap_uuid:
                    # fallback: buscar swap UUID
                    swap_uuid = subprocess.run(
                        ["blkid", "-s", "UUID", "-o", "value", "-t", "TYPE=swap"],
                        capture_output=True, text=True, check=False
                    ).stdout.strip().splitlines()[0]
            except Exception:
                swap_uuid = ""

            if swap_uuid:
                run_nonfatal("grub resume swap",
                    "sed", "-i",
                    f's/^GRUB_CMDLINE_LINUX_DEFAULT="/GRUB_CMDLINE_LINUX_DEFAULT="resume=UUID={swap_uuid} /',
                    grub_file, sudo=True)

            run_nonfatal("update-grub", "update-grub", sudo=True)

            # 3) modprobe.d: forzar nvidia-drm modeset y desactivar runtime PM problemático
            write_file_if_missing("/etc/modprobe.d/nvidia.conf", (
                "# Optimus Wayland config\n"
                "options nvidia_drm modeset=1 fbdev=1\n"
                "options nvidia NVreg_DynamicPowerManagement=0x02\n"
                "# Desactivar runtime PM para evitar cuelgues en suspend\n"
                "options nvidia NVreg_EnableGpuFirmware=0\n"
            ))

            # 4) Variables de entorno para PRIME offload (Intel -> NVIDIA)
            # Para que apps usen NVIDIA: __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia
            env_file = "/etc/environment.d/99-nvidia-prime.conf"
            write_file_if_missing(env_file, (
                "# NVIDIA PRIME Offload - Intel iGPU por defecto, NVIDIA on-demand\n"
                "# Para usar NVIDIA: prime-run <app>  O  __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia <app>\n"
                "__NV_PRIME_RENDER_OFFLOAD=0\n"
                "__GLX_VENDOR_LIBRARY_NAME=\n"
                "__VK_LAYER_NV_optimus=NVIDIA_only\n"
            ))

            # 5) Configurar optimus-manager (startup con Intel, switch manual a NVIDIA)
            write_file_if_missing("/etc/optimus-manager/optimus-manager.conf", (
                "[optimus]\n"
                "# GPU de inicio: integrated (Intel) para ahorrar bateria\n"
                "startup_mode=intel\n"
                "\n"
                "[nvidia]\n"
                "# Permitir que NVIDIA se apague cuando no se use\n"
                "power_control=auto\n"
                "\n"
                "[intel]\n"
                "power_control=auto\n"
                "\n"
                "[xorg]\n"
                "# Config Xorg para NVIDIA cuando se hace switch\n"
                "server_name=Xorg\n"
            ), mode=0o644)

            # 6) Habilitar servicio optimus-manager (systemd)
            run_nonfatal("enable optimus-manager",
                "systemctl", "enable", "--now", "optimus-manager.service", sudo=True)

        # ── nvidia-suspend/hibernate/resume (para laptops) ──
        nvidia_suspend_src = "/lib/systemd/system-sleep/nvidia-suspend.sh"
        if os.path.exists(nvidia_suspend_src):
            ok &= run_nonfatal("enable nvidia-suspend",
                "systemctl", "enable", "nvidia-suspend", "nvidia-hibernate",
                "nvidia-resume", sudo=True)

        # ── Verificación post-instalación ──
        try:
            subprocess.run(["nvidia-smi"], capture_output=True, check=True)
            print("INFO nvidia-smi: GPU detectada correctamente")
        except Exception:
            print("WARN nvidia-smi fallo; revisar drivers NVIDIA")

        # ── Intel iGPU: paquetes para aceleración video/VA-API ──
        if has_intel:
            print("INFO Intel iGPU detectada: instalando paquetes VA-API / media-driver")
            ok &= run_critical("install intel media driver",
                "nala", "install", "--no-install-recommends", "-y",
                "intel-media-va-driver",      # VA-API para video encode/decode
                "intel-gpu-tools",            # intel_gpu_top, etc.
                "va-driver-all",              # VA-API backend genérico
                "vainfo",                     # Verificar VA-API
                "libva2", "libva-drm2",
                sudo=True)

            # Configurar i915 para mejor rendimiento/energía
            write_file_if_missing("/etc/modprobe.d/i915.conf", (
                "# Intel iGPU config para Optimus\n"
                "options i915 enable_guc=3 enable_fbc=1 enable_dc=1\n"
            ))

        # ── AMD GPU (si aplica) ──
        if has_amd:
            print("INFO AMD GPU detectada: instalando paquetes mesa/vaapi")
            ok &= run_critical("install amd mesa vaapi",
                "nala", "install", "--no-install-recommends", "-y",
                "mesa-va-drivers", "mesa-vdpau-drivers",
                "libva2", "vainfo",
                sudo=True)

        # ── Resumen final ──
        if is_optimus:
            print("\n=== CONFIGURACION OPTIMUS COMPLETADA ===")
            print("Escritorio/Video -> Intel iGPU (ahorro energia)")
            print("ComfyUI/Steam/Juegos -> NVIDIA via: prime-run <app>")
            print("Ejemplo: prime-run comfyui   O   prime-run steam")
            print("Alternativa: optimus-manager --switch nvidia (requiere relogin)")
            print("Verificar: glxinfo | grep 'OpenGL renderer'")
            print("==========================================\n")

        return ok