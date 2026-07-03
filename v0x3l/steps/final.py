# Step 5: Entorno — Noctalia Shell v4 + SwayFX

import os
from v0x3l.steps.base import BaseStep


class DesktopStep(BaseStep):
    number = 5
    title = "Entorno"
    category = "final"

    def run(self) -> bool:
        user = os.environ.get("SUDO_USER", os.environ.get("USER", ""))
        success = True

        # ── Noctalia Shell v4 ──────────────────────────────────────
        noctalia_installed = os.path.exists("/usr/bin/noctalia-shell") or \
                             os.path.exists("/usr/bin/noctalia-qs")

        if not noctalia_installed:
            # Import GPG key
            ok = self.runner.ui.run_cmd(
                "Importing Noctalia GPG key",
                "bash", "-c",
                "curl -fsSL https://pkg.noctalia.dev/gpg.key | "
                "gpg --dearmor -o /etc/apt/keyrings/noctalia.gpg",
                sudo=True,
            )
            if not ok:
                success = False

            # Add APT repository
            if ok:
                ok = self.runner.ui.run_cmd(
                    "Adding Noctalia APT repository",
                    "bash", "-c",
                    "echo 'deb [signed-by=/etc/apt/keyrings/noctalia.gpg] "
                    "https://pkg.noctalia.dev/apt trixie main' "
                    "> /etc/apt/sources.list.d/noctalia.list",
                    sudo=True,
                )
                if not ok:
                    success = False

            # Update package lists
            if ok:
                ok = self.runner.ui.run_cmd(
                    "Updating package lists (nala)",
                    "nala", "update",
                    sudo=True,
                )
                if not ok:
                    success = False

            # Install noctalia-shell
            if ok:
                ok = self.runner.ui.run_cmd(
                    "Installing noctalia-shell",
                    "nala", "install", "-y", "noctalia-shell",
                    sudo=True,
                )
                if not ok:
                    success = False
        else:
            self.runner.ui.run_cmd("Noctalia Shell already installed — skipping", "true")

        # ── SwayFX ────────────────────────────────────────────────
        sway_installed = os.path.exists("/usr/bin/sway") or \
                         os.path.exists("/usr/local/bin/sway")

        if not sway_installed:
            # Clone setup repo
            ok = self.runner.ui.run_cmd(
                "Cloning SwayFX setup repository",
                "git", "clone",
                "https://codeberg.org/justaguylinux/swayfx-setup.git",
                "/tmp/swayfx-setup",
            )
            if not ok:
                success = False

            # Run the installer (interactive — use raw terminal)
            if ok:
                ok = self.runner.ui.run_raw_cmd(
                    "bash", "/tmp/swayfx-setup/install.sh",
                )
                if not ok:
                    success = False

            # Refresh shared library cache
            if ok:
                ok = self.runner.ui.run_cmd(
                    "Running ldconfig",
                    "ldconfig",
                    sudo=True,
                )
                if not ok:
                    success = False
        else:
            self.runner.ui.run_cmd("Sway already installed — skipping", "true")

        return success
