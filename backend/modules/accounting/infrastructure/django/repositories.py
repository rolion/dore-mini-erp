from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import Count, Max, Min, Sum

from modules.accounting.domain.account import Account, AccountValidationError, MethodMapping
from modules.accounting.domain.catalog import METHOD_CODES
from modules.accounting.domain.entry import Entry

from .models import AccountModel, EntryModel, MethodMappingModel

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

    def get_for_update(self, account_id: UUID) -> Account | None:
        """Como `get`, bloqueando la fila: serializa el registro de entradas con los cambios de la cuenta."""
        model = self._accounts().select_for_update().filter(pk=account_id).first()
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


def _entry(model: EntryModel) -> Entry:
    return Entry(id=model.id, account_id=model.account_id, currency=model.currency, amount=model.amount,
                 payment_date=model.payment_date, method=model.payment_method, origin_kind=model.origin_kind,
                 origin_id=model.origin_id, origin_document_ref=model.origin_document_ref,
                 receipt_number=model.receipt_number, recorded_by=model.recorded_by,
                 recorded_by_name=model.recorded_by_name, created_at=model.created_at)


@dataclass(frozen=True)
class EntryFilters:
    date_from: date | None = None
    date_to: date | None = None
    account_id: UUID | None = None
    method: str | None = None
    origin: str | None = None


@dataclass(frozen=True)
class CurrencyTotal:
    currency: str
    count: int
    amount: Decimal
    by_origin: dict[str, Decimal]


@dataclass(frozen=True)
class Coverage:
    first_payment_date: date | None
    last_payment_date: date | None
    first_recorded_at: datetime | None


class DjangoEntryRepository:
    """Libro de entradas de una empresa: toda consulta filtra por `company_id`. Solo inserta y lee."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _rows(self):
        return EntryModel.objects.filter(company_id=self.company_id)

    def insert(self, entry: Entry) -> tuple[Entry, bool]:
        """Inserta la entrada o devuelve la existente del mismo origen: `(entrada, creada)`.

        El `INSERT` va en un punto de guardado: si la restricción única salta (carrera o reintento) la transacción
        del llamante sigue siendo utilizable.
        """
        try:
            with transaction.atomic():
                row = EntryModel.objects.create(
                    id=entry.id, company_id=self.company_id, account_id=entry.account_id, currency=entry.currency,
                    amount=entry.amount, payment_date=entry.payment_date, payment_method=entry.method,
                    origin_kind=entry.origin_kind, origin_id=entry.origin_id,
                    origin_document_ref=entry.origin_document_ref, receipt_number=entry.receipt_number,
                    recorded_by=entry.recorded_by, recorded_by_name=entry.recorded_by_name)
            return _entry(row), True
        except IntegrityError:
            existing = self._rows().filter(origin_kind=entry.origin_kind, origin_id=entry.origin_id).first()
            if existing is None:
                raise
            return _entry(existing), False

    def get(self, entry_id: UUID) -> EntryModel | None:
        return self._rows().select_related('account').filter(pk=entry_id).first()

    def has_entries_for_account(self, account_id: UUID) -> bool:
        return self._rows().filter(account_id=account_id).exists()

    def query(self, filters: EntryFilters):
        rows = self._rows().select_related('account')
        if filters.date_from:
            rows = rows.filter(payment_date__gte=filters.date_from)
        if filters.date_to:
            rows = rows.filter(payment_date__lte=filters.date_to)
        if filters.account_id:
            rows = rows.filter(account_id=filters.account_id)
        if filters.method:
            rows = rows.filter(payment_method=filters.method)
        if filters.origin:
            rows = rows.filter(origin_kind=filters.origin)
        return rows

    def totals(self, filters: EntryFilters) -> list[CurrencyTotal]:
        """Totales de TODO el conjunto filtrado (no de una página), por moneda y sin conversión."""
        grouped = (self.query(filters).order_by().values('currency', 'origin_kind')
                   .annotate(total=Sum('amount'), n=Count('id')))
        by_currency: dict[str, dict] = {}
        for row in grouped:
            bucket = by_currency.setdefault(row['currency'], {'count': 0, 'by_origin': {}})
            bucket['count'] += row['n']
            bucket['by_origin'][row['origin_kind']] = row['total']
        return [CurrencyTotal(currency, data['count'], sum(data['by_origin'].values(), Decimal('0')), data['by_origin'])
                for currency, data in sorted(by_currency.items())]

    def coverage(self) -> Coverage:
        aggregate = self._rows().aggregate(first=Min('payment_date'), last=Max('payment_date'),
                                           recorded=Min('created_at'))
        return Coverage(aggregate['first'], aggregate['last'], aggregate['recorded'])
