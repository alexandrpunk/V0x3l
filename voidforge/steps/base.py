# Clase base para todos los steps

from abc import ABC, abstractmethod
from typing import Optional


class BaseStep(ABC):
    """Clase base para todos los pasos de instalacion."""

    number: int = 0
    title: str = ""
    category: str = ""

    def __init__(self, runner: "StepRunner"):
        self.runner = runner
        self.shell = runner.shell

    def should_skip(self, skip_steps: set[int]) -> bool:
        return self.number in skip_steps

    @abstractmethod
    def run(self) -> bool:
        """Ejecuta el paso. Retorna True si fue exitoso."""
        ...
