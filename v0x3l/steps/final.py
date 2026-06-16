# Step 5: Entorno (gestor de escritorio DMS)

import os
from v0x3l.steps.base import BaseStep


class DesktopStep(BaseStep):
    number = 5
    title = "Entorno"
    category = "final"

    def run(self) -> bool:
        user = os.environ.get("SUDO_USER", os.environ.get("USER", ""))
        return self.runner.ui.run_raw_cmd(
            "sudo", "-u", user, "bash", "-c",
            "curl -fsSL https://install.danklinux.com | bash")
