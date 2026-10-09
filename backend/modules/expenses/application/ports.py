"""Puertos que Expenses necesita del exterior (solo el reloj)."""
from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...
