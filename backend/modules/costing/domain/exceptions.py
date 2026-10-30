from decimal import Decimal
from uuid import UUID


class ValuationValidationError(Exception):
    """Errores de forma y de regla por campo (`{'lines': [{campo: [mensaje]}]}` o `{campo: [mensaje]}`)."""

    def __init__(self, errors: dict[str, object]):
        super().__init__(errors)
        self.errors = errors


class ValuationAlreadyAdopted(Exception):
    """La empresa ya tiene una adopción distinta a la que se intenta registrar."""

    code = 'valuation_already_adopted'

    def __init__(self):
        super().__init__('La empresa ya tiene una valoración inicial adoptada.')


class AdoptionIdReused(Exception):
    """La clave de la adopción ya se usó con otro contenido."""

    code = 'adoption_id_reused'

    def __init__(self):
        super().__init__('La clave de adopción ya se usó con otros valores.')


class NegativeStock(Exception):
    """Hay saldos negativos: no se puede adoptar. `blockers` lista producto, almacén y cantidad."""

    code = 'negative_stock'

    def __init__(self, blockers: list):
        super().__init__('No se puede adoptar la valoración con stock negativo.')
        self.blockers = blockers


class StockChanged(Exception):
    """Las existencias no coinciden con las cantidades conciliadas enviadas."""

    code = 'stock_changed'

    def __init__(self, differences: list[tuple[UUID, Decimal | None, Decimal | None]]):
        super().__init__('Las existencias cambiaron desde la conciliación. Vuelva a conciliar.')
        # (producto, cantidad enviada o None, cantidad actual o None)
        self.differences = differences
