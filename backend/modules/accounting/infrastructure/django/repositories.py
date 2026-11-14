from uuid import UUID

from django.db import IntegrityError, transaction

from modules.accounting.domain.account import Account, AccountValidationError, MethodMapping
from modules.accounting.domain.catalog import METHOD_CODES

from .models import AccountModel, MethodMappingModel

DUPLICATE_NAME = 'Ya existe una cuenta con ese nombre.'


def _account(model: AccountModel) -> Account:
    return Account(id=model.id, name=model.name, currency=model.currency, is_active=model.is_active,
                   created_at=model.created_at, updated_at=model.updated_at)


class DjangoAccountRepository:
    """Repositorio acotado a una empresa: toda consulta filtra por `company_id`."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _accounts(self):
        return AccountModel.objects.filter(company_id=self.company_id)

    def get(self, account_id: UUID) -> Account | None:
        model = self._accounts().filter(pk=account_id).first()
        return _account(model) if model else None

    def list(self, is_active: bool | None = None) -> list[Account]:
        queryset = self._accounts().order_by('name', 'id')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        return [_account(model) for model in queryset]

    def by_id(self) -> dict[UUID, Account]:
        return {account.id: account for account in self.list()}

    def save(self, account: Account) -> Account:
        if self._accounts().exclude(pk=account.id).filter(name__iexact=account.name).exists():
            raise AccountValidationError({'name': [DUPLICATE_NAME]})
        try:
            with transaction.atomic():
                AccountModel.objects.update_or_create(
                    id=account.id, company_id=self.company_id,
                    defaults={'name': account.name, 'currency': account.currency, 'is_active': account.is_active})
        except IntegrityError:  # carrera con otra petición: la restricción única manda
            raise AccountValidationError({'name': [DUPLICATE_NAME]}) from None
        return _account(self._accounts().get(pk=account.id))


class DjangoMethodMappingRepository:
    """Mapeo método → cuenta de una empresa. Los métodos sin fila se tratan como activos y sin destino."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _rows(self):
        return MethodMappingModel.objects.filter(company_id=self.company_id)

    def all(self) -> list[MethodMapping]:
        rows = {row.method: row for row in self._rows()}
        return [
            MethodMapping(code, rows[code].is_active, rows[code].account_id) if code in rows else MethodMapping(code)
            for code in METHOD_CODES
        ]

    def get(self, code: str) -> MethodMapping | None:
        return next((m for m in self.all() if m.code == code), None)

    def save(self, mapping: MethodMapping) -> None:
        MethodMappingModel.objects.update_or_create(
            company_id=self.company_id, method=mapping.code,
            defaults={'account_id': mapping.account_id, 'is_active': mapping.is_active})

    def lock_company(self) -> None:
        """Serializa cambios de cuentas/mapeo de la empresa (bloquea sus cuentas) dentro de una transacción."""
        list(AccountModel.objects.select_for_update().filter(company_id=self.company_id).values_list('id', flat=True))
