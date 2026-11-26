"""Apoyos de prueba para la numeración correlativa de compras (TASK-numeracion-correlativa-compras)."""
from uuid import UUID

from modules.purchases.domain.purchase import PurchaseNumber

_PERIOD_ID = UUID('00000000-0000-4000-8000-0000000000c6')
_numbers = iter(range(1, 10_000_000))


def fake_number() -> PurchaseNumber:
    """Número de compra único en todo el proceso de pruebas (serie ficticia del período 2026)."""
    return PurchaseNumber(_PERIOD_ID, '2026', next(_numbers))


class FakeNumbering:
    """Puerto de numeración en memoria: devuelve números únicos; puede simular la falta o el cierre del período."""

    def __init__(self, error=None):
        self.error = error
        self.calls: list = []

    def next_number(self, purchase_date):
        self.calls.append(purchase_date)
        if self.error is not None:
            raise self.error
        return fake_number()
