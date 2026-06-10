# Step 15: DMS (Dank Linux)

import os
from voidforge.steps.base import BaseStep


class DMSStep(BaseStep):
    number = 15
    title = "Instalando DMS (Dank Linux)"
    category = "final"

    def run(self) -> bool:
        user = os.environ.get("SUDO_USER", os.environ.get("USER", ""))
        return self.runner.ui.run_cmd("DMS installer",
            "sudo", "-u", user, "bash", "-c",
            "curl -fsSL https://install.danklinux.com | bash",
            sudo=False, timeout=120, capture_output=False)
