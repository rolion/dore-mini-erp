"""Puertos que Expenses necesita del exterior (el reloj y las clasificaciones de Contabilidad)."""
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol
from uuid import UUID


class Clock(Protocol):
    def now(self) -> datetime: ...


@dataclass(frozen=True)
class ClassificationInfo:
    id: UUID
    name: str
    direction: str
    active: bool


class ClassificationGateway(Protocol):
    """Clasificaciones de egreso de Contabilidad; su implementación vive en `infrastructure/adapters.py`."""

    def validate_expense_classification(self, classification_id: UUID) -> ClassificationInfo:
        """Lanza `ExpenseValidationError` (`classification_id`) si no es de la empresa, está inactiva o no es de egreso."""
        ...

    def describe(self, classification_ids: Iterable[UUID]) -> dict[UUID, ClassificationInfo]: ...

    def is_covered(self, on: date) -> bool:
        """¿Contabilidad debe crear movimiento para una operación con esa fecha efectiva?"""
        ...
