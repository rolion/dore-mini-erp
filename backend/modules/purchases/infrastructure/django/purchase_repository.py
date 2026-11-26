from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.db.models import CharField, Count, DecimalField, OuterRef, Q, QuerySet, Subquery, Sum
from django.db.models.functions import Cast, Coalesce

from modules.purchases.domain.enums import PaymentStatus, PurchaseStatus, ReceptionStatus
from modules.purchases.domain.purchase import Purchase, PurchaseNumber, provisional_reference
from modules.purchases.domain.repositories import PurchaseFilters, PurchaseSummary

from .mappers import purchase_to_entity, purchase_to_model_values
from .models import PaymentModel, PurchaseItemModel, PurchaseModel, SupplierModel

HEX_DIGITS = frozenset('0123456789abcdef')


class PurchaseList:
    """Vista perezosa de resúmenes sobre un queryset: permite paginar sin cargar todas las compras."""

    def __init__(self, company_id: UUID, queryset: QuerySet):
        self._company_id = company_id
        self._queryset = queryset

    def count(self) -> int:
        return self._queryset.count()

    def __len__(self) -> int:
        return self.count()

    def _summaries(self, models) -> list[PurchaseSummary]:
        models = list(models)
        names = dict(SupplierModel.objects.filter(
            company_id=self._company_id, pk__in={m.supplier_id for m in models}).values_list('id', 'name'))
        return [self._summary(m, names.get(m.supplier_id, '')) for m in models]

    @staticmethod
    def _summary(m, supplier_name: str) -> PurchaseSummary:
        status = PurchaseStatus(m.status)
        confirmed = status is PurchaseStatus.CONFIRMED
        number = (PurchaseNumber(m.fiscal_period_id, m.fiscal_period_name, m.number)
                  if m.number is not None else None)
        return PurchaseSummary(
            id=m.id, purchase_date=m.purchase_date, supplier_id=m.supplier_id, supplier_name=supplier_name,
            external_reference=m.external_reference, total=m.total, status=status, items_count=m.items_count,
            reference=number.code if number else provisional_reference(m.id), number=number,
            reception_status=ReceptionStatus(m.reception_status) if confirmed else None,
            payment_status=PaymentStatus(m.payment_status) if confirmed else None,
            paid_total=m.paid_total if confirmed else None,
            balance=m.total - m.paid_total if confirmed else None)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return self._summaries(self._queryset[index])
        return self._summaries([self._queryset[index]])[0]

    def __iter__(self):
        return iter(self._summaries(self._queryset))


class DjangoPurchaseRepository:
    """Repositorio acotado a una empresa: toda consulta filtra por `company_id` y `save` lo establece al crear."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _purchases(self) -> QuerySet:
        return PurchaseModel.objects.filter(company_id=self.company_id)

    def get(self, purchase_id: UUID, for_update: bool = False) -> Purchase | None:
        queryset = self._purchases()
        if for_update:
            queryset = queryset.select_for_update()
        model = queryset.filter(pk=purchase_id).first()
        if model is None:
            return None
        return purchase_to_entity(model, model.items.all())

    @transaction.atomic
    def save(self, purchase: Purchase) -> Purchase:
        model, _ = PurchaseModel.objects.update_or_create(
            id=purchase.id, company_id=self.company_id, defaults=purchase_to_model_values(purchase))
        model.items.all().delete()
        PurchaseItemModel.objects.bulk_create([
            PurchaseItemModel(
                id=item.id, purchase=model, position=position, product_id=item.product_id,
                product_name=item.product_name, unit_abbreviation=item.unit_abbreviation,
                quantity=item.quantity, unit_price=item.unit_price, subtotal=item.subtotal)
            for position, item in enumerate(purchase.items)])
        return purchase_to_entity(model, model.items.all())

    def _paid_total(self):
        """Suma de pagos confirmados de la compra, solo de esta empresa."""
        money = DecimalField(max_digits=12, decimal_places=2)
        paid = PaymentModel.objects.filter(
            company_id=self.company_id, purchase_id=OuterRef('pk'), status='confirmed',
        ).order_by().values('purchase_id').annotate(total=Sum('amount')).values('total')
        return Coalesce(Subquery(paid, output_field=money), Decimal('0.00'), output_field=money)

    def list(self, supplier_id: UUID | None = None, filters: PurchaseFilters | None = None) -> PurchaseList:
        queryset = self._purchases().annotate(
            items_count=Count('items'), paid_total=self._paid_total(),
        ).order_by('-purchase_date', '-created_at', 'id')
        if supplier_id is not None:
            queryset = queryset.filter(supplier_id=supplier_id)
        if filters is not None:
            queryset = self._apply(queryset, filters)
        return PurchaseList(self.company_id, queryset)

    @staticmethod
    def _apply(queryset: QuerySet, f: PurchaseFilters) -> QuerySet:
        if f.supplier_id is not None:
            queryset = queryset.filter(supplier_id=f.supplier_id)
        if f.date_from is not None:
            queryset = queryset.filter(purchase_date__gte=f.date_from)
        if f.date_to is not None:
            queryset = queryset.filter(purchase_date__lte=f.date_to)
        if f.status is not None:
            queryset = queryset.filter(status=f.status.value)
        # Recepción y pago solo existen en compras confirmadas.
        if f.reception_status or f.payment_status or f.pending_payment:
            queryset = queryset.filter(status=PurchaseStatus.CONFIRMED.value)
        if f.reception_status is not None:
            queryset = queryset.filter(reception_status=f.reception_status.value)
        if f.payment_status is not None:
            queryset = queryset.filter(payment_status=f.payment_status.value)
        if f.pending_payment:
            queryset = queryset.filter(payment_status__in=[PaymentStatus.UNPAID.value, PaymentStatus.PARTIAL.value])
        if f.search:
            match = Q(external_reference__icontains=f.search)
            text = f.search.strip().lower()
            # `NC-000012` o `12`: el número de la serie (un número por período: devuelve todos los períodos).
            digits = text.removeprefix('nc-')
            # `isascii`: `isdigit()` acepta superíndices (`²`) que `int()` rechaza (500).
            if digits.isascii() and digits.isdigit() and int(digits) > 0 and len(digits) <= 9:
                match |= Q(number=int(digits))
            # La referencia provisional es COM- + los 8 primeros hex del id (borradores y heredadas sin número).
            prefix = text.removeprefix('com-')
            if 1 <= len(prefix) <= 8 and set(prefix) <= HEX_DIGITS:
                queryset = queryset.annotate(id_text=Cast('id', CharField())).filter(
                    match | Q(id_text__startswith=prefix))
            else:
                queryset = queryset.filter(match)
        return queryset
