"""Puertos que Expenses necesita del exterior (el reloj, las clasificaciones y los asientos de Contabilidad)."""
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


@dataclass(frozen=True)
class PostedAccounts:
    """Cuentas con que quedó contabilizado el gasto (instantánea que se guarda en él)."""
    expense_account_id: UUID
    payment_account_id: UUID


class ExpensePostingGateway(Protocol):
    """Asiento de partida doble del gasto (Debe cuenta de gasto / Haber Caja-Banco); su implementación vive en
    `infrastructure/adapters.py`. Todo corre dentro de la transacción del llamante."""

    def is_covered(self, on: date) -> bool:
        """¿Debe contabilizarse un gasto con esa fecha? Sin cobertura no se exigen cuentas."""
        ...

    def validate_accounts(self, expense_account_id: UUID | None, payment_account_id: UUID | None) -> None:
        """Lanza `ExpenseValidationError` (`expense_account_id` / `payment_account_id`) si una cuenta elegida no sirve."""
        ...

    def post(self, expense, category_name: str, expense_account_id: UUID | None,
             payment_account_id: UUID | None) -> PostedAccounts | None:
        """Contabiliza el gasto (idempotente por gasto). Lanza `ExpensePostingError` si Contabilidad no puede."""
        ...

    def reverse(self, expense_id: UUID, actor_id: int | None = None, actor_name: str = '') -> None:
        """Revierte el asiento del gasto con fecha de hoy, a nombre de quien anula (idempotente). Sin asiento no hace
        nada. Lanza `ExpensePostingError`."""
        ...
