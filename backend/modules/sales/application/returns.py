"""Devolución total de un pedido entregado: reingresa el stock, contrarresta ingreso, costo y cobros."""
from dataclasses import dataclass
from uuid import UUID

from modules.sales.domain.exceptions import OrderNotFound
from modules.sales.domain.order import Order
from modules.sales.domain.repositories import OrderRepository

from .commands import _load_for_update
from .ports import (
    Actor,
    Clock,
    DeliveryCosting,
    ReversalEntry,
    SalesPosting,
    StockOutput,
    StockOutputRecord,
)


class ReturnOrder:
    """DELIVERED -> RETURNED. Todo ocurre en la transacción de quien llama: si falla un paso (p. ej. período contable
    cerrado) no queda stock, costo, asiento ni cambio de estado. El bloqueo del pedido más el estado terminal y las
    reversiones idempotentes por origen impiden duplicar efectos con reintentos o solicitudes simultáneas."""

    def __init__(self, repository: OrderRepository, clock: Clock, stock: StockOutput | None = None,
                 posting: SalesPosting | None = None, costing: DeliveryCosting | None = None):
        self.repository = repository
        self.clock = clock
        self.stock = stock
        self.posting = posting
        self.costing = costing

    def execute(self, order_id: UUID, reason: object = None, actor: Actor | None = None,
                refund_acknowledged: bool = False) -> Order:
        actor = actor or Actor(None, '')
        order = _load_for_update(self.repository, order_id)
        order.register_return(reason, self.clock.now(), actor.user_name, bool(refund_acknowledged))
        if self.stock is not None:
            self.stock.reverse_outputs(order.id, order.return_reason, actor)
        if self.costing is not None:
            self.costing.reverse_cost(order.id)
        if self.posting is not None:
            today = self.clock.today()
            self.posting.reverse_delivery(order, order.return_reason, actor, today)
            if order.payments:
                self.posting.reverse_payments(order, order.return_reason, actor, today)
        return self.repository.save(order)


@dataclass(frozen=True)
class ReturnPreview:
    """Qué contrarrestaría la devolución: solo lectura e informativo (el servidor revalida al confirmar)."""

    order: Order
    inventory_enabled: bool
    stock: StockOutputRecord | None
    entries: list[ReversalEntry]
    requires_refund_acknowledgement: bool


class PreviewOrderReturn:
    def __init__(self, repository: OrderRepository, stock: StockOutput | None = None,
                 posting: SalesPosting | None = None):
        self.repository = repository
        self.stock = stock
        self.posting = posting

    def execute(self, order_id: UUID) -> ReturnPreview:
        order = self.repository.get(order_id)
        if order is None:
            raise OrderNotFound(order_id)
        order.ensure_returnable()
        inventory = self.stock is not None and self.stock.is_available()
        return ReturnPreview(
            order=order, inventory_enabled=inventory,
            stock=self.stock.output_for(order.id) if inventory else None,
            entries=[entry for entry in (self.posting.reversal_entries(order) if self.posting else [])
                     if entry.reversed_by_id is None],
            requires_refund_acknowledgement=bool(order.payments))
