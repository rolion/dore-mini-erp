"""Casos de uso del motor de asientos (CONT-02). Sin Django: repositorios y bloqueo de período entran por puertos."""
from datetime import date
from typing import Callable, Protocol
from uuid import UUID

from modules.accounting.domain.journal import (
    ORIGIN_CONFLICT,
    ORIGIN_IN_LEGACY_LEDGER,
    JournalConflict,
    JournalEntry,
    JournalEntryNotFound,
    JournalValidationError,
    build_lines,
)


class JournalStore(Protocol):
    """Puerto: persistencia de asientos de una empresa."""

    def get_by_origin(self, origin_kind: str, origin_id: UUID) -> JournalEntry | None: ...

    def legacy_origin_exists(self, origin_kind: str, origin_id: UUID) -> bool: ...

    def insert(self, entry: JournalEntry) -> tuple[JournalEntry, bool]: ...

    def get_for_update(self, entry_id: UUID) -> JournalEntry | None: ...

    def reversal_of(self, entry_id: UUID) -> JournalEntry | None: ...


class AccountStore(Protocol):
    """Puerto: cuentas de una empresa."""

    def get_for_update(self, account_id: UUID): ...


# Bloquea y devuelve el período abierto de una fecha (con `.id`); lanza si está cerrado o no existe.
PeriodLocker = Callable[[date], object]


def usable_currency(accounts: AccountStore, disabled_classes, account_ids) -> str:
    """Valida cuentas para un asiento NUEVO (de la empresa, activas, clasificadas y habilitadas, en una moneda)."""
    errors: list[str] = []
    currencies: set[str] = set()
    for account_id in sorted(account_ids, key=str):  # orden fijo: sin interbloqueos entre asientos
        account = accounts.get_for_update(account_id)
        if account is None:
            errors.append('Una cuenta no existe en esta empresa.')
        elif not account.is_active:
            errors.append(f'La cuenta «{account.name}» está inactiva.')
        elif account.account_class is None or account.code is None:
            errors.append(f'La cuenta «{account.name}» no tiene código y clasificación contable; complétela en Cuentas.')
        elif account.account_class in disabled_classes:
            errors.append(f'La clasificación contable de la cuenta «{account.name}» está deshabilitada.')
        else:
            currencies.add(account.currency)
    if errors:
        raise JournalValidationError({'lines': errors})
    if len(currencies) > 1:
        raise JournalValidationError({'lines': ['Todas las cuentas del asiento deben tener la misma moneda.']})
    return currencies.pop()


def _replay(candidate: JournalEntry, stored: JournalEntry) -> tuple[JournalEntry, bool]:
    differences = candidate.differences(stored)
    if differences:
        raise JournalConflict(ORIGIN_CONFLICT,
                              f'El evento ya tiene un asiento con otros datos: {", ".join(differences)}.', differences)
    return stored, False


class PostJournalEntry:
    def __init__(self, journal: JournalStore, accounts: AccountStore, disabled_classes, lock_period: PeriodLocker):
        self.journal = journal
        self.accounts = accounts
        self.disabled_classes = disabled_classes
        self.lock_period = lock_period

    def execute(self, *, accounting_date, description, lines, origin_kind=None, origin_id=None,
                created_by: int | None = None, created_by_name: str = '') -> tuple[JournalEntry, bool]:
        """Devuelve `(asiento, creado)`; `creado=False` si el evento ya tenía el mismo asiento (reintento)."""
        built = build_lines(lines)
        common = {'accounting_date': accounting_date, 'description': description, 'lines': built,
                  'origin_kind': origin_kind, 'origin_id': origin_id, 'created_by': created_by,
                  'created_by_name': created_by_name}
        if origin_id is not None and isinstance(origin_kind, str):
            existing = self.journal.get_by_origin(origin_kind.strip(), origin_id)
            if existing is not None:  # reintento: no se revalida contra cuentas ni períodos de hoy
                return _replay(JournalEntry.post(currency=existing.currency, **common), existing)
        currency = usable_currency(self.accounts, self.disabled_classes, {line.account_id for line in built})
        entry = JournalEntry.post(currency=currency, **common)
        if entry.origin_id is not None and self.journal.legacy_origin_exists(entry.origin_kind, entry.origin_id):
            raise JournalConflict(ORIGIN_IN_LEGACY_LEDGER,
                                  'El origen ya está contabilizado en el libro de entradas anterior.')
        period = self.lock_period(entry.accounting_date)
        stored, created = self.journal.insert(entry.with_period(period.id))
        return (stored, True) if created else _replay(entry, stored)


class ReverseJournalEntry:
    def __init__(self, journal: JournalStore, lock_period: PeriodLocker):
        self.journal = journal
        self.lock_period = lock_period

    def execute(self, entry_id: UUID, reversal_date, reason, created_by: int | None = None,
                created_by_name: str = '') -> tuple[JournalEntry, bool]:
        original = self.journal.get_for_update(entry_id)
        if original is None:
            raise JournalEntryNotFound(str(entry_id))
        if original.is_reversal:
            raise JournalValidationError({'entry': ['Una reversión no se puede revertir.']})
        existing = self.journal.reversal_of(original.id)
        if existing is not None:
            return existing, False
        reversal = original.reverse(reversal_date, reason, created_by, created_by_name)
        period = self.lock_period(reversal.accounting_date)
        return self.journal.insert(reversal.with_period(period.id))
