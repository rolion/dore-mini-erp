"""Regularización de pagos históricos (PB-ACC-004): clasificación pura de cada pago contra el libro.

Sin Django. Nunca decide una cuenta por su cuenta: solo usa el mapeo histórico explícito que recibe.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from .account import Account
from .catalog import FLOW_CURRENCY, METHOD_CODES, ORIGIN_KINDS
from .entry import Entry, EntryValidationError

MISSING, EXISTING, PENDING, CONFLICT, DESTINATION_DIFFERENCE, INVALID = (
    'missing', 'existing', 'pending', 'conflict', 'destination_difference', 'invalid')
STATUSES = (MISSING, EXISTING, PENDING, CONFLICT, DESTINATION_DIFFERENCE, INVALID)
CREATED, ALREADY_EXISTED, FAILED = 'created', 'already_existed', 'failed'

REASON_NO_MAPPING = 'method_without_mapping'
REASON_OUT_OF_RANGE = 'date_outside_mapping'


class RegularizationInputError(Exception):
    """El mapeo histórico o los parámetros no son válidos; `errors` es una lista de mensajes."""

    def __init__(self, errors: list[str]):
        super().__init__('; '.join(errors))
        self.errors = errors


@dataclass(frozen=True)
class SourcePayment:
    """Pago histórico tal como lo guarda su módulo de origen. Los campos que el origen no guarda quedan vacíos."""
    origin_kind: str
    id: UUID
    amount: Decimal
    method: str
    payment_date: date
    document_ref: str = ''
    receipt_number: str = ''
    reference: str = ''
    recorded_by: int | None = None
    recorded_by_name: str = ''
    document_state: str = ''

    @property
    def absent_fields(self) -> tuple[str, ...]:
        """Datos históricos que el origen no tiene (se reportan, nunca se inventan)."""
        absent = []
        if self.recorded_by is None and not self.recorded_by_name:
            absent.append('author')
        if self.origin_kind == 'SERVICE' and not self.receipt_number:
            absent.append('receipt_number')
        if not self.document_ref:
            absent.append('document_ref')
        return tuple(absent)


@dataclass(frozen=True)
class MappingRule:
    account_id: UUID
    date_from: date | None = None
    date_to: date | None = None

    def covers(self, day: date) -> bool:
        return (self.date_from is None or day >= self.date_from) and (self.date_to is None or day <= self.date_to)


class HistoricalMapping:
    """Método → reglas por rango de fecha efectiva, explícitas y sin solapes."""

    def __init__(self, rules: dict[str, list[MappingRule]]):
        self.rules = rules

    def resolve(self, method: str, day: date) -> tuple[UUID | None, str]:
        rules = self.rules.get(method)
        if not rules:
            return None, REASON_NO_MAPPING
        for rule in rules:
            if rule.covers(day):
                return rule.account_id, ''
        return None, REASON_OUT_OF_RANGE


def _parse_date(value: object, label: str, errors: list[str]) -> date | None:
    if value in (None, ''):
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        errors.append(f'{label}: fecha no válida «{value}» (use AAAA-MM-DD).')
        return None


def parse_mapping(raw: object, accounts: dict[UUID, Account]) -> HistoricalMapping:
    """Valida el mapeo `{método: [{account_id, from?, to?}]}` contra las cuentas de la empresa."""
    errors: list[str] = []
    if not isinstance(raw, dict) or not raw:
        raise RegularizationInputError(['El mapeo debe ser un objeto {método: [reglas]} no vacío.'])
    rules: dict[str, list[MappingRule]] = {}
    for method, entries in raw.items():
        if method not in METHOD_CODES:
            errors.append(f'{method}: método desconocido (use {", ".join(METHOD_CODES)}).')
            continue
        if not isinstance(entries, list) or not entries:
            errors.append(f'{method}: debe ser una lista con al menos una regla.')
            continue
        parsed: list[MappingRule] = []
        for index, item in enumerate(entries, 1):
            label = f'{method}[{index}]'
            if not isinstance(item, dict):
                errors.append(f'{label}: la regla debe ser un objeto.')
                continue
            try:
                account_id = UUID(str(item.get('account_id')))
            except ValueError:
                errors.append(f'{label}: account_id no es un UUID.')
                continue
            account = accounts.get(account_id)
            if account is None:
                errors.append(f'{label}: la cuenta no existe en la empresa.')
                continue
            if not account.can_receive:
                errors.append(f'{label}: la cuenta «{account.name}» debe estar activa y en {FLOW_CURRENCY}.')
                continue
            date_from, date_to = _parse_date(item.get('from'), label, errors), _parse_date(item.get('to'), label, errors)
            if date_from and date_to and date_from > date_to:
                errors.append(f'{label}: «from» es posterior a «to».')
                continue
            parsed.append(MappingRule(account_id, date_from, date_to))
        ordered = sorted(parsed, key=lambda r: r.date_from or date.min)
        for before, after in zip(ordered, ordered[1:]):
            if (before.date_to or date.max) >= (after.date_from or date.min):
                errors.append(f'{method}: las reglas se solapan en el tiempo.')
                break
        rules[method] = ordered
    if errors:
        raise RegularizationInputError(errors)
    return HistoricalMapping(rules)


@dataclass(frozen=True)
class Item:
    """Resultado de comparar un pago con el libro."""
    payment: SourcePayment
    status: str
    account_id: UUID | None = None
    reason: str = ''
    fields: tuple[str, ...] = ()
    outcome: str = ''  # solo al aplicar: created / already_existed / failed
    error: str = ''

    @property
    def currency(self) -> str:
        return FLOW_CURRENCY


def _valid_or_message(payment: SourcePayment, account_id: UUID) -> str:
    try:
        Entry.record(account_id=account_id, currency=FLOW_CURRENCY, amount=payment.amount,
                     payment_date=payment.payment_date, method=payment.method, origin_kind=payment.origin_kind,
                     origin_id=payment.id)
    except EntryValidationError as exc:
        return next((m[0] for m in exc.errors.values() if m), 'datos no válidos.')
    return ''


def classify(payment: SourcePayment, existing: Entry | None, mapping: HistoricalMapping) -> Item:
    """Compara por identidad de origen. Una entrada existente jamás se corrige: solo se informa la diferencia."""
    account_id, reason = mapping.resolve(payment.method, payment.payment_date)
    if existing is not None:
        fields = tuple(name for name, ours, theirs in (
            ('amount', payment.amount, existing.amount), ('payment_date', payment.payment_date, existing.payment_date),
            ('method', payment.method, existing.method), ('currency', FLOW_CURRENCY, existing.currency),
        ) if ours != theirs)
        if fields:
            return Item(payment, CONFLICT, existing.account_id, fields=fields)
        if account_id is not None and account_id != existing.account_id:
            return Item(payment, DESTINATION_DIFFERENCE, existing.account_id, fields=('account_id',))
        return Item(payment, EXISTING, existing.account_id)
    if payment.origin_kind not in ORIGIN_KINDS or payment.method not in METHOD_CODES:
        return Item(payment, INVALID, reason='unknown_origin_or_method')
    if account_id is None:
        return Item(payment, PENDING, reason=reason)
    message = _valid_or_message(payment, account_id)
    if message:
        return Item(payment, INVALID, account_id, reason=message)
    return Item(payment, MISSING, account_id)


@dataclass
class Group:
    count: int = 0
    amount: Decimal = Decimal('0.00')


@dataclass
class Report:
    items: list[Item] = field(default_factory=list)

    def groups(self) -> dict[tuple[str, str, str, str], Group]:
        """Cantidad e importe por (estado, origen, cuenta, moneda); aplicado: el estado final de cada pago."""
        result: dict[tuple[str, str, str, str], Group] = {}
        for item in self.items:
            status = {CREATED: 'created', ALREADY_EXISTED: EXISTING, FAILED: 'failed'}.get(item.outcome, item.status)
            key = (status, item.payment.origin_kind, str(item.account_id or ''), item.currency)
            group = result.setdefault(key, Group())
            group.count += 1
            group.amount += item.payment.amount
        return result

    def absent_fields(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.items:
            if item.status == MISSING:
                for name in item.payment.absent_fields:
                    counts[name] = counts.get(name, 0) + 1
        return counts


def regularization_stamp(now: datetime, executed_by: str) -> tuple[datetime, str]:
    return now, executed_by.strip()
