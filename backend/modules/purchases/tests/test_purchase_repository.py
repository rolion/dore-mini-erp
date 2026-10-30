from datetime import date, datetime, timezone
from uuid import uuid4

from django.test import TestCase

from modules.purchases.domain.enums import PaymentStatus, PurchaseStatus, ReceptionStatus
from modules.purchases.domain.purchase import ItemDraft, Purchase
from modules.purchases.infrastructure.django.models import SupplierModel
from modules.purchases.infrastructure.django.purchase_repository import DjangoPurchaseRepository


def build(supplier_id, purchase_date=date(2026, 10, 29), items=None, **extra):
    drafts = [ItemDraft(uuid4(), '2', '10.00', product_name='Harina', unit_abbreviation='kg')
              for _ in range(2 if items is None else items)]
    return Purchase.create(supplier_id=supplier_id, purchase_date=purchase_date, items=drafts, **extra)


class PurchaseRepositoryTests(TestCase):
    def setUp(self):
        self.company_id = uuid4()
        self.repo = DjangoPurchaseRepository(self.company_id)
        self.supplier = SupplierModel.objects.create(company_id=self.company_id, name='Sur')

    def test_round_trip_keeps_lines_in_order(self):  # AC-01
        purchase = build(self.supplier.id, external_reference='F-1', notes='n')
        saved = self.repo.save(purchase)
        loaded = self.repo.get(purchase.id)
        self.assertEqual([i.product_id for i in loaded.items], [i.product_id for i in purchase.items])
        self.assertEqual((loaded.external_reference, loaded.notes, loaded.total), ('F-1', 'n', purchase.total))
        self.assertIsNotNone(saved.created_at)

    def test_lifecycle_fields_round_trip(self):  # INV-08, EDGE-07, AC-10
        now = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
        fresh = self.repo.get(self.repo.save(build(self.supplier.id)).id)
        self.assertEqual((fresh.status, fresh.confirmed_at, fresh.cancelled_at, fresh.cancellation_reason),
                         (PurchaseStatus.DRAFT, None, None, ''))
        self.assertEqual((fresh.reception_status, fresh.payment_status),
                         (ReceptionStatus.NOT_RECEIVED, PaymentStatus.UNPAID))
        confirmed = build(self.supplier.id)
        confirmed.confirm(now)
        self.repo.save(confirmed)
        loaded = self.repo.get(confirmed.id)
        self.assertEqual((loaded.status, loaded.confirmed_at, loaded.editable), (PurchaseStatus.CONFIRMED, now, False))
        loaded.cancel('Pedido duplicado', now)
        self.repo.save(loaded)
        cancelled = self.repo.get(confirmed.id)
        self.assertEqual((cancelled.status, cancelled.cancelled_at, cancelled.cancellation_reason),
                         (PurchaseStatus.CANCELLED, now, 'Pedido duplicado'))
        self.assertEqual(cancelled.confirmed_at, now)

    def test_save_replaces_the_lines(self):  # AC-07
        purchase = build(self.supplier.id)
        self.repo.save(purchase)
        purchase.update(items=[ItemDraft(uuid4(), '1', '5.00', product_name='Azúcar')])
        self.repo.save(purchase)
        self.assertEqual([i.product_name for i in self.repo.get(purchase.id).items], ['Azúcar'])

    def test_other_company_cannot_read_or_list(self):  # INV-11
        purchase = build(self.supplier.id)
        self.repo.save(purchase)
        other = DjangoPurchaseRepository(uuid4())
        self.assertIsNone(other.get(purchase.id))
        self.assertEqual(len(other.list()), 0)

    def test_list_orders_filters_and_summarizes(self):  # AC-09
        other_supplier = SupplierModel.objects.create(company_id=self.company_id, name='Norte')
        old = self.repo.save(build(self.supplier.id, purchase_date=date(2026, 10, 1)))
        new = self.repo.save(build(self.supplier.id, purchase_date=date(2026, 10, 20), items=1))
        mine = self.repo.save(build(other_supplier.id, purchase_date=date(2026, 10, 10), items=0))
        rows = list(self.repo.list())
        self.assertEqual([r.id for r in rows], [new.id, mine.id, old.id])
        self.assertEqual((rows[0].supplier_name, rows[0].items_count, rows[0].total), ('Sur', 1, new.total))
        self.assertEqual([r.id for r in self.repo.list(supplier_id=other_supplier.id)], [mine.id])
        self.assertEqual(len(self.repo.list()[0:2]), 2)
