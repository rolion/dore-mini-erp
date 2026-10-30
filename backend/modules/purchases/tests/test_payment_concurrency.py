import threading
import time
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest import mock, skipUnless
from uuid import uuid4

from django.db import close_old_connections, connection, transaction
from django.test import TransactionTestCase

from modules.purchases.application.payment_commands import RegisterPayment
from modules.purchases.application.ports import Actor
from modules.purchases.domain.exceptions import PurchaseValidationError
from modules.purchases.domain.purchase import ItemDraft, Purchase
from modules.purchases.infrastructure.django.models import PaymentModel, SupplierModel
from modules.purchases.infrastructure.django.payment_repository import DjangoPaymentRepository
from modules.purchases.infrastructure.django.purchase_repository import DjangoPurchaseRepository

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
TODAY = date(2026, 10, 30)
ACTOR = Actor(uuid4(), 'Ana')
SLOW_SAVE = 0.6


@skipUnless(connection.vendor == 'postgresql', 'El bloqueo de fila requiere PostgreSQL.')
class PaymentRowLockTests(TransactionTestCase):
    """AC-13 con conexiones reales: el bloqueo de la compra serializa dos pagos que juntos excederían el saldo."""

    def setUp(self):
        self.company_id = uuid4()
        supplier = SupplierModel.objects.create(company_id=self.company_id, name='Sur')
        purchase = Purchase.create(supplier_id=supplier.id, purchase_date=TODAY,
                                   items=[ItemDraft(uuid4(), '10', '10.00', product_name='Harina')])  # total 100.00
        purchase.confirm(NOW)
        self.purchase = DjangoPurchaseRepository(self.company_id).save(purchase)

    def register(self, amount):
        def action():
            use_case = RegisterPayment(DjangoPurchaseRepository(self.company_id),
                                       DjangoPaymentRepository(self.company_id))
            return use_case.execute(self.purchase.id, uuid4(), amount, 'CASH', TODAY, ACTOR, TODAY)
        return action

    def test_two_simultaneous_payments_cannot_exceed_the_balance(self):
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
            a = threading.Thread(target=run, args=('first', self.register('60.00')))
            b = threading.Thread(target=run, args=('second', self.register('60.00')))
            a.start()
            self.assertTrue(holding.wait(5))
            b.start()
            a.join(10)
            b.join(10)
        failures = [r for r in results.values() if isinstance(r, PurchaseValidationError)]
        self.assertEqual(len(failures), 1, results)
        self.assertEqual(PaymentModel.objects.count(), 1)
        self.assertEqual(DjangoPaymentRepository(self.company_id).paid_total(self.purchase.id), Decimal('60.00'))
