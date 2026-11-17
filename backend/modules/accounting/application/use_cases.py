from dataclasses import dataclass
from uuid import UUID

from modules.accounting.domain.account import (
    Account,
    AccountValidationError,
    AccountConflict,
    AccountNotFound,
    MethodNotFound,
)
from modules.accounting.domain.account_class import (
    ACCOUNT_CLASSES,
    ensure_enabled,
    parse_account_class,
    validate_account_class,
)
from modules.accounting.domain.catalog import FLOW_CURRENCY, METHOD_LABELS
from modules.accounting.domain.classification import Classification, ClassificationNotFound
from modules.accounting.domain.entry import EntryNotFound
from modules.accounting.domain.posting import ROLES, validate_account_for_role


def _active_methods_using(mappings, account_id: UUID) -> list[str]:
    return [m.code for m in mappings.all() if m.is_active and m.account_id == account_id]


def _labels(codes: list[str]) -> str:
    return ', '.join(METHOD_LABELS[code] for code in codes)


def _require(accounts, account_id: UUID) -> Account:
    account = accounts.get(account_id)
    if account is None:
        raise AccountNotFound(str(account_id))
    return account


class ListAccounts:
    def __init__(self, accounts):
        self.accounts = accounts

    def execute(self, is_active: bool | None = None, account_class: str | None = None) -> list[Account]:
        return self.accounts.list(is_active, account_class)


class GetAccount:
    def __init__(self, accounts):
        self.accounts = accounts

    def execute(self, account_id: UUID) -> Account:
        return _require(self.accounts, account_id)


# `kind` ausente = sin cambio; `kind=None` explícito = quitar el tipo de cuenta de dinero.
UNSET = object()


def _classify(account: Account, account_class: object, account_classes) -> None:
    """Clasifica la cuenta: un valor nuevo debe estar habilitado; repetir el actual no se revalida."""
    code = validate_account_class(account_class)
    if code == account.account_class:
        return
    ensure_enabled(code, account_classes.disabled())
    account.classify(code)


class CreateAccount:
    """Alta de una cuenta del plan: código, nombre y clasificación habilitada son obligatorios."""

    def __init__(self, accounts, account_classes=None):
        self.accounts = accounts
        self.account_classes = account_classes

    def execute(self, name: object, currency: object, kind: object = None,
                opening_balance: object = None, account_class: object = None, code: object = None,
                is_contra: bool = False) -> Account:
        missing = {}
        if code is None or (isinstance(code, str) and not code.strip()):
            missing['code'] = ['El código es obligatorio.']
        if account_class is None:
            missing['account_class'] = ['La clasificación contable es obligatoria.']
        if missing:
            raise AccountValidationError(missing)
        account = Account.create(name, currency, kind, opening_balance, code, is_contra)
        _classify(account, account_class, self.account_classes)
        account.ensure_consistent()
        return self.accounts.save(account)


class UpdateAccount:
    def __init__(self, accounts, mappings, entries=None, account_classes=None):
        self.accounts = accounts
        self.mappings = mappings
        self.entries = entries
        self.account_classes = account_classes

    def _has_entries(self, account: Account) -> bool:
        return bool(self.entries and self.entries.has_entries_for_account(account.id))

    def execute(self, account_id: UUID, name: object = None, currency: object = None,
                kind: object = UNSET, opening_balance: object = None, account_class: object = None,
                code: object = None, is_contra: bool | None = None) -> Account:
        self.mappings.lock_company()
        account = _require(self.accounts, account_id)
        previous_currency = account.currency
        if opening_balance is not None:
            previous_balance = account.opening_balance
            account.set_opening_balance(opening_balance)
            if account.opening_balance != previous_balance and self._has_entries(account):
                raise AccountConflict(
                    'account_has_entries',
                    'No se puede cambiar el saldo de apertura: la cuenta ya tiene movimientos registrados.')
        if name is not None:
            account.rename(name)
        if code is not None:
            account.change_code(code)
        if kind is not UNSET:
            account.clear_kind() if kind is None else account.change_kind(kind)
        if account_class is not None:
            previous_class = account.account_class
            _classify(account, account_class, self.account_classes)
            if previous_class is not None and account.account_class != previous_class and self._has_entries(account):
                raise AccountConflict(
                    'account_has_entries',
                    'No se puede cambiar la clasificación: la cuenta ya tiene asientos registrados.')
        if is_contra is not None and bool(is_contra) != account.is_contra:
            if self._has_entries(account):
                raise AccountConflict(
                    'account_has_entries',
                    'No se puede cambiar la marca de cuenta correctora: la cuenta ya tiene asientos registrados.')
            account.change_is_contra(is_contra)
        account.ensure_consistent()
        if currency is not None:
            account.change_currency(currency)
            if account.currency != previous_currency and self.entries and self.entries.has_entries_for_account(account.id):
                raise AccountConflict(
                    'account_has_entries',
                    'No se puede cambiar la moneda: la cuenta ya tiene entradas registradas en el libro.')
            using = _active_methods_using(self.mappings, account.id)
            if account.currency != FLOW_CURRENCY and using:
                raise AccountConflict(
                    'account_in_use',
                    f'No se puede cambiar la moneda: la usan los métodos {_labels(using)}. '
                    'Reasígnalos o desactívalos primero.', using)
        return self.accounts.save(account)


class ActivateAccount:
    def __init__(self, accounts):
        self.accounts = accounts

    def execute(self, account_id: UUID) -> Account:
        account = _require(self.accounts, account_id)
        account.activate()
        return self.accounts.save(account)


class DeactivateAccount:
    def __init__(self, accounts, mappings):
        self.accounts = accounts
        self.mappings = mappings

    def execute(self, account_id: UUID) -> Account:
        self.mappings.lock_company()
        account = _require(self.accounts, account_id)
        using = _active_methods_using(self.mappings, account.id)
        if using:
            raise AccountConflict(
                'account_in_use',
                f'No se puede desactivar: la usan los métodos {_labels(using)}. '
                'Reasígnalos o desactívalos primero.', using)
        account.deactivate()
        return self.accounts.save(account)


def _require_classification(classifications, classification_id: UUID) -> Classification:
    classification = classifications.get(classification_id)
    if classification is None:
        raise ClassificationNotFound(str(classification_id))
    return classification


class ListClassifications:
    def __init__(self, classifications):
        self.classifications = classifications

    def execute(self, is_active: bool | None = None, direction: str | None = None) -> list[Classification]:
        return self.classifications.list(is_active, direction)


class GetClassification:
    def __init__(self, classifications):
        self.classifications = classifications

    def execute(self, classification_id: UUID) -> Classification:
        return _require_classification(self.classifications, classification_id)


class CreateClassification:
    def __init__(self, classifications):
        self.classifications = classifications

    def execute(self, name: object, direction: object) -> Classification:
        return self.classifications.save(Classification.create(name, direction))


class RenameClassification:
    def __init__(self, classifications):
        self.classifications = classifications

    def execute(self, classification_id: UUID, name: object) -> Classification:
        classification = _require_classification(self.classifications, classification_id)
        classification.rename(name)
        return self.classifications.save(classification)


class SetClassificationActive:
    """Activa o desactiva; nunca borra ni toca registros que ya usaron la clasificación."""

    def __init__(self, classifications, active: bool):
        self.classifications = classifications
        self.active = active

    def execute(self, classification_id: UUID) -> Classification:
        classification = _require_classification(self.classifications, classification_id)
        classification.activate() if self.active else classification.deactivate()
        return self.classifications.save(classification)


@dataclass(frozen=True)
class MethodView:
    code: str
    label: str
    is_active: bool
    account: Account | None


class ListMethods:
    def __init__(self, accounts, mappings):
        self.accounts = accounts
        self.mappings = mappings

    def execute(self) -> list[MethodView]:
        by_id = self.accounts.by_id()
        return [MethodView(m.code, METHOD_LABELS[m.code], m.is_active, by_id.get(m.account_id) if m.account_id else None)
                for m in self.mappings.all()]


class ConfigureMethod:
    def __init__(self, accounts, mappings):
        self.accounts = accounts
        self.mappings = mappings

    def execute(self, code: str, account_id: UUID | None, is_active: bool) -> MethodView:
        self.mappings.lock_company()
        mapping = self.mappings.get(code)
        if mapping is None:
            raise MethodNotFound(code)
        account = _require(self.accounts, account_id) if account_id else None
        if account is not None and is_active and account.id != mapping.account_id:
            # Uso nuevo y activo: el método apunta a una cuenta de Activo.
            # Lo ya configurado no se revalida (cambiar solo el estado no exige reclasificar cuentas heredadas).
            validate_account_for_role(ROLES['MONEY'], account, frozenset())
        mapping.configure(account, is_active)
        self.mappings.save(mapping)
        return MethodView(code, METHOD_LABELS[code], mapping.is_active, account)


def missing_methods(accounts, mappings) -> list[str]:
    """Códigos de los métodos activos sin un destino válido (cuenta activa en la moneda de los flujos)."""
    by_id = accounts.by_id()
    return [m.code for m in mappings.all() if not m.is_complete(by_id)]


class ListEntries:
    """Una página del libro y, sobre TODO el conjunto filtrado, totales por moneda y la cobertura del libro."""

    def __init__(self, entries):
        self.entries = entries

    def execute(self, filters):
        return self.entries.query(filters), self.entries.totals(filters), self.entries.coverage()


class GetEntry:
    def __init__(self, entries):
        self.entries = entries

    def execute(self, entry_id: UUID):
        row = self.entries.get(entry_id)
        if row is None:
            raise EntryNotFound(str(entry_id))
        return row


@dataclass(frozen=True)
class AccountClassView:
    code: str
    enabled: bool


class ListAccountClasses:
    """Siempre las seis, en orden fijo, con su estado en la empresa."""

    def __init__(self, account_classes):
        self.account_classes = account_classes

    def execute(self) -> list[AccountClassView]:
        disabled = self.account_classes.disabled()
        return [AccountClassView(code, code not in disabled) for code in ACCOUNT_CLASSES]


class SetAccountClassEnabled:
    """Habilita o deshabilita (idempotente); no toca cuentas, entradas ni saldos."""

    def __init__(self, account_classes, enabled: bool):
        self.account_classes = account_classes
        self.enabled = enabled

    def execute(self, code: object) -> AccountClassView:
        parsed = parse_account_class(code)
        self.account_classes.set_enabled(parsed, self.enabled)
        return AccountClassView(parsed, self.enabled)
