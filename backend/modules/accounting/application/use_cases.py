from dataclasses import dataclass
from uuid import UUID

from modules.accounting.domain.account import (
    Account,
    AccountConflict,
    AccountNotFound,
    MethodNotFound,
)
from modules.accounting.domain.catalog import FLOW_CURRENCY, METHOD_LABELS


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

    def execute(self, is_active: bool | None = None) -> list[Account]:
        return self.accounts.list(is_active)


class GetAccount:
    def __init__(self, accounts):
        self.accounts = accounts

    def execute(self, account_id: UUID) -> Account:
        return _require(self.accounts, account_id)


class CreateAccount:
    def __init__(self, accounts):
        self.accounts = accounts

    def execute(self, name: object, currency: object) -> Account:
        return self.accounts.save(Account.create(name, currency))


class UpdateAccount:
    def __init__(self, accounts, mappings):
        self.accounts = accounts
        self.mappings = mappings

    def execute(self, account_id: UUID, name: object = None, currency: object = None) -> Account:
        self.mappings.lock_company()
        account = _require(self.accounts, account_id)
        if name is not None:
            account.rename(name)
        if currency is not None:
            account.change_currency(currency)
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
        mapping.configure(account, is_active)
        self.mappings.save(mapping)
        return MethodView(code, METHOD_LABELS[code], mapping.is_active, account)


def missing_methods(accounts, mappings) -> list[str]:
    """Códigos de los métodos activos sin un destino válido (cuenta activa en la moneda de los flujos)."""
    by_id = accounts.by_id()
    return [m.code for m in mappings.all() if not m.is_complete(by_id)]
