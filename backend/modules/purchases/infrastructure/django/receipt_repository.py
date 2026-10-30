from decimal import Decimal
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import QuerySet, Sum

from modules.purchases.domain.enums import ReceiptStatus
from modules.purchases.domain.exceptions import ReceiptConflict
from modules.purchases.domain.receipt import Receipt

from .mappers import receipt_to_entity
from .models import ReceiptItemModel, ReceiptModel


class DjangoReceiptRepository:
    """Repositorio acotado a una empresa: toda consulta filtra por `company_id`."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _receipts(self) -> QuerySet:
        return ReceiptModel.objects.filter(company_id=self.company_id)

    def get(self, receipt_id: UUID) -> Receipt | None:
        model = self._receipts().filter(pk=receipt_id).first()
        return None if model is None else receipt_to_entity(model, model.items.all())

    def save(self, receipt: Receipt) -> Receipt:
        try:
            with transaction.atomic():  # savepoint: un id repetido no aborta la transacción del llamador
                return self._insert(receipt)
        except IntegrityError as exc:
            raise ReceiptConflict() from exc

    def _insert(self, receipt: Receipt) -> Receipt:
        model = ReceiptModel.objects.create(
            id=receipt.id, company_id=self.company_id, purchase_id=receipt.purchase_id,
            receipt_date=receipt.receipt_date, status=receipt.status.value, warehouse_id=receipt.warehouse_id,
            user_id=receipt.user_id, user_name=receipt.user_name)
        ReceiptItemModel.objects.bulk_create([
            ReceiptItemModel(receipt=model, position=position, purchase_item_id=line.purchase_item_id,
                             product_id=line.product_id, product_name=line.product_name,
                             unit_abbreviation=line.unit_abbreviation, quantity=line.quantity)
            for position, line in enumerate(receipt.lines)])
        return receipt_to_entity(model, model.items.all())

    def list_for_purchase(self, purchase_id: UUID) -> list[Receipt]:
        models = list(self._receipts().filter(purchase_id=purchase_id).prefetch_related('items'))
        return [receipt_to_entity(m, m.items.all()) for m in models]

    def received_totals(self, purchase_id: UUID) -> dict[UUID, Decimal]:
        rows = (ReceiptItemModel.objects
                .filter(receipt__company_id=self.company_id, receipt__purchase_id=purchase_id,
                        receipt__status=ReceiptStatus.CONFIRMED.value)
                .values('purchase_item_id').annotate(total=Sum('quantity')))
        return {row['purchase_item_id']: row['total'] for row in rows}
