"""Diagnóstico de la transición a partida doble (CONT-07, Etapa 1): clasificación pura de cada movimiento. Sin Django.

Nunca asume una contrapartida: sin regla explícita en el mapeo el movimiento queda pendiente con motivo.
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID

from .catalog import ENTRY_ORIGIN_KINDS, FLOW_CURRENCY

CONVERTIBLE, HISTORICAL, PENDING = 'convertible_con_regla', 'historica', 'pendiente'
STATES = (CONVERTIBLE, HISTORICAL, PENDING)

NO_CUTOFF = 'sin_corte'
BEFORE_CUTOFF = 'anterior_al_corte'
NO_COUNTERPART_RULE = 'sin_regla_de_contrapartida'
ACCOUNT_WITHOUT_CODE = 'cuenta_sin_codigo'
SOURCE_MISSING = 'origen_inexistente'
SOURCE_UNVERIFIABLE = 'origen_no_verificable'
AMOUNT_DIFFERS = 'monto_distinto'
CURRENCY_DIFFERS = 'moneda_distinta'
COMPANY_INCONSISTENT = 'empresa_inconsistente'
NO_EQUITY_ACCOUNT = 'sin_cuenta_patrimonio'


class TransitionMappingError(Exception):
    """El mapeo de transición no es válido; `errors` es una lista de mensajes."""

    def __init__(self, errors: list[str]):
        super().__init__('; '.join(errors))
        self.errors = errors


@dataclass(frozen=True)
class TransitionMapping:
    """Reglas explícitas del dueño: código destino de cada cuenta de dinero y de cada contrapartida."""
    money_codes: dict[UUID, str] = field(default_factory=dict)
    counterparts: dict[str, str] = field(default_factory=dict)  # origin_kind -> código de la cuenta de contrapartida
    opening_equity: str | None = None


def _code(value: object, label: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f'{label}: el código debe ser un texto no vacío.')
        return None
    return value.strip()


def parse_transition_mapping(raw: object, account_ids: set[UUID]) -> TransitionMapping:
    """Valida `{money_accounts, counterparts, opening_equity}` contra las cuentas de la empresa."""
    if not isinstance(raw, dict):
        raise TransitionMappingError(['El mapeo debe ser un objeto JSON.'])
    errors: list[str] = []
    unknown = set(raw) - {'money_accounts', 'counterparts', 'opening_equity'}
    if unknown:
        errors.append(f'Claves desconocidas: {", ".join(sorted(unknown))}.')
    money: dict[UUID, str] = {}
    money_raw = raw.get('money_accounts', {})
    if not isinstance(money_raw, dict):
        errors.append('money_accounts debe ser un objeto {cuenta: código}.')
        money_raw = {}
    for key, value in money_raw.items():
        try:
            account_id = UUID(str(key))
        except ValueError:
            errors.append(f'money_accounts: «{key}» no es un UUID.')
            continue
        if account_id not in account_ids:
            errors.append(f'money_accounts: la cuenta {account_id} no existe en la empresa.')
            continue
        code = _code(value, f'money_accounts[{account_id}]', errors)
        if code:
            money[account_id] = code
    if len(set(money.values())) != len(money):
        errors.append('money_accounts: dos cuentas de dinero comparten el mismo código.')
    counterparts: dict[str, str] = {}
    counter_raw = raw.get('counterparts', {})
    if not isinstance(counter_raw, dict):
        errors.append('counterparts debe ser un objeto {origen: código}.')
        counter_raw = {}
    for origin, value in counter_raw.items():
        if origin not in ENTRY_ORIGIN_KINDS:
            errors.append(f'counterparts: origen desconocido «{origin}» (use {", ".join(ENTRY_ORIGIN_KINDS)}).')
            continue
        code = _code(value, f'counterparts[{origin}]', errors)
        if code:
            counterparts[origin] = code
    equity = raw.get('opening_equity')
    if equity is not None:
        equity = _code(equity, 'opening_equity', errors)
    shared = set(money.values()) & ({equity} | set(counterparts.values()) if equity else set(counterparts.values()))
    if shared:
        errors.append(f'Un código no puede ser a la vez de una cuenta de dinero y de una contrapartida: {", ".join(sorted(shared))}.')
    if errors:
        raise TransitionMappingError(errors)
    return TransitionMapping(money, counterparts, equity)


@dataclass(frozen=True)
class EntryFact:
    id: UUID
    origin_kind: str
    origin_id: UUID
    operation: str
    direction: str
    amount: Decimal
    currency: str
    payment_date: date
    account_id: UUID
    classification_id: UUID | None = None
    regularized: bool = False


@dataclass(frozen=True)
class SourceFact:
    """Pago de origen tal como lo guarda su módulo (solo ventas y cobros son verificables desde accounting)."""
    amount: Decimal


@dataclass(frozen=True)
class Verdict:
    state: str
    reason: str = ''


def classify_entry(entry: EntryFact, source: SourceFact | None, source_verifiable: bool, cutoff: date | None,
                   known_accounts: set[UUID], mapping: TransitionMapping) -> Verdict:
    if cutoff is None:
        return Verdict(PENDING, NO_CUTOFF)
    if entry.payment_date < cutoff:
        return Verdict(HISTORICAL, BEFORE_CUTOFF)
    if entry.account_id not in known_accounts:
        return Verdict(PENDING, COMPANY_INCONSISTENT)
    if not source_verifiable:
        return Verdict(PENDING, SOURCE_UNVERIFIABLE)
    if source is None:
        return Verdict(PENDING, SOURCE_MISSING)
    if source.amount != entry.amount:
        return Verdict(PENDING, AMOUNT_DIFFERS)
    if entry.currency != FLOW_CURRENCY:
        return Verdict(PENDING, CURRENCY_DIFFERS)
    if entry.account_id not in mapping.money_codes:
        return Verdict(PENDING, ACCOUNT_WITHOUT_CODE)
    if entry.origin_kind not in mapping.counterparts:
        return Verdict(PENDING, NO_COUNTERPART_RULE)
    return Verdict(CONVERTIBLE)


def classify_opening(opening_balance: Decimal, account_id: UUID, cutoff: date | None,
                     mapping: TransitionMapping) -> Verdict | None:
    """Estado del asiento de apertura de una cuenta; `None` si no tiene saldo de apertura."""
    if opening_balance <= 0:
        return None
    if cutoff is None:
        return Verdict(PENDING, NO_CUTOFF)
    if account_id not in mapping.money_codes:
        return Verdict(PENDING, ACCOUNT_WITHOUT_CODE)
    if not mapping.opening_equity:
        return Verdict(PENDING, NO_EQUITY_ACCOUNT)
    return Verdict(CONVERTIBLE)
