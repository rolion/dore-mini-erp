from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import Count, Max, Min, Q, Sum
from django.utils import timezone

from modules.accounting.domain.account import Account, AccountValidationError, MethodMapping
from modules.accounting.domain.catalog import METHOD_CODES, OPERATION_RECORD
from modules.accounting.domain.classification import Classification
from modules.accounting.domain.coverage import Period
from modules.accounting.domain.entry import Entry

from .models import (
    AccountClassSettingModel,
    AccountModel,
    ClassificationModel,
    CoveragePeriodModel,
    EntryModel,
    MethodMappingModel,
    SettingsModel,
)

DUPLICATE_NAME = 'Ya existe una cuenta con ese nombre.'


def _account(model: AccountModel) -> Account:
    return Account(id=model.id, name=model.name, currency=model.currency, is_active=model.is_active,
                   created_at=model.created_at, updated_at=model.updated_at, kind=model.kind,
                   opening_balance=model.opening_balance, account_class=model.account_class)


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
                    defaults={'name': account.name, 'currency': account.currency, 'is_active': account.is_active,
                              'kind': account.kind, 'opening_balance': account.opening_balance,
                              'account_class': account.account_class})
        except IntegrityError:  # carrera con otra petición: la restricción única manda
            raise AccountValidationError({'name': [DUPLICATE_NAME]}) from None
        return _account(self._accounts().get(pk=account.id))


class DjangoAccountClassRepository:
    """Estado de las seis clasificaciones contables de una empresa (sin fila = habilitada)."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def disabled(self) -> frozenset[str]:
        rows = AccountClassSettingModel.objects.filter(company_id=self.company_id, is_enabled=False)
        return frozenset(rows.values_list('code', flat=True))

    def set_enabled(self, code: str, enabled: bool) -> None:
        try:
            with transaction.atomic():
                AccountClassSettingModel.objects.update_or_create(
                    company_id=self.company_id, code=code, defaults={'is_enabled': enabled})
        except IntegrityError:  # carrera al crear la fila: la restricción única manda; se actualiza la existente
            AccountClassSettingModel.objects.filter(company_id=self.company_id, code=code).update(is_enabled=enabled)


DUPLICATE_CLASSIFICATION = 'Ya existe una clasificación con ese nombre y dirección.'


def _classification(model: ClassificationModel) -> Classification:
    return Classification(id=model.id, name=model.name, direction=model.direction, is_active=model.is_active,
                          created_at=model.created_at, updated_at=model.updated_at)


class DjangoClassificationRepository:
    """Repositorio de clasificaciones acotado a una empresa."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _rows(self):
        return ClassificationModel.objects.filter(company_id=self.company_id)

    def get(self, classification_id: UUID) -> Classification | None:
        model = self._rows().filter(pk=classification_id).first()
        return _classification(model) if model else None

    def list(self, is_active: bool | None = None, direction: str | None = None) -> list[Classification]:
        queryset = self._rows().order_by('name', 'id')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        if direction is not None:
            queryset = queryset.filter(direction=direction)
        return [_classification(model) for model in queryset]

    def save(self, classification: Classification) -> Classification:
        if self._rows().exclude(pk=classification.id).filter(
                name__iexact=classification.name, direction=classification.direction).exists():
            raise AccountValidationError({'name': [DUPLICATE_CLASSIFICATION]})
        try:
            with transaction.atomic():
                ClassificationModel.objects.update_or_create(
                    id=classification.id, company_id=self.company_id,
                    defaults={'name': classification.name, 'direction': classification.direction,
                              'is_active': classification.is_active})
        except IntegrityError:
            raise AccountValidationError({'name': [DUPLICATE_CLASSIFICATION]}) from None
        return _classification(self._rows().get(pk=classification.id))


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


class DjangoCoverageRepository:
    """Ajustes de corte y tramos de cobertura de una empresa; toda consulta filtra por `company_id`."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def cutoff_date(self) -> date | None:
        return SettingsModel.objects.filter(company_id=self.company_id).values_list('cutoff_date', flat=True).first()

    def create_cutoff(self, cutoff: date) -> date:
        """Crea el corte si no existe (idempotente: nunca pisa uno existente) y devuelve el vigente."""
        row, _ = SettingsModel.objects.get_or_create(company_id=self.company_id, defaults={'cutoff_date': cutoff})
        return row.cutoff_date

    def set_cutoff(self, cutoff: date) -> None:
        SettingsModel.objects.filter(company_id=self.company_id).update(cutoff_date=cutoff)

    def periods(self) -> list[Period]:
        return [Period(timezone.localtime(row.started_at).date(),
                       timezone.localtime(row.ended_at).date() if row.ended_at else None)
                for row in CoveragePeriodModel.objects.filter(company_id=self.company_id)]

    def first_started_on(self) -> date | None:
        periods = self.periods()
        return periods[0].started_on if periods else None

    def has_open_period(self) -> bool:
        return CoveragePeriodModel.objects.filter(company_id=self.company_id, ended_at__isnull=True).exists()

    def open_period(self) -> None:
        """Abre un tramo si no hay uno abierto (idempotente; la restricción única parcial resuelve las carreras)."""
        try:
            with transaction.atomic():
                CoveragePeriodModel.objects.get_or_create(company_id=self.company_id, ended_at__isnull=True,
                                                          defaults={'started_at': timezone.now()})
        except IntegrityError:
            pass

    def close_period(self) -> None:
        CoveragePeriodModel.objects.filter(company_id=self.company_id, ended_at__isnull=True).update(
            ended_at=timezone.now())


def _entry(model: EntryModel) -> Entry:
    return Entry(id=model.id, account_id=model.account_id, currency=model.currency, amount=model.amount,
                 payment_date=model.payment_date, method=model.payment_method, origin_kind=model.origin_kind,
                 origin_id=model.origin_id, origin_document_ref=model.origin_document_ref,
                 receipt_number=model.receipt_number, recorded_by=model.recorded_by,
                 recorded_by_name=model.recorded_by_name, created_at=model.created_at,
                 regularized_at=model.regularized_at, regularized_by_name=model.regularized_by_name,
                 direction=model.direction, operation=model.operation, classification_id=model.classification_id,
                 reverses_id=model.reverses_id)


@dataclass(frozen=True)
class EntryFilters:
    date_from: date | None = None
    date_to: date | None = None
    account_id: UUID | None = None
    method: str | None = None
    origin: str | None = None
    direction: str | None = None


@dataclass(frozen=True)
class CurrencyTotal:
    """Totales de una moneda. `amount`/`by_origin` son los ingresos originales (compatibles con la API anterior)."""
    currency: str
    count: int
    amount: Decimal
    by_origin: dict[str, Decimal]
    expense: Decimal = Decimal('0.00')
    reversed_income: Decimal = Decimal('0.00')  # cobros revertidos
    reversed_expense: Decimal = Decimal('0.00')  # egresos revertidos (devuelven dinero)

    @property
    def net(self) -> Decimal:
        return self.amount - self.expense - self.reversed_income + self.reversed_expense


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
                    recorded_by=entry.recorded_by, recorded_by_name=entry.recorded_by_name,
                    regularized_at=entry.regularized_at, regularized_by_name=entry.regularized_by_name,
                    direction=entry.direction, operation=entry.operation, classification_id=entry.classification_id,
                    reverses_id=entry.reverses_id)
            return _entry(row), True
        except IntegrityError:
            existing = self._rows().filter(origin_kind=entry.origin_kind, origin_id=entry.origin_id,
                                           operation=entry.operation).first()
            if existing is None:
                raise
            return _entry(existing), False

    def by_origin(self, origin_kind: str, origin_ids) -> dict[UUID, Entry]:
        """Entradas de la empresa de ese origen para los IDs dados (lectura en bloques, sin N+1)."""
        ids = list(origin_ids)
        found: dict[UUID, Entry] = {}
        for start in range(0, len(ids), 1000):
            for row in self._rows().filter(origin_kind=origin_kind, operation=OPERATION_RECORD,
                                           origin_id__in=ids[start:start + 1000]):
                found[row.origin_id] = _entry(row)
        return found

    def get_by_origin(self, origin_kind: str, origin_id: UUID, operation: str) -> Entry | None:
        row = self._rows().filter(origin_kind=origin_kind, origin_id=origin_id, operation=operation).first()
        return _entry(row) if row else None

    def net_by_account(self, account_ids=None) -> dict[UUID, Decimal]:
        """Efecto neto de los movimientos por cuenta: ingresos suman y egresos restan (incluidas las reversiones)."""
        rows = self._rows()
        if account_ids is not None:
            rows = rows.filter(account_id__in=list(account_ids))
        grouped = rows.order_by().values('account_id').annotate(
            income=Sum('amount', filter=Q(direction='INCOME')), expense=Sum('amount', filter=Q(direction='EXPENSE')))
        zero = Decimal('0.00')
        return {row['account_id']: (row['income'] or zero) - (row['expense'] or zero) for row in grouped}

    def get(self, entry_id: UUID) -> EntryModel | None:
        return self._rows().select_related('account', 'reverses', 'reversed_by_entry').filter(pk=entry_id).first()

    def has_entries_for_account(self, account_id: UUID) -> bool:
        return self._rows().filter(account_id=account_id).exists()

    def has_entries(self) -> bool:
        return self._rows().exists()

    def first_payment_date(self) -> date | None:
        return self._rows().aggregate(first=Min('payment_date'))['first']

    def query(self, filters: EntryFilters):
        rows = self._rows().select_related('account', 'reverses', 'reversed_by_entry')
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
        if filters.direction:
            rows = rows.filter(direction=filters.direction)
        return rows

    def totals(self, filters: EntryFilters) -> list[CurrencyTotal]:
        """Totales de TODO el conjunto filtrado (no de una página), por moneda y sin conversión."""
        grouped = (self.query(filters).order_by().values('currency', 'origin_kind', 'direction', 'operation')
                   .annotate(total=Sum('amount'), n=Count('id')))
        by_currency: dict[str, dict] = {}
        zero = Decimal('0.00')
        for row in grouped:
            bucket = by_currency.setdefault(row['currency'], {
                'count': 0, 'by_origin': {}, 'expense': zero, 'reversed_income': zero, 'reversed_expense': zero})
            bucket['count'] += row['n']
            if row['operation'] == OPERATION_RECORD:
                if row['direction'] == 'INCOME':
                    bucket['by_origin'][row['origin_kind']] = bucket['by_origin'].get(row['origin_kind'], zero) + row['total']
                else:
                    bucket['expense'] += row['total']
            elif row['direction'] == 'EXPENSE':  # reversión de un ingreso
                bucket['reversed_income'] += row['total']
            else:  # reversión de un egreso
                bucket['reversed_expense'] += row['total']
        return [CurrencyTotal(currency, data['count'], sum(data['by_origin'].values(), zero), data['by_origin'],
                              data['expense'], data['reversed_income'], data['reversed_expense'])
                for currency, data in sorted(by_currency.items())]

    def coverage(self) -> Coverage:
        aggregate = self._rows().aggregate(first=Min('payment_date'), last=Max('payment_date'),
                                           recorded=Min('created_at'))
        return Coverage(aggregate['first'], aggregate['last'], aggregate['recorded'])
