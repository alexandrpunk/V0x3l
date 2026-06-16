# Step 4: Apariencia (iconos + cursors + Plymouth + GRUB)

import os
import subprocess
import tempfile
import shutil
from v0x3l.steps.base import BaseStep
from v0x3l.config import (
    PLYMOUTH_THEME_SRC, PLYMOUTH_THEME_NAME,
    CURSOR_THEME_SRC, CURSOR_THEME_NAME,
    GRUB_THEME_SRC, GRUB_THEME_NAME,
    COLLOID_DIR, COLLOID_THEME_NAME,
)


class AppearanceStep(BaseStep):
    number = 4
    title = "Apariencia"
    category = "theming"

    def run(self) -> bool:
        ok = True
        has_nvidia = os.environ.get("HAS_NVIDIA_GPU", "0") == "1"

        # ── Catppuccin cursors ──
        if not os.path.exists(f"/usr/share/icons/{CURSOR_THEME_NAME}"):
            if os.path.isfile(CURSOR_THEME_SRC):
                tmpdir = tempfile.mkdtemp()
                shutil.copy(CURSOR_THEME_SRC, f"{tmpdir}/cursors.zip")
                self.runner.ui.run_cmd("extract cursors",
                    "unzip", "-q", f"{tmpdir}/cursors.zip", "-d", "/usr/share/icons/", sudo=True)
                subprocess.run(["rm", "-rf", tmpdir])
            else:
                ok = False

        # ── Colloid icons ──
        if not os.path.exists(f"/usr/share/icons/{COLLOID_THEME_NAME}") and os.path.isdir(COLLOID_DIR):
            ok &= self.runner.ui.run_cmd("install Colloid",
                "bash", f"{COLLOID_DIR}/install.sh", "-b", "-s",
                "catppuccin", "-t", "green", sudo=True)

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
        grub_theme = f"/usr/share/grub/themes/{GRUB_THEME_NAME}"
        if os.path.isdir(GRUB_THEME_SRC):
            os.makedirs(grub_theme, exist_ok=True)
            if not os.path.exists(f"{grub_theme}/theme.txt"):
                self.runner.ui.run_cmd("copy GRUB theme",
                    "cp", "-r", f"{GRUB_THEME_SRC}/.", f"{grub_theme}/", sudo=True)

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
