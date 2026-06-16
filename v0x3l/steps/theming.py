# Step 4: Apariencia (iconos + Plymouth + GRUB)

import os
import subprocess
from v0x3l.steps.base import BaseStep
from v0x3l.config import PLYMOUTH_THEME_SRC, PLYMOUTH_THEME_NAME


class AppearanceStep(BaseStep):
    number = 4
    title = "Apariencia"
    category = "theming"

    def run(self) -> bool:
        ok = True
        has_nvidia = os.environ.get("HAS_NVIDIA_GPU", "0") == "1"

        # ── Colloid icons ──
        if not os.path.exists("/usr/share/icons/Colloid-catppuccin-green-dark"):
            import tempfile
            tmpdir = tempfile.mkdtemp()
            ok &= self.runner.ui.run_cmd("clone Colloid",
                "git", "clone", "--depth", "1",
                "https://github.com/vinceliuice/Colloid-icon-theme.git",
                tmpdir, sudo=False)
            if ok:
                ok &= self.runner.ui.run_cmd("install Colloid",
                    "bash", f"{tmpdir}/install.sh", "-b", "-s",
                    "catppuccin", "-t", "green", sudo=True)
            subprocess.run(["rm", "-rf", tmpdir])

        # ── Plymouth ──
        self.runner.ui.run_cmd("install plymouth",
            "nala", "install", "-y", "plymouth", "plymouth-themes",
            sudo=True)
        os.makedirs("/usr/share/plymouth/themes", exist_ok=True)

        theme_src = PLYMOUTH_THEME_SRC
        theme_name = PLYMOUTH_THEME_NAME
        theme_dir = f"/usr/share/plymouth/themes/{theme_name}"
        theme_file = f"{theme_dir}/{theme_name}.plymouth"

        if os.path.isdir(theme_src) and os.path.exists(
                f"{theme_src}/{theme_name}.plymouth"):
            os.makedirs(theme_dir, exist_ok=True)
            if not os.path.isfile(theme_file):
                self.runner.ui.run_cmd("copy plymouth theme",
                    "cp", "-r", f"{theme_src}/.", f"{theme_dir}/", sudo=True)
            if os.path.isfile(theme_file):
                self.runner.ui.run_cmd("plymouth alternatives",
                    "update-alternatives", "--install",
                    "/usr/share/plymouth/themes/default.plymouth",
                    "default.plymouth", theme_file, "100", sudo=True)
                self.runner.ui.run_cmd("plymouth set",
                    "update-alternatives", "--set",
                    "default.plymouth", theme_file, sudo=True)

        # ── GRUB theme ──
        grub_theme = "/usr/share/grub/themes/grub-theme-vimix-very-dark-blue"
        if not os.path.exists(f"{grub_theme}/theme.txt"):
            import tempfile
            tmpdir = tempfile.mkdtemp()
            self.runner.ui.run_cmd("clone GRUB theme",
                "git", "clone", "--depth", "1",
                "https://github.com/trueNAHO/"
                "grub2-theme-vimix-very-dark-blue.git",
                tmpdir, sudo=False)
            subprocess.run(["install", "--directory", "--mode", "755",
                            grub_theme], capture_output=True)
            subprocess.run(["cp", "--no-preserve=ownership", "--recursive",
                            f"{tmpdir}/src/.", grub_theme],
                           capture_output=True)
            subprocess.run(["rm", "-rf", tmpdir])

        grub_cfg = "/etc/default/grub"

        # 1. GRUB_THEME (obligatorio para que GRUB use el tema visual)
        theme_line = f'GRUB_THEME="{grub_theme}/theme.txt"'
        self.runner.ui.run_cmd("set GRUB_THEME", "bash", "-c",
            f'grep -q "^GRUB_THEME=" "{grub_cfg}" && '
            f'sed -i "s|^GRUB_THEME=.*|{theme_line}|" "{grub_cfg}" || '
            f'echo "{theme_line}" >> "{grub_cfg}"',
            sudo=True)

        # 2. GRUB_GFXPAYLOAD_LINUX (necesario para Plymouth)
        self.runner.ui.run_cmd("set gfxpayload", "bash", "-c",
            f'grep -q "^GRUB_GFXPAYLOAD_LINUX=" "{grub_cfg}" || '
            f'echo "GRUB_GFXPAYLOAD_LINUX=keep" >> "{grub_cfg}"',
            sudo=True)

        # 3. Kernel params: quiet splash + NVIDIA si corresponde
        if has_nvidia:
            self.runner.ui.run_cmd("set kernel nvidia params", "bash", "-c",
                'sed -i "s/^GRUB_CMDLINE_LINUX_DEFAULT=.*/'
                'GRUB_CMDLINE_LINUX_DEFAULT=\\"quiet splash '
                'nvidia-drm.modeset=1 nvidia-drm.fbdev=1 '
                'nvidia.NVreg_PreserveVideoMemoryAllocations=1\\"/"'
                f' "{grub_cfg}"',
                sudo=True)
        else:
            self.runner.ui.run_cmd("set kernel splash", "bash", "-c",
                'sed -i "s/^GRUB_CMDLINE_LINUX_DEFAULT=.*/'
                'GRUB_CMDLINE_LINUX_DEFAULT=\\"quiet splash\\"/"'
                f' "{grub_cfg}"',
                sudo=True)

        os.makedirs("/etc/initramfs-tools/conf.d", exist_ok=True)
        with open("/etc/initramfs-tools/conf.d/splash", "w") as f:
            f.write("FRAMEBUFFER=y\n")
        if has_nvidia:
            for mod in ("nvidia", "nvidia-drm", "nvidia-modeset", "nvidia-uvm"):
                with open("/etc/initramfs-tools/modules", "a") as f:
                    f.write(f"{mod}\n")

        self.runner.ui.run_cmd("grub-mkconfig",
            "grub-mkconfig", "-o", "/boot/grub/grub.cfg", sudo=True)
        self.runner.ui.run_cmd("update-initramfs",
            "update-initramfs", "-u", sudo=True)
        self.runner.ui.run_cmd("nala autoremove",
            "nala", "autoremove", "-y", sudo=True)
        self.runner.ui.run_cmd("nala clean",
            "nala", "clean", sudo=True)

        return ok
