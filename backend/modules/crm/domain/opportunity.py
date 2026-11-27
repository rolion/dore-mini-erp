"""Oportunidad: posible venta ubicada en una etapa de un tablero (puro: sin Django). INV-01…INV-03, INV-06, INV-07."""
from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4

from .errors import CrmConflict, CrmValidationError

OPEN, WON, LOST = 'open', 'won', 'lost'
STATUSES = (OPEN, WON, LOST)
CURRENCY = 'BOB'
TITLE_MAX = 150
LOST_REASON_MAX = 500
DESCRIPTION_MAX = 1000
AMOUNT_MAX = Decimal('9999999999.99')  # Decimal(12, 2)
CENT = Decimal('0.01')


def clean_title(value: object) -> str:
    title = value.strip() if isinstance(value, str) else ''
    if not title:
        raise CrmValidationError({'title': ['Ingresa un título.']})
    if len(title) > TITLE_MAX:
        raise CrmValidationError({'title': [f'Usa como máximo {TITLE_MAX} caracteres.']})
    return title


def clean_amount(value: object) -> Decimal:
    if isinstance(value, (float, bool)):  # dinero nunca en float
        raise CrmValidationError({'amount': ['Ingresa un importe válido.']})
    try:
        amount = Decimal(str(value)) if value is not None else None
    except InvalidOperation:
        amount = None
    if amount is None or not amount.is_finite():
        raise CrmValidationError({'amount': ['Ingresa un importe válido.']})
    if amount < 0:
        raise CrmValidationError({'amount': ['El importe no puede ser negativo.']})
    if amount != amount.quantize(CENT):
        raise CrmValidationError({'amount': ['Usa como máximo 2 decimales.']})
    if amount > AMOUNT_MAX:
        raise CrmValidationError({'amount': ['El importe es demasiado grande.']})
    return amount.quantize(CENT)


def clean_description(value: object) -> str:
    """INV-03: opcional, recortada, hasta DESCRIPTION_MAX caracteres."""
    text = value.strip() if isinstance(value, str) else ''
    if len(text) > DESCRIPTION_MAX:
        raise CrmValidationError({'description': [f'Usa como máximo {DESCRIPTION_MAX} caracteres.']})
    return text


def clean_lost_reason(value: object) -> str:
    reason = value.strip() if isinstance(value, str) else ''
    if not reason:
        raise CrmValidationError({'lost_reason': ['Indica el motivo de la pérdida.']})
    if len(reason) > LOST_REASON_MAX:
        raise CrmValidationError({'lost_reason': [f'Usa como máximo {LOST_REASON_MAX} caracteres.']})
    return reason


@dataclass(frozen=True)
class StageChange:
    """Registro inmutable de un cambio de etapa (INV-08); `from_stage_id` nulo al crear."""
    opportunity_id: UUID
    from_stage_id: UUID | None
    to_stage_id: UUID
    changed_by: int | None
    changed_at: datetime


@dataclass
class Opportunity:
    id: UUID
    board_id: UUID
    stage_id: UUID
    lead_id: UUID | None
    customer_id: UUID | None
    title: str
    owner_id: int
    amount: Decimal
    currency: str = CURRENCY
    next_action_at: datetime | None = None
    status: str = OPEN
    closed_at: datetime | None = None
    order_id: UUID | None = None
    lost_reason: str = ''
    created_at: datetime | None = None
    description: str = ''

    @classmethod
    def create(cls, *, board_id: UUID, stage_id: UUID, lead_id: UUID | None, customer_id: UUID | None,
               title: object, amount: object = None, owner_id: int, next_action_at: datetime | None = None,
               description: object = None) -> 'Opportunity':
        errors: dict[str, list[str]] = {}
        if lead_id is None and customer_id is None:
            errors['lead_id'] = ['Elige un prospecto o un cliente.']
        values = {}
        checks = (('title', lambda: clean_title(title)),
                  ('amount', lambda: clean_amount(amount if amount is not None else Decimal('0'))),  # INV-04
                  ('description', lambda: clean_description(description)))
        for field, check in checks:
            try:
                values[field] = check()
            except CrmValidationError as exc:
                errors.update(exc.errors)
        if errors:
            raise CrmValidationError(errors)
        return cls(id=uuid4(), board_id=board_id, stage_id=stage_id, lead_id=lead_id, customer_id=customer_id,
                   owner_id=owner_id, next_action_at=next_action_at, **values)

    @property
    def is_open(self) -> bool:
        return self.status == OPEN

    def _require_open(self) -> None:
        if not self.is_open:
            raise CrmConflict('opportunity_closed', 'La oportunidad está cerrada y no se puede modificar.',
                              status=self.status)

    def edit(self, *, title: object = None, amount: object = None, owner_id: int | None = None,
             next_action_at: datetime | None = None, change_next_action: bool = False,
             description: object = None) -> None:
        """Cambia solo lo indicado (`None` = sin cambio; `change_next_action` permite vaciar la fecha)."""
        self._require_open()
        new_title = clean_title(title) if title is not None else self.title
        new_amount = clean_amount(amount) if amount is not None else self.amount
        new_description = clean_description(description) if description is not None else self.description
        self.title, self.amount, self.description = new_title, new_amount, new_description
        if owner_id is not None:
            self.owner_id = owner_id
        if change_next_action:
            self.next_action_at = next_action_at

    def move_to(self, stage_id: UUID, active_stage_ids: Collection[UUID]) -> UUID | None:
        """Mueve a una etapa activa del mismo tablero (INV-02); devuelve la etapa anterior o `None` si no cambia."""
        self._require_open()
        if stage_id not in active_stage_ids:
            raise CrmValidationError({'stage_id': ['Elige una etapa activa de este tablero.']})
        if stage_id == self.stage_id:
            return None
        previous, self.stage_id = self.stage_id, stage_id
        return previous

    def _require_not_closed_as(self, result: str) -> None:
        if self.status not in (OPEN, result):
            raise CrmConflict('already_closed', 'La oportunidad ya está cerrada con otro resultado.',
                              status=self.status)

    def close_won(self, now: datetime) -> bool:
        """Cierra como ganada; repetir no cambia `closed_at` (INV-03). Devuelve si cambió."""
        self._require_not_closed_as(WON)
        if self.status == WON:
            return False
        self.status, self.closed_at = WON, now
        return True

    def close_lost(self, reason: object, now: datetime) -> bool:
        """Cierra como perdida con motivo obligatorio; repetir no cambia nada (INV-03). Devuelve si cambió."""
        reason = clean_lost_reason(reason)
        self._require_not_closed_as(LOST)
        if self.status == LOST:
            return False
        self.status, self.closed_at, self.lost_reason = LOST, now, reason
        return True

    def link_order(self, order_id: UUID, order_customer_id: UUID | None, order_cancelled: bool) -> bool:
        """Vincula un pedido del mismo cliente, no cancelado, solo estando ganada (INV-06). Devuelve si cambió."""
        if self.status != WON:
            raise CrmConflict('opportunity_not_won', 'Solo una oportunidad ganada puede vincular un pedido.',
                              status=self.status)
        if self.customer_id is None:
            raise CrmConflict('customer_required', 'Convierte el prospecto en cliente antes de vincular un pedido.')
        if order_customer_id != self.customer_id:
            raise CrmConflict('order_customer_mismatch', 'El pedido es de otro cliente.')
        if order_cancelled:
            raise CrmConflict('order_cancelled', 'El pedido está cancelado.')
        if self.order_id == order_id:
            return False
        self.order_id = order_id
        return True

    def attach_customer(self, customer_id: UUID) -> bool:
        """Al convertir el prospecto, la oportunidad abierta sin cliente recibe el cliente (conserva `lead_id`)."""
        if not self.is_open or self.customer_id is not None:
            return False
        self.customer_id = customer_id
        return True
