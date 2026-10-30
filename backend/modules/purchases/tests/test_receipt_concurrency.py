import threading
import time
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest import mock
from uuid import uuid4

from django.db import close_old_connections, transaction
from django.test import TransactionTestCase

from modules.purchases.application.ports import Actor, StockEntryMovement  # noqa: F401
from modules.purchases.application.receipt_commands import ReceiptLineInput, RegisterReception
from modules.purchases.domain.exceptions import PurchaseValidationError
from modules.purchases.domain.purchase import ItemDraft, Purchase
from modules.purchases.infrastructure.django.models import ReceiptModel, SupplierModel
from modules.purchases.infrastructure.django.purchase_repository import DjangoPurchaseRepository
from modules.purchases.infrastructure.django.receipt_repository import DjangoReceiptRepository
from modules.purchases.tests.test_receipt_application import ACTOR, FakeStock
from modules.purchases.tests.test_purchase_application import FakeProducts

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
TODAY = date(2026, 10, 30)
SLOW_SAVE = 0.6


class ReceiptRowLockTests(TransactionTestCase):
    """AC-17 con conexiones reales: el bloqueo de la compra serializa dos recepciones que juntas excederían lo comprado."""

    def setUp(self):
        self.company_id = uuid4()
        supplier = SupplierModel.objects.create(company_id=self.company_id, name='Sur')
        purchase = Purchase.create(supplier_id=supplier.id, purchase_date=TODAY,
                                   items=[ItemDraft(uuid4(), '10', '5.00', product_name='Harina')])
        purchase.confirm(NOW)
        self.purchase = DjangoPurchaseRepository(self.company_id).save(purchase)

    def register(self, quantity):
        def action():
            use_case = RegisterReception(DjangoPurchaseRepository(self.company_id),
                                         DjangoReceiptRepository(self.company_id), FakeProducts(),
                                         FakeStock(enabled=False))
            return use_case.execute(self.purchase.id, uuid4(), TODAY,
                                    [ReceiptLineInput(self.purchase.items[0].id, quantity)], None, ACTOR, TODAY)
        return action

    def test_two_simultaneous_receptions_cannot_exceed_the_purchased_quantity(self):
        holding = threading.Event()
        results = {}
        original = DjangoPurchaseRepository.save

        def slow_save(repo, purchase):
            holding.set()
            time.sleep(SLOW_SAVE)  # conserva el bloqueo de la compra mientras el otro hilo intenta entrar
            return original(repo, purchase)

        def run(name, action):
            try:
                with transaction.atomic():
                    results[name] = action()
            except Exception as exc:  # noqa: BLE001 - se informa al test
                results[name] = exc
            finally:
                close_old_connections()

        with mock.patch.object(DjangoPurchaseRepository, 'save', slow_save):
            a = threading.Thread(target=run, args=('first', self.register('6')))
            b = threading.Thread(target=run, args=('second', self.register('6')))
            a.start()
            self.assertTrue(holding.wait(5))
            b.start()
            a.join(10)
            b.join(10)
        failures = [r for r in results.values() if isinstance(r, PurchaseValidationError)]
        self.assertEqual(len(failures), 1, results)
        self.assertEqual(ReceiptModel.objects.count(), 1)
        totals = DjangoReceiptRepository(self.company_id).received_totals(self.purchase.id)
        self.assertEqual(list(totals.values()), [Decimal('6.000')])
