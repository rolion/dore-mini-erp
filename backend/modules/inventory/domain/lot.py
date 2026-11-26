from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

CODE_PREFIX = 'L'
NUMBER_MIN_DIGITS = 4


class LotStatus(str, Enum):
    REFRIGERATING = 'refrigerating'
    RELEASED = 'released'


def format_lot_code(lot_date: date, number: int) -> str:
    """`L-YYYYMMDD-0001`: fecha del lote y correlativo del período fiscal (crece de ancho pasado el 9999)."""
    return f'{CODE_PREFIX}-{lot_date:%Y%m%d}-{number:0{NUMBER_MIN_DIGITS}d}'


@dataclass(frozen=True)
class LotNumber:
    """Número asignado a un lote dentro de la serie de su período fiscal."""

    period_id: UUID
    period_name: str
    number: int


@dataclass
class StockLot:
    """Lote de un producto en un almacén. Nace en refrigeración y solo cambia a liberado (INV-06)."""

    id: UUID
    product_id: UUID
    warehouse_id: UUID
    lot_date: date
    number: LotNumber
    status: LotStatus = LotStatus.REFRIGERATING
    released_at: datetime | None = None
    released_by_id: UUID | None = None
    released_by_name: str = ''
    created_at: datetime | None = None

    @classmethod
    def create(cls, *, product_id: UUID, warehouse_id: UUID, lot_date: date, number: LotNumber) -> 'StockLot':
        return cls(id=uuid4(), product_id=product_id, warehouse_id=warehouse_id, lot_date=lot_date, number=number)

    @property
    def code(self) -> str:
        return format_lot_code(self.lot_date, self.number.number)

    @property
    def is_released(self) -> bool:
        return self.status is LotStatus.RELEASED

    def release(self, *, now: datetime, user_id: UUID | None, user_name: str) -> bool:
        """Libera el lote; devuelve `False` (sin cambios) si ya estaba liberado."""
        if self.is_released:
            return False
        self.status = LotStatus.RELEASED
        self.released_at = now
        self.released_by_id = user_id
        self.released_by_name = user_name
        return True

    def available(self, physical: Decimal) -> Decimal:
        """Disponible para empaque: el saldo físico solo si está liberado (el de refrigeración está bloqueado)."""
        return physical if self.is_released else Decimal('0')


@dataclass(frozen=True)
class LotPosition:
    """Un lote con su saldo físico y su disponible para empaque."""

    lot: StockLot
    warehouse_name: str
    physical: Decimal

    @property
    def available(self) -> Decimal:
        return self.lot.available(self.physical)
