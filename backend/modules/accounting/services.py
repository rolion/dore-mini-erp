"""Fachada pública de Contabilidad (convención de `docs/architecture/ddd.md`): DTO inmutables, nunca modelos."""
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from django.db import connection, transaction
from django.utils import timezone

from modules.accounting.application.coverage import GetCoverageStatus
from modules.accounting.application.use_cases import missing_methods
from modules.accounting.domain.catalog import METHOD_LABELS
from modules.accounting.domain.account import AccountValidationError
from modules.accounting.domain.entry import (
    Entry,
    EntryConflict,
    EntryContractError,
    EntryValidationError,
)
from modules.accounting.infrastructure.django.repositories import (
    DjangoAccountRepository,
    DjangoClassificationRepository,
    DjangoCoverageRepository,
    DjangoEntryRepository,
    DjangoMethodMappingRepository,
)
from shared import module_gate

__all__ = ['AccountRef', 'AccountValidationError', 'ClassificationInfo', 'ClassificationRef', 'CoverageRef', 'EntryConflict',
           'EntryContractError', 'EntryInput', 'EntryRef', 'EntryValidationError', 'RecordedEntry', 'missing_method_labels', 'record_entry',
           'coverage_status', 'describe_classifications', 'resolve_account', 'validate_classification', 'validate_money_account']


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


@dataclass(frozen=True)
class ClassificationRef:
    classification_id: UUID
    name: str
    direction: str  # 'INCOME' o 'EXPENSE'


def validate_money_account(company_id: UUID, account_id: UUID) -> AccountRef:
    """Valida una cuenta de dinero elegida para un uso NUEVO, sea un cobro o un pago (no distingue dirección).

    Lanza `AccountValidationError` si no existe en la empresa o está inactiva. Los registros anteriores de una cuenta
    desactivada no se tocan.
    """
    account = DjangoAccountRepository(company_id).get(account_id)
    if account is None:
        raise AccountValidationError({'account_id': ['La cuenta no existe en esta empresa.']})
    if not account.is_active:
        raise AccountValidationError({'account_id': ['La cuenta está inactiva.']})
    return AccountRef(account.id, account.name, account.currency)


def validate_classification(company_id: UUID, classification_id: UUID, direction: str) -> ClassificationRef:
    """Valida una clasificación para un uso nuevo: de la empresa, activa y de la dirección (`INCOME`/`EXPENSE`)."""
    classification = DjangoClassificationRepository(company_id).get(classification_id)
    if classification is None:
        raise AccountValidationError({'classification_id': ['La clasificación no existe en esta empresa.']})
    classification.ensure_usable(direction)
    return ClassificationRef(classification.id, classification.name, classification.direction)


@dataclass(frozen=True)
class ClassificationInfo:
    """Clasificación tal como está hoy (nombre, dirección y estado), para mostrar o revalidar una asociación."""
    classification_id: UUID
    name: str
    direction: str
    is_active: bool


def describe_classifications(company_id: UUID, classification_ids) -> dict[UUID, ClassificationInfo]:
    """Clasificaciones de la empresa entre los ids pedidos; los ajenos o inexistentes no aparecen."""
    wanted = set(classification_ids)
    if not wanted:
        return {}
    return {c.id: ClassificationInfo(c.id, c.name, c.direction, c.is_active)
            for c in DjangoClassificationRepository(company_id).list() if c.id in wanted}


@dataclass(frozen=True)
class CoverageRef:
    """¿Una operación con esa fecha efectiva debe crear movimiento? `reason`: accounting_disabled, before_cutoff, in_gap."""
    enabled: bool
    cutoff_date: date | None
    covered: bool
    reason: str | None = None


def coverage_status(company_id: UUID, effective_date: date) -> CoverageRef:
    """Decisión única de cobertura: solo si `covered` se crea movimiento (con cuenta y clasificación válidas).

    Sin cobertura (módulo deshabilitado, fecha anterior al corte o dentro de un periodo sin cobertura) la operación de
    origen se guarda sin movimiento y sin error. Completa de forma perezosa el corte de empresas anteriores.
    """
    with transaction.atomic():
        status = GetCoverageStatus(DjangoCoverageRepository(company_id), DjangoEntryRepository(company_id),
                                   timezone.localdate(), module_gate.is_enabled(company_id, 'accounting')
                                   ).execute(effective_date)
    return CoverageRef(status.enabled, status.cutoff_date, status.covered, status.reason)


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
    regularized_at: datetime | None = None  # solo regularización de pagos históricos
    regularized_by_name: str = ''


@dataclass(frozen=True)
class EntryRef:
    """La entrada registrada, como DTO inmutable (nunca el agregado ni el modelo)."""
    id: UUID
    account_id: UUID
    currency: str
    amount: Decimal
    payment_date: date


@dataclass(frozen=True)
class RecordedEntry:
    entry: EntryRef
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
        recorded_by=data.recorded_by, recorded_by_name=data.recorded_by_name,
        regularized_at=data.regularized_at, regularized_by_name=data.regularized_by_name)
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
    return RecordedEntry(EntryRef(stored.id, stored.account_id, stored.currency, stored.amount, stored.payment_date), created)
