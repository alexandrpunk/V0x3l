# Step 5: Entorno (gestor de escritorio DMS)

import os
from voidforge.steps.base import BaseStep


class DesktopStep(BaseStep):
    number = 5
    title = "Entorno"
    category = "final"

    def run(self) -> bool:
        user = os.environ.get("SUDO_USER", os.environ.get("USER", ""))
        ok = self.runner.ui.run_cmd("DMS installer",
            "sudo", "-u", user, "bash", "-c",
            "curl -fsSL https://install.danklinux.com | bash",
            sudo=False, timeout=300, capture_output=True)
        if not ok:
            from voidforge.shell import log as shell_log
            shell_log("DMS installer retorno error")
        return ok
