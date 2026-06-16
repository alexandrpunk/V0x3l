# Step runner - ejecuta steps secuencialmente, maneja checkpoint

import os
from typing import Optional
from v0x3l.config import CHECKPOINT_FILE


class StepRunner:
    """Orquesta la ejecucion de los steps."""

    def __init__(self, shell, ui):
        self.shell = shell
        self.ui = ui
        self.skip_steps: set[int] = set()
        self.steps: list = []
        self._load_checkpoint()

    def _load_checkpoint(self) -> Optional[int]:
        if os.path.exists(CHECKPOINT_FILE):
            try:
                with open(CHECKPOINT_FILE) as f:
                    return int(f.read().strip())
            except (ValueError, OSError):
                pass
        return None

    def save_checkpoint(self, step_num: int):
        with open(CHECKPOINT_FILE, "w") as f:
            f.write(str(step_num))

    def clear_checkpoint(self):
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)

    def register_step(self, step):
        self.steps.append(step)
        self.steps.sort(key=lambda s: s.number)

    def run_all(self, resume: bool = False):
        """Ejecuta todos los steps secuencialmente."""
        if resume:
            cp = self._load_checkpoint()
            start = (cp + 1) if cp is not None else 0
        else:
            start = 0

        for step in self.steps:
            if step.number < start:
                continue
            if step.should_skip(self.skip_steps):
                continue
            if not self.ui.run_step(step):
                return False

        self.clear_checkpoint()
        if hasattr(self.ui, 'on_all_done'):
            self.ui.on_all_done()
        return True

    def run_single(self, step_num: int) -> bool:
        """Ejecuta un step especifico."""
        for step in self.steps:
            if step.number == step_num:
                return self.ui.run_step(step)
        return False

    def run_range(self, start: int, end: int) -> bool:
        """Ejecuta un rango de steps."""
        for step in self.steps:
            if step.number < start or step.number > end:
                continue
            if step.should_skip(self.skip_steps):
                continue
            if not self.ui.run_step(step):
                return False
        return True

    def get_checkpoint_status(self) -> str:
        cp = self._load_checkpoint()
        if cp is not None:
            return f"Paso {cp} completado"
        return "Sin progreso"
