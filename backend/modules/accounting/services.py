"""Fachada pública de Contabilidad (convención de `docs/architecture/ddd.md`): DTO inmutables, nunca modelos."""
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from django.db import connection, transaction
from django.utils import timezone

from modules.accounting.application.coverage import GetCoverageStatus
from modules.accounting.application.journal import PostJournalEntry, ReverseJournalEntry
from modules.accounting.application.use_cases import missing_methods
from modules.accounting.domain.catalog import METHOD_LABELS, OPERATION_RECORD, OPERATION_REVERSAL
from modules.accounting.domain.account import AccountValidationError
from modules.accounting.domain.account_class import ensure_enabled, validate_account_class as _parse_account_class
from modules.accounting.domain.entry import (
    Entry,
    EntryConflict,
    EntryContractError,
    EntryNotFound,
    EntryValidationError,
)
from modules.accounting.domain.journal import (
    JournalConflict,
    JournalEntry,
    JournalEntryNotFound,
    JournalLineInput,
    JournalValidationError,
)
from modules.accounting.domain.fiscal_period import (
    DateOutsideFiscalPeriod,
    FiscalPeriodClosed,
    FiscalPeriodContractError,
)
from modules.accounting.infrastructure.django.repositories import (
    DjangoAccountClassRepository,
    DjangoAccountRepository,
    DjangoClassificationRepository,
    DjangoCoverageRepository,
    DjangoEntryRepository,
    DjangoFiscalPeriodRepository,
    DjangoJournalRepository,
    DjangoMethodMappingRepository,
)
from shared import module_gate

__all__ = ['AccountRef', 'AccountValidationError', 'ClassificationInfo', 'ClassificationRef', 'CoverageRef',
           'DateOutsideFiscalPeriod', 'EntryConflict', 'EntryContractError', 'EntryInput', 'EntryRef',
           'EntryValidationError', 'FiscalPeriodClosed', 'FiscalPeriodContractError', 'JournalBalance',
           'JournalConflict', 'JournalEntryInput', 'JournalEntryNotFound', 'JournalEntryRef', 'JournalLineInput',
           'JournalLineRef', 'JournalValidationError', 'PeriodRef', 'PostedJournalEntry', 'RecordedEntry',
           'missing_method_labels', 'record_entry', 'coverage_status', 'describe_classifications', 'get_journal_entry',
           'journal_balances', 'lock_open_period', 'period_for', 'post_journal_entry', 'resolve_account',
           'reverse_journal_entry', 'validate_account_class', 'validate_classification', 'validate_money_account']


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


def validate_account_class(company_id: UUID, code: str) -> str:
    """Valida una clasificación contable (ASSET…COST) para un uso NUEVO: del catálogo y habilitada en la empresa.

    Devuelve el código normalizado o lanza `AccountValidationError`. Lo ya clasificado no se revalida.
    """
    parsed = _parse_account_class(code)
    ensure_enabled(parsed, DjangoAccountClassRepository(company_id).disabled())
    return parsed


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
    origin_kind: str  # 'PRODUCT' (pago de pedido), 'SERVICE' (pago de proforma), 'EXPENSE' o 'PURCHASE_PAYMENT'
    origin_id: UUID  # ID del pago o del gasto en su módulo de origen
    origin_document_ref: str = ''  # ID del pedido o número de proforma
    receipt_number: str = ''  # CB-NNNNNN cuando existe
    recorded_by: int | None = None
    recorded_by_name: str = ''
    regularized_at: datetime | None = None  # solo regularización de pagos históricos
    regularized_by_name: str = ''
    classification_id: UUID | None = None  # obligatoria en egresos (EXPENSE, PURCHASE_PAYMENT): de egreso y activa


@dataclass(frozen=True)
class EntryRef:
    """La entrada registrada, como DTO inmutable (nunca el agregado ni el modelo)."""
    id: UUID
    account_id: UUID
    currency: str
    amount: Decimal
    payment_date: date
    direction: str = 'INCOME'
    operation: str = 'RECORD'


@dataclass(frozen=True)
class RecordedEntry:
    entry: EntryRef
    created: bool  # False: ya existía (reintento idempotente)


def _ref(entry: Entry) -> EntryRef:
    return EntryRef(entry.id, entry.account_id, entry.currency, entry.amount, entry.payment_date,
                    entry.direction, entry.operation)


def record_entry(company_id: UUID, data: EntryInput) -> RecordedEntry:
    """Registra el movimiento de un origen (cobro o egreso) dentro de la transacción del llamante.

    Contrato anterior (una cuenta por movimiento). Los asientos de partida doble usan `post_journal_entry`: cuando un
    origen migre al motor, su llamante deja de usar `record_entry` para ese origen en la misma entrega (el motor rechaza
    un origen ya presente en este libro, así no se contabiliza dos veces).

    Idempotente por `(empresa, origen)`: repetir con los mismos datos devuelve el existente (`created=False`); con
    datos distintos lanza `EntryConflict`. Lanza `EntryContractError` si no hay transacción abierta y
    `EntryValidationError` si el monto, la cuenta, la moneda o (en egresos) la clasificación no son válidos.
    La dirección la deriva el origen: `PRODUCT`/`SERVICE` son ingresos; `EXPENSE`/`PURCHASE_PAYMENT`, egresos.
    """
    if not connection.in_atomic_block:
        raise EntryContractError('record_entry debe ejecutarse dentro de la transacción del pago.')
    entry = Entry.record(
        account_id=data.account_id, currency=data.currency, amount=data.amount, payment_date=data.payment_date,
        method=data.method, origin_kind=data.origin_kind, origin_id=data.origin_id,
        origin_document_ref=data.origin_document_ref, receipt_number=data.receipt_number,
        recorded_by=data.recorded_by, recorded_by_name=data.recorded_by_name,
        regularized_at=data.regularized_at, regularized_by_name=data.regularized_by_name,
        classification_id=data.classification_id)
    entries = DjangoEntryRepository(company_id)
    account = DjangoAccountRepository(company_id).get_for_update(entry.account_id)
    if account is None:
        raise EntryValidationError({'account_id': ['La cuenta no existe en esta empresa.']})
    if account.currency != entry.currency:
        raise EntryValidationError({'currency': [f'La moneda debe ser la de la cuenta ({account.currency}).']})
    already = entries.get_by_origin(entry.origin_kind, entry.origin_id, entry.operation)
    if already is None and entry.direction == 'EXPENSE':
        # Un reintento no se revalida: la clasificación pudo desactivarse después de registrar el egreso.
        try:
            validate_classification(company_id, entry.classification_id, 'EXPENSE')
        except AccountValidationError as exc:
            raise EntryValidationError(exc.errors) from exc
    stored, created = entries.insert(entry)
    if not created:
        differences = entry.differences(stored)
        if differences:
            raise EntryConflict(differences)
    return RecordedEntry(_ref(stored), created)


def reverse_entry(company_id: UUID, origin_kind: str, origin_id: UUID, reversal_date: date,
                  recorded_by: int | None = None, recorded_by_name: str = '') -> RecordedEntry:
    """Revierte el movimiento de un origen con otro de dirección opuesta, mismo monto, moneda y cuenta.

    El original no se modifica ni se borra. Idempotente: si ya fue revertido devuelve la reversión existente
    (`created=False`) sin tocar de nuevo el saldo. Corre dentro de la transacción del llamante y bloquea la cuenta (como
    `record_entry`), de modo que dos reversiones simultáneas crean una sola. Permite cuentas inactivas: restituye.
    Lanza `EntryNotFound` si el origen no tiene movimiento y `EntryContractError` fuera de una transacción.
    """
    if not connection.in_atomic_block:
        raise EntryContractError('reverse_entry debe ejecutarse dentro de la transacción de la anulación.')
    entries = DjangoEntryRepository(company_id)
    original = entries.get_by_origin(origin_kind, origin_id, OPERATION_RECORD)
    if original is None:
        raise EntryNotFound(f'{origin_kind}:{origin_id}')
    DjangoAccountRepository(company_id).get_for_update(original.account_id)
    existing = entries.get_by_origin(origin_kind, origin_id, OPERATION_REVERSAL)
    if existing is not None:
        return RecordedEntry(_ref(existing), False)
    stored, created = entries.insert(original.reverse(reversal_date, recorded_by, recorded_by_name))
    return RecordedEntry(_ref(stored), created)


def account_balances(company_id: UUID, account_ids=None) -> dict[UUID, Decimal]:
    """Saldo actual por cuenta de la empresa: apertura + ingresos − egresos (las reversiones cuentan con su dirección).

    Sin `account_ids` devuelve todas las cuentas; los ids de otra empresa no aparecen en el resultado.
    """
    wanted = None if account_ids is None else set(account_ids)
    accounts = [a for a in DjangoAccountRepository(company_id).list() if wanted is None or a.id in wanted]
    net = DjangoEntryRepository(company_id).net_by_account([a.id for a in accounts])
    return {a.id: a.opening_balance + net.get(a.id, Decimal('0.00')) for a in accounts}


@dataclass(frozen=True)
class PeriodRef:
    id: UUID
    name: str
    start_date: date
    end_date: date
    is_open: bool


def _period_ref(period) -> PeriodRef:
    return PeriodRef(period.id, period.name, period.start_date, period.end_date, period.is_open)


def period_for(company_id: UUID, accounting_date: date) -> PeriodRef | None:
    """El período fiscal de la empresa que contiene la fecha (abierto o cerrado), sin bloquear; `None` si no hay."""
    period = DjangoFiscalPeriodRepository(company_id).find_containing(accounting_date)
    return _period_ref(period) if period else None


def lock_open_period(company_id: UUID, accounting_date: date) -> PeriodRef:
    """Exige que la fecha contable esté en un período abierto y lo bloquea hasta el fin de la transacción del llamante.

    Todo asiento (manual, automático o reversión, esta con su fecha explícita) debe llamarla antes de insertarse, dentro
    de su transacción: cerrar el período espera a que esa transacción termine, y si el cierre gana, el asiento ve el
    período cerrado. Lanza `FiscalPeriodContractError` fuera de una transacción, `DateOutsideFiscalPeriod` sin período
    y `FiscalPeriodClosed` si el período está cerrado.
    """
    if not connection.in_atomic_block:
        raise FiscalPeriodContractError('lock_open_period debe ejecutarse dentro de la transacción del asiento.')
    if not isinstance(accounting_date, date) or isinstance(accounting_date, datetime):
        raise FiscalPeriodContractError('La fecha contable debe ser una fecha (date).')
    period = DjangoFiscalPeriodRepository(company_id).find_containing_for_update(accounting_date)
    if period is None:
        raise DateOutsideFiscalPeriod(accounting_date)
    if not period.is_open:
        raise FiscalPeriodClosed(period.name, accounting_date)
    return _period_ref(period)


@dataclass(frozen=True)
class JournalEntryInput:
    """Asiento que quien contabiliza entrega al motor. Con `origin_kind` y `origin_id` es automático e idempotente."""
    accounting_date: date
    description: str
    lines: list  # de `JournalLineInput` (cuenta + Debe o Haber)
    origin_kind: str | None = None  # tipo de evento del módulo de origen (p. ej. 'SALE_PAYMENT')
    origin_id: UUID | None = None  # id del evento en su módulo: referencia única de evento
    created_by: int | None = None
    created_by_name: str = ''


@dataclass(frozen=True)
class JournalLineRef:
    account_id: UUID
    debit: Decimal
    credit: Decimal
    memo: str = ''


@dataclass(frozen=True)
class JournalEntryRef:
    """El asiento como DTO inmutable (nunca el agregado ni el modelo)."""
    id: UUID
    accounting_date: date
    description: str
    source: str
    currency: str
    total: Decimal
    period_id: UUID | None
    lines: tuple[JournalLineRef, ...]
    origin_kind: str | None = None
    origin_id: UUID | None = None
    reverses_id: UUID | None = None
    reversed_by_id: UUID | None = None
    reversal_reason: str = ''


@dataclass(frozen=True)
class PostedJournalEntry:
    entry: JournalEntryRef
    created: bool  # False: ya existía (reintento idempotente o reversión ya hecha)


@dataclass(frozen=True)
class JournalBalance:
    debit: Decimal
    credit: Decimal


def _journal_ref(entry: JournalEntry) -> JournalEntryRef:
    return JournalEntryRef(
        entry.id, entry.accounting_date, entry.description, entry.source, entry.currency, entry.total_debit,
        entry.period_id, tuple(JournalLineRef(line.account_id, line.debit, line.credit, line.memo)
                               for line in entry.lines),
        entry.origin_kind, entry.origin_id, entry.reverses_id, entry.reversed_by_id, entry.reversal_reason)


def _require_transaction(name: str) -> None:
    if not connection.in_atomic_block:
        raise EntryContractError(f'{name} debe ejecutarse dentro de la transacción del asiento.')


def post_journal_entry(company_id: UUID, data: JournalEntryInput) -> PostedJournalEntry:
    """Confirma un asiento de partida doble dentro de la transacción del llamante (atómico: todo o nada).

    Valida forma, Debe = Haber, cuentas de la empresa (activas, clasificadas, misma moneda) y fecha en período abierto
    (`lock_open_period`). Con `origin_kind`/`origin_id` es idempotente por `(empresa, origen)`: repetir con los mismos
    datos devuelve el existente (`created=False`) sin revalidar; con datos distintos lanza `JournalConflict`. Lanza
    `EntryContractError` fuera de una transacción y `JournalValidationError` si algo no cumple.
    """
    _require_transaction('post_journal_entry')
    stored, created = PostJournalEntry(
        DjangoJournalRepository(company_id), DjangoAccountRepository(company_id),
        DjangoAccountClassRepository(company_id).disabled(),
        lambda accounting_date: lock_open_period(company_id, accounting_date),
    ).execute(accounting_date=data.accounting_date, description=data.description, lines=data.lines,
              origin_kind=data.origin_kind, origin_id=data.origin_id, created_by=data.created_by,
              created_by_name=data.created_by_name)
    return PostedJournalEntry(_journal_ref(stored), created)


def reverse_journal_entry(company_id: UUID, entry_id: UUID, reversal_date: date, reason: str,
                          created_by: int | None = None, created_by_name: str = '') -> PostedJournalEntry:
    """Revierte por completo un asiento: otro asiento con Debe/Haber invertidos, vinculado al original (que no cambia).

    Corre en la transacción del llamante y bloquea el original, de modo que dos solicitudes simultáneas crean una sola
    reversión; repetir devuelve la existente (`created=False`). Usa las cuentas originales aunque estén deshabilitadas;
    la fecha explícita debe caer en un período abierto (el del original puede estar cerrado). Lanza
    `JournalEntryNotFound` si el asiento no es de la empresa y `JournalValidationError` si es una reversión o falta el
    motivo.
    """
    _require_transaction('reverse_journal_entry')
    stored, created = ReverseJournalEntry(
        DjangoJournalRepository(company_id), lambda accounting_date: lock_open_period(company_id, accounting_date),
    ).execute(entry_id, reversal_date, reason, created_by, created_by_name)
    return PostedJournalEntry(_journal_ref(stored), created)


def get_journal_entry(company_id: UUID, entry_id: UUID) -> JournalEntryRef:
    """El asiento de la empresa con sus líneas; `JournalEntryNotFound` si no existe o es de otra empresa."""
    entry = DjangoJournalRepository(company_id).get(entry_id)
    if entry is None:
        raise JournalEntryNotFound(str(entry_id))
    return _journal_ref(entry)


def journal_balances(company_id: UUID, account_ids=None) -> dict[UUID, JournalBalance]:
    """Debe y Haber acumulados por cuenta en el libro de asientos (solo cuentas con movimientos de la empresa).

    No incluye el libro de entradas anterior ni aplica el signo según la clasificación (lo resuelven los saldos).
    """
    wanted = None if account_ids is None else set(account_ids)
    return {account_id: JournalBalance(debit, credit) for account_id, (debit, credit)
            in DjangoJournalRepository(company_id).totals_by_account(wanted).items()}
