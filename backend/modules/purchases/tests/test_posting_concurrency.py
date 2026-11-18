"""COM-02/COM-01: concurrencia entre pagos y recepciones contabilizados (hilos reales sobre PostgreSQL).

El primer hilo retiene el bloqueo de la compra (se retrasa su guardado) mientras el segundo intenta entrar; se
verifica el resultado final (libro y columnas de Compras), no el orden de llegada.
"""
import threading
import time
from decimal import Decimal
from unittest import mock, skipUnless
from uuid import uuid4

from django.db import close_old_connections, connection, transaction
from django.test import TransactionTestCase
from django.utils import timezone

from modules.accounting import services as accounting
from modules.accounts.testing import make_admin, make_company
from modules.catalog.infrastructure.django.models import ProductModel, UnitModel
from modules.inventory.infrastructure.django.models import StockMovementModel, WarehouseModel
from modules.purchases.application.payment_commands import RegisterPayment
from modules.purchases.application.ports import Actor
from modules.purchases.application.receipt_commands import ReceiptLineInput, RegisterReception
from modules.purchases.domain.purchase import ItemDraft, Purchase
from modules.purchases.infrastructure.adapters import ProductCatalogAdapter, PurchasePostingAdapter, StockEntryAdapter
from modules.purchases.infrastructure.django.models import PaymentModel, ReceiptModel, SupplierModel
from modules.purchases.infrastructure.django.payment_repository import DjangoPaymentRepository
from modules.purchases.infrastructure.django.purchase_repository import DjangoPurchaseRepository
from modules.purchases.infrastructure.django.receipt_repository import DjangoReceiptRepository
from modules.purchases.tests.payment_support import PaymentBooks

TODAY = timezone.localdate()
D = Decimal
ZERO = Decimal('0')
HOLD_SECONDS = 0.6


@skipUnless(connection.vendor == 'postgresql', 'El bloqueo de fila requiere PostgreSQL.')
class PostingConcurrencyCase(TransactionTestCase):
    """Compra confirmada de 100 kg a 10.00 (total 1.000,00), con Contabilidad e Inventario habilitados."""

    def setUp(self):
        self.company = make_company('Empresa Concurrente')
        self.user = make_admin(self.company, 'ana')
        self.books = PaymentBooks(self.company, extra_modules=('inventory',))
        # El corte de cobertura se crea al primer uso: se fija antes para que no serialice por casualidad a los hilos.
        accounting.coverage_status(self.company.id, TODAY)
        self.actor = Actor(self.user.pk, 'ana')
        supplier = SupplierModel.objects.create(company_id=self.company.id, name='Sur')
        kg = UnitModel.objects.create(company_id=self.company.id, name='Kilogramo', abbreviation='kg',
                                      allows_fractions=True)
        product = ProductModel.objects.create(company_id=self.company.id, name='Harina', sale_price=D('1.00'),
                                              base_unit=kg, tracks_stock=True, active=True, can_buy=True)
        self.warehouse = WarehouseModel.objects.create(company_id=self.company.id, name='Central', is_default=True)
        purchase = Purchase.create(supplier_id=supplier.id, purchase_date=TODAY, items=[
            ItemDraft(product.id, '100', '10.00', product_name='Harina', unit_abbreviation='kg')])
        purchase.confirm(timezone.now())
        self.purchase = DjangoPurchaseRepository(self.company.id).save(purchase)
        self.item_id = self.purchase.items[0].id

    # --- acciones (cada una corre en su propia transacción y conexión) --------------------------------------------

    def receive(self, quantity, receipt_id=None):
        def action():
            use_case = RegisterReception(
                DjangoPurchaseRepository(self.company.id), DjangoReceiptRepository(self.company.id),
                ProductCatalogAdapter(self.company.id), StockEntryAdapter(self.company.id),
                PurchasePostingAdapter(self.company.id), DjangoPaymentRepository(self.company.id))
            return use_case.execute(self.purchase.id, receipt_id or uuid4(), TODAY,
                                    [ReceiptLineInput(self.item_id, quantity)], self.warehouse.id, self.actor, TODAY)
        return action

    def pay(self, amount, payment_id=None):
        def action():
            use_case = RegisterPayment(
                DjangoPurchaseRepository(self.company.id), DjangoPaymentRepository(self.company.id),
                posting=PurchasePostingAdapter(self.company.id), receipts=DjangoReceiptRepository(self.company.id))
            return use_case.execute(self.purchase.id, payment_id or uuid4(), amount, 'CASH', TODAY, self.actor, TODAY)
        return action

    def run_overlapping(self, first, second):
        """Ejecuta `first` reteniendo el bloqueo de la compra y `second` intentando entrar; devuelve sus resultados."""
        holding = threading.Event()
        results: dict[str, object] = {}
        original = DjangoPurchaseRepository.save

        def slow_save(repo, purchase):
            holding.set()
            time.sleep(HOLD_SECONDS)  # conserva el bloqueo de la compra mientras el otro hilo espera
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
            self.assertTrue(holding.wait(10))
            b.start()
            a.join(30)
            b.join(30)
        return results

    def assert_no_errors(self, results):
        errors = {name: result for name, result in results.items() if isinstance(result, Exception)}
        self.assertEqual(errors, {}, results)
        self.assertEqual(set(results), {'first', 'second'})


class PaymentAgainstReceptionTests(PostingConcurrencyCase):
    def assert_consistent_books(self):
        """Mismo libro en cualquier orden: 400 recibidos y 500 pagados (400 de deuda y 100 de anticipo)."""
        b = self.books
        payable_debit, payable_credit = b.net(b.payable)
        advances_debit, advances_credit = b.net(b.advances)
        self.assertEqual(payable_credit - payable_debit, ZERO)  # no queda deuda
        self.assertEqual(advances_debit - advances_credit, D('100.00'))  # 100 de anticipo sin aplicar
        self.assertEqual(b.net(b.inventory), (D('400.00'), ZERO))
        payment = PaymentModel.objects.get(purchase_id=self.purchase.id)
        self.assertEqual(payment.debt_amount + payment.advance_amount, D('500.00'))
        self.assertEqual(b.net(b.caja), (ZERO, D('500.00')))
        applied = ReceiptModel.objects.get(purchase_id=self.purchase.id).advance_applied
        self.assertEqual(applied + payment.debt_amount, D('400.00'))  # lo recibido queda saldado

    def test_a_reception_that_lands_first_makes_the_payment_settle_debt_and_leave_an_advance(self):  # AC-13, AC-16
        results = self.run_overlapping(self.receive('40'), self.pay('500.00'))
        self.assert_no_errors(results)
        payment = PaymentModel.objects.get(purchase_id=self.purchase.id)
        self.assertEqual((payment.debt_amount, payment.advance_amount), (D('400.00'), D('100.00')))
        self.assert_consistent_books()

    def test_a_payment_that_lands_first_becomes_an_advance_that_the_reception_applies(self):  # AC-13, AC-16
        results = self.run_overlapping(self.pay('500.00'), self.receive('40'))
        self.assert_no_errors(results)
        payment = PaymentModel.objects.get(purchase_id=self.purchase.id)
        self.assertEqual((payment.debt_amount, payment.advance_amount), (ZERO, D('500.00')))
        self.assertEqual(ReceiptModel.objects.get(purchase_id=self.purchase.id).advance_applied, D('400.00'))
        self.assert_consistent_books()


class DuplicateRequestTests(PostingConcurrencyCase):
    def created_flags(self, results):
        return sorted(flag for _, flag in (results['first'], results['second']))

    def test_the_same_payment_sent_twice_at_once_is_registered_once(self):  # AC-12
        payment_id = uuid4()
        results = self.run_overlapping(self.pay('300.00', payment_id), self.pay('300.00', payment_id))
        self.assert_no_errors(results)
        self.assertEqual(self.created_flags(results), [False, True])
        self.assertEqual(PaymentModel.objects.filter(purchase_id=self.purchase.id).count(), 1)
        self.assertEqual(self.books.journal().count(), 1)  # sin recepciones: un solo asiento de anticipo
        self.assertEqual(self.books.net(self.books.caja), (ZERO, D('300.00')))

    def test_the_same_reception_sent_twice_at_once_is_registered_once(self):  # AC-04
        receipt_id = uuid4()
        results = self.run_overlapping(self.receive('40', receipt_id), self.receive('40', receipt_id))
        self.assert_no_errors(results)
        self.assertEqual(self.created_flags(results), [False, True])
        self.assertEqual(ReceiptModel.objects.filter(purchase_id=self.purchase.id).count(), 1)
        self.assertEqual(self.books.journal('PURCHASE_RECOGNITION').count(), 1)
        self.assertEqual(self.books.net(self.books.inventory), (D('400.00'), ZERO))
        self.assertEqual(StockMovementModel.objects.filter(company_id=self.company.id).count(), 1)
