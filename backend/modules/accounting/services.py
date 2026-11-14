"""Fachada pública de Contabilidad (convención de `docs/architecture/ddd.md`): DTO inmutables, nunca modelos."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from django.db import connection

from modules.accounting.application.use_cases import missing_methods
from modules.accounting.domain.catalog import METHOD_LABELS
from modules.accounting.domain.entry import (
    Entry,
    EntryConflict,
    EntryContractError,
    EntryValidationError,
)
from modules.accounting.infrastructure.django.repositories import (
    DjangoAccountRepository,
    DjangoEntryRepository,
    DjangoMethodMappingRepository,
)

__all__ = ['AccountRef', 'EntryConflict', 'EntryContractError', 'EntryInput', 'EntryValidationError',
           'RecordedEntry', 'missing_method_labels', 'record_entry', 'resolve_account']


@dataclass(frozen=True)
class AccountRef:
    account_id: UUID
    name: str
    currency: str


def resolve_account(company_id: UUID, method: str) -> AccountRef | None:
    """Cuenta destino vigente del método para la empresa, o `None` si el método está inactivo o sin destino válido.

    La resuelve el servidor al cobrar; quien registre la entrada debe guardar esta cuenta en ella (no la recalcula).
    """
    mapping = DjangoMethodMappingRepository(company_id).get(method)
    if mapping is None or not mapping.is_active or mapping.account_id is None:
        return None
    account = DjangoAccountRepository(company_id).get(mapping.account_id)
    if account is None or not account.can_receive:
        return None
    return AccountRef(account.id, account.name, account.currency)


def missing_method_labels(company_id: UUID) -> list[str]:
    """Etiquetas de los métodos activos sin destino válido (precondición para habilitar Contabilidad)."""
    codes = missing_methods(DjangoAccountRepository(company_id), DjangoMethodMappingRepository(company_id))
    return [METHOD_LABELS[code] for code in codes]


@dataclass(frozen=True)
class EntryInput:
    """Datos del cobro que otro módulo entrega al libro. `account_id` es la cuenta que `resolve_account` devolvió."""
    account_id: UUID
    currency: str
    amount: Decimal
    payment_date: date
    method: str
    origin_kind: str  # 'PRODUCT' (pago de pedido) o 'SERVICE' (pago de proforma)
    origin_id: UUID  # ID del pago en su módulo de origen
    origin_document_ref: str = ''  # ID del pedido o número de proforma
    receipt_number: str = ''  # CB-NNNNNN cuando existe
    recorded_by: int | None = None
    recorded_by_name: str = ''


@dataclass(frozen=True)
class RecordedEntry:
    entry_id: UUID
    account_id: UUID
    currency: str
    amount: Decimal
    payment_date: date
    created: bool  # False: ya existía (reintento idempotente)


def record_entry(company_id: UUID, data: EntryInput) -> RecordedEntry:
    """Registra la entrada de un pago dentro de la transacción del llamante (que la confirma o la revierte).

    Idempotente por `(empresa, origin_kind, origin_id)`: repetir con los mismos datos devuelve la existente
    (`created=False`); con datos distintos lanza `EntryConflict`. Lanza `EntryContractError` si no hay transacción
    abierta y `EntryValidationError` si el monto, la cuenta o la moneda no son válidos.
    """
    if not connection.in_atomic_block:
        raise EntryContractError('record_entry debe ejecutarse dentro de la transacción del pago.')
    entry = Entry.record(
        account_id=data.account_id, currency=data.currency, amount=data.amount, payment_date=data.payment_date,
        method=data.method, origin_kind=data.origin_kind, origin_id=data.origin_id,
        origin_document_ref=data.origin_document_ref, receipt_number=data.receipt_number,
        recorded_by=data.recorded_by, recorded_by_name=data.recorded_by_name)
    account = DjangoAccountRepository(company_id).get_for_update(entry.account_id)
    if account is None:
        raise EntryValidationError({'account_id': ['La cuenta no existe en esta empresa.']})
    if account.currency != entry.currency:
        raise EntryValidationError({'currency': [f'La moneda debe ser la de la cuenta ({account.currency}).']})
    stored, created = DjangoEntryRepository(company_id).insert(entry)
    if not created:
        differences = entry.differences(stored)
        if differences:
            raise EntryConflict(differences)
    return RecordedEntry(stored.id, stored.account_id, stored.currency, stored.amount, stored.payment_date, created)
