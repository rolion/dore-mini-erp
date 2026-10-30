import threading
import time
from datetime import date, datetime, timezone
from unittest import mock
from uuid import uuid4

from django.db import close_old_connections, transaction
from django.test import TransactionTestCase

from modules.purchases.application.purchase_commands import CancelPurchase, ConfirmPurchase
from modules.purchases.domain.enums import PurchaseStatus
from modules.purchases.domain.purchase import ItemDraft, Purchase
from modules.purchases.infrastructure.django.purchase_repository import DjangoPurchaseRepository
from modules.purchases.infrastructure.django.repositories import DjangoSupplierRepository
from modules.purchases.infrastructure.django.models import PurchaseModel, SupplierModel

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
SLOW_SAVE = 0.6


class RowLockConcurrencyTests(TransactionTestCase):
    """AC-12 con conexiones reales: `select_for_update` serializa dos acciones simultáneas sobre la misma compra."""

    def setUp(self):
        self.company_id = uuid4()
        supplier = SupplierModel.objects.create(company_id=self.company_id, name='Sur')
        self.repo = DjangoPurchaseRepository(self.company_id)
        self.suppliers = DjangoSupplierRepository(self.company_id)
        purchase = Purchase.create(
            supplier_id=supplier.id, purchase_date=date(2026, 10, 29),
            items=[ItemDraft(uuid4(), '2', '10.00', product_name='Harina')])
        self.purchase_id = self.repo.save(purchase).id

    def race(self, first, second):
        """Lanza `first` y, cuando ya tiene la fila bloqueada, `second`; devuelve ambos resultados y las veces que se guardó."""
        saves = []
        original = DjangoPurchaseRepository.save
        holding = threading.Event()
        results = {}

        def slow_save(repo, purchase):
            saves.append(purchase.status)
            holding.set()
            time.sleep(SLOW_SAVE)  # conserva el bloqueo de la fila mientras el otro hilo intenta entrar
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
            a = threading.Thread(target=run, args=('first', first))
            b = threading.Thread(target=run, args=('second', second))
            a.start()
            self.assertTrue(holding.wait(5))
            b.start()
            a.join(10)
            b.join(10)
        return results, saves

    def confirm(self, now):
        return lambda: ConfirmPurchase(DjangoPurchaseRepository(self.company_id), self.suppliers).execute(
            self.purchase_id, now)

    def cancel(self, reason, now):
        return lambda: CancelPurchase(DjangoPurchaseRepository(self.company_id)).execute(self.purchase_id, reason, now)

    def test_two_simultaneous_confirmations_change_it_once(self):
        results, saves = self.race(self.confirm(NOW), self.confirm(LATER))
        self.assertEqual(saves, [PurchaseStatus.CONFIRMED])  # el segundo esperó y vio la compra ya confirmada
        self.assertEqual({r.confirmed_at for r in results.values()}, {NOW})
        self.assertEqual(PurchaseModel.objects.get(pk=self.purchase_id).confirmed_at, NOW)

    def test_two_simultaneous_cancellations_keep_the_first_reason(self):
        results, saves = self.race(self.cancel('Primera', NOW), self.cancel('Segunda', LATER))
        self.assertEqual(saves, [PurchaseStatus.CANCELLED])
        self.assertEqual({r.cancellation_reason for r in results.values()}, {'Primera'})
        row = PurchaseModel.objects.get(pk=self.purchase_id)
        self.assertEqual((row.status, row.cancellation_reason, row.cancelled_at), ('cancelled', 'Primera', NOW))

    def test_confirm_and_cancel_at_once_end_in_one_consistent_state(self):
        results, saves = self.race(self.confirm(NOW), self.cancel('x', LATER))
        self.assertFalse([r for r in results.values() if isinstance(r, Exception)])
        self.assertEqual(saves, [PurchaseStatus.CONFIRMED, PurchaseStatus.CANCELLED])  # en serie, nunca a la vez
        row = PurchaseModel.objects.get(pk=self.purchase_id)
        self.assertEqual((row.status, row.confirmed_at, row.cancelled_at), ('cancelled', NOW, LATER))
