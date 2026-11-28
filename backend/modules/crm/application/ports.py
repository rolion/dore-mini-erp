"""Puertos de CRM: lo que necesita de otros contextos, expresado con DTO propios."""
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID


@dataclass(frozen=True)
class CustomerRef:
    id: UUID
    name: str
    phone: str


@dataclass(frozen=True)
class CommercialSummary:
    order_count: int
    last_purchase_date: date | None
    outstanding_amount: Decimal


class CustomerDirectory(Protocol):
    def search_active(self, search: str | None, customer_ids: Collection[UUID] | None) -> Sequence[CustomerRef]:
        """Clientes activos por nombre e id; admite `count()` y rebanadas."""


class SalesReader(Protocol):
    def summaries(self, customer_ids: Collection[UUID]) -> dict[UUID, CommercialSummary]: ...

    def customer_ids_in_warehouse(self, warehouse_id: UUID) -> list[UUID]: ...


class WarehouseDirectory(Protocol):
    def exists(self, warehouse_id: UUID) -> bool: ...


class ModuleAvailability(Protocol):
    def sales_enabled(self) -> bool: ...

    def inventory_enabled(self) -> bool: ...


class StageCards(Protocol):
    """Tarjetas = oportunidades **abiertas** de una etapa (PB-CRM-004); reasignar deja historial de etapa."""

    def count(self, stage_id: UUID) -> int: ...

    def reassign(self, from_stage_id: UUID, to_stage_id: UUID) -> int: ...


# --- Prospectos y oportunidades (PB-CRM-004) ----------------------------------------------------------------

@dataclass(frozen=True)
class CustomerContact:
    id: UUID
    name: str
    phone: str
    active: bool = True


class CustomerGatewayError(Exception):
    """Clientes rechazó los datos del cliente a crear: `errors` es `{campo: [mensajes]}`."""

    def __init__(self, errors: dict[str, list[str]]):
        super().__init__(errors)
        self.errors = errors


class CustomerGateway(Protocol):
    def normalize_phone(self, raw: str) -> str: ...

    def find_active_by_phone(self, normalized_phone: str) -> list[CustomerContact]: ...

    def get(self, customer_id: UUID) -> CustomerContact | None:
        """Cliente de la empresa (activo o no) o `None`."""

    def get_many(self, customer_ids: Collection[UUID]) -> dict[UUID, CustomerContact]: ...

    def create(self, name: str, phone: str, email: str) -> CustomerContact:
        """Crea el cliente; lanza `CustomerGatewayError` si Clientes rechaza los datos."""


@dataclass(frozen=True)
class OrderRef:
    id: UUID
    customer_id: UUID | None
    order_date: date
    total: Decimal
    status: str
    cancelled: bool


class OrderGateway(Protocol):
    def get(self, order_id: UUID) -> OrderRef | None:
        """Pedido de la empresa en cualquier estado, o `None` si no existe o es ajeno."""

    def list_for_customer(self, customer_id: UUID) -> Sequence[OrderRef]:
        """Pedidos no cancelados del cliente, los más recientes primero."""


class UserDirectory(Protocol):
    def exists(self, user_id: int) -> bool: ...

    def names(self, user_ids: Collection[int]) -> dict[int, str]: ...

    def search(self, search: str = '') -> list[dict]: ...


class Clock(Protocol):
    def __call__(self) -> datetime: ...


# --- Bandeja de WhatsApp (PB-CRM-012) -----------------------------------------------------------------------

@dataclass(frozen=True)
class InboxMessage:
    id: UUID
    direction: str
    type: str
    content: dict[str, Any]
    status: str
    failure_reason: str
    created_at: datetime | None
    sent_at: datetime | None


@dataclass(frozen=True)
class InboxConversation:
    id: UUID
    phone: str
    owner_id: int | None
    customer_id: UUID | None
    lead_id: UUID | None
    opportunity_id: UUID | None
    last_message: InboxMessage | None
    window_open: bool
    window_expires_at: datetime | None


class ConversationInbox(Protocol):
    """Conversaciones y mensajes de WhatsApp de la empresa (los guarda `messaging`). Traduce sus errores a los de CRM:
    inexistente → `CrmNotFound`; datos inválidos → `CrmValidationError`; ventana cerrada, plantilla no aprobada,
    conexión inactiva o mensaje no reintentable → `CrmConflict`."""

    def page(self, *, owner_id: int | None, unassigned: bool, opportunity_id: UUID | None, search: str | None,
             customer_ids: Collection[UUID], lead_ids: Collection[UUID], offset: int, limit: int
             ) -> tuple[int, list[InboxConversation]]: ...

    def get(self, conversation_id: UUID) -> InboxConversation: ...

    def messages(self, conversation_id: UUID, after: datetime | None) -> list[InboxMessage]: ...

    def connection_active(self) -> bool: ...

    def send_text(self, conversation_id: UUID, body: str) -> InboxMessage: ...

    def send_template(self, conversation_id: UUID, template_id: UUID, components: list | None) -> InboxMessage: ...

    def retry(self, conversation_id: UUID, message_id: UUID) -> InboxMessage: ...

    def assign(self, conversation_id: UUID, owner_id: int | None) -> None: ...

    def link(self, conversation_id: UUID, customer_id: UUID | None, lead_id: UUID | None,
             opportunity_id: UUID | None) -> None: ...
