"""PB-INV-008: revertir una recepción de compra (dominio, aplicación y API con BD real)."""
from datetime import date, datetime, timezone
from decimal import Decimal
import threading
from unittest import mock, skipUnless
from uuid import UUID, uuid4

from django.db import close_old_connections, connection, transaction
from django.test import SimpleTestCase, TransactionTestCase
from django.utils import timezone as dj_timezone

from modules.inventory import services as inventory
from modules.inventory.infrastructure.django.models import StockMovementModel
from modules.purchases.application.ports import Actor
from modules.purchases.application.receipt_commands import ReceiptLineInput, RegisterReception, RevertReception
from modules.purchases.domain.enums import InventoryMode, ReceiptStatus
from modules.purchases.domain.exceptions import (
    PurchaseValidationError,
    ReceiptAlreadyReverted,
    ReceiptInventoryUnavailable,
    ReceiptNotFound,
)
from modules.purchases.domain.purchase import ItemDraft, Purchase
from modules.purchases.domain.receipt import Receipt, ReceiptLine
from modules.purchases.infrastructure.django.models import PaymentModel, ReceiptModel, SupplierModel
from modules.purchases.infrastructure.django.purchase_repository import DjangoPurchaseRepository
from modules.purchases.infrastructure.django.receipt_repository import DjangoReceiptRepository
from modules.purchases.tests.test_purchase_application import FakeProducts
from modules.purchases.tests.test_receipt_application import FakeStock
from modules.purchases.tests.test_receipt_api import ReceiptApiTestCase, purchase_url
from modules.inventory.tests.policy import set_negative_stock

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
TODAY = date(2026, 10, 30)
ACTOR = Actor(uuid4(), 'Ana')


def make_receipt(**extra) -> Receipt:
    values = dict(id=uuid4(), purchase_id=uuid4(), receipt_date=date(2026, 10, 30), user_id=None, user_name='ana',
                  lines=[ReceiptLine(uuid4(), uuid4(), 'Harina', 'kg', Decimal('4'))])
    values.update(extra)
    return Receipt(**values)


class ReceiptRevertDomainTests(SimpleTestCase):
    def test_revert_sets_status_and_reversal_data(self):  # INV-06
        receipt = make_receipt()
        receipt.revert('  Error de conteo ', ACTOR.user_id, 'Ana', NOW)
        self.assertEqual((receipt.status, receipt.reverted_at, receipt.reverted_by_name, receipt.revert_reason),
                         (ReceiptStatus.REVERTED, NOW, 'Ana', 'Error de conteo'))

    def test_reason_is_required_and_limited(self):  # AC-09
        for bad in (None, '', '   ', 5, 'x' * 201):
            receipt = make_receipt()
            with self.assertRaises(PurchaseValidationError, msg=repr(bad)) as ctx:
                receipt.revert(bad, None, 'Ana', NOW)
            self.assertIn('reason', ctx.exception.errors)
            self.assertEqual(receipt.status, ReceiptStatus.CONFIRMED)

    def test_cannot_revert_twice(self):  # AC-09
        receipt = make_receipt()
        receipt.revert('Uno', None, 'Ana', NOW)
        with self.assertRaises(ReceiptAlreadyReverted):
            receipt.revert('Dos', None, 'Ana', NOW)

    def test_moved_stock_by_mode(self):  # EDGE-02
        self.assertTrue(make_receipt(inventory_mode=InventoryMode.INVENTORY).moved_stock)
        self.assertFalse(make_receipt(inventory_mode=InventoryMode.DOCUMENTAL, warehouse_id=uuid4()).moved_stock)
        self.assertTrue(make_receipt(inventory_mode=None, warehouse_id=uuid4()).moved_stock)
        self.assertFalse(make_receipt(inventory_mode=None).moved_stock)


class RevertApplicationTests(ReceiptApiTestCase):
    """Caso de uso con repositorios reales y un puerto de stock configurable."""

    def use_case(self, stock):
        from modules.purchases.infrastructure.django.purchase_repository import DjangoPurchaseRepository
        from modules.purchases.infrastructure.django.receipt_repository import DjangoReceiptRepository
        return RevertReception(DjangoPurchaseRepository(self.company.id), DjangoReceiptRepository(self.company.id),
                               stock)

    def test_unknown_receipt_or_receipt_of_another_purchase(self):  # AC-13
        from modules.purchases.infrastructure.adapters import StockEntryAdapter
        purchase = self.confirmed_purchase()
        other = self.confirmed_purchase()
        receipt = self.receive(other, [(self.item_id(other, self.bag), '1')])
        use_case = self.use_case(StockEntryAdapter(self.company.id))
        with self.assertRaises(ReceiptNotFound):
            use_case.execute(UUID(purchase['id']), uuid4(), 'x', ACTOR, NOW)
        with self.assertRaises(ReceiptNotFound):
            use_case.execute(UUID(purchase['id']), UUID(receipt['id']), 'x', ACTOR, NOW)

    def test_inventory_unavailable_for_a_receipt_that_moved_stock(self):  # AC-10
        from modules.purchases.infrastructure.adapters import StockEntryAdapter
        self.inventory_on()
        purchase = self.confirmed_purchase()
        receipt = self.receive(purchase, [(self.item_id(purchase, self.flour), '4')],
                               warehouse_id=str(self.warehouse.id))
        from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
        from modules.modularity.tests.test_enforcement import set_enabled
        set_enabled(self.company, DEFAULT_ENABLED_KEYS + ('purchases',))
        with self.assertRaises(ReceiptInventoryUnavailable):
            self.use_case(StockEntryAdapter(self.company.id)).execute(
                UUID(purchase['id']), UUID(receipt['id']), 'Error', ACTOR, NOW)
        self.assertEqual(ReceiptModel.objects.get(pk=receipt['id']).status, 'confirmed')


class ReceiptRevertApiTests(ReceiptApiTestCase):
    def revert_url(self, purchase, receipt):
        return purchase_url(purchase['id'], f'receipts/{receipt["id"]}/revert/')

    def revert(self, purchase, receipt, expected=200, **body):
        body.setdefault('reason', 'Mercadería devuelta al proveedor')
        response = self.client.post(self.revert_url(purchase, receipt), body, format='json')
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()

    def flour_receipt(self, quantity='4', purchase=None):
        purchase = purchase or self.confirmed_purchase()
        receipt = self.receive(purchase, [(self.item_id(purchase, self.flour), quantity)],
                               warehouse_id=str(self.warehouse.id))
        return purchase, receipt

    def balance(self):
        return inventory.get_balance(self.company.id, self.flour.id, self.warehouse.id)

    def test_reverting_restores_stock_pending_and_keeps_history(self):  # AC-06, AC-11, EDGE-06
        self.inventory_on()
        purchase = self.confirmed_purchase()
        first = self.receive(purchase, [(self.item_id(purchase, self.flour), '10'),
                                        (self.item_id(purchase, self.bag), '4')],
                             warehouse_id=str(self.warehouse.id))
        self.assertEqual(self.purchase_detail(purchase)['reception_status'], 'received')
        self.assertEqual(self.balance(), Decimal('10'))

        body = self.revert(purchase, first)
        self.assertEqual(body['status'], 'reverted')
        self.assertFalse(body['can_revert'])
        self.assertEqual((body['reversal']['user_name'], body['reversal']['reason']),
                         ('ana', 'Mercadería devuelta al proveedor'))
        self.assertTrue(body['reversal']['reverted_at'])
        movement = body['movements'][0]
        self.assertEqual(movement['status'], 'reversed')
        self.assertTrue(movement['reversed_by']['id'])
        self.assertEqual(self.balance(), Decimal('0'))
        detail = self.purchase_detail(purchase)
        self.assertEqual(detail['reception_status'], 'not_received')
        self.assertIn('receive', detail['allowed_actions'])
        self.assertEqual(self.movements().count(), 2)  # el original se conserva
        listing = self.client.get(purchase_url(purchase['id'], 'receipts/')).json()['results']
        self.assertEqual(listing[0]['status'], 'reverted')

    def test_reverting_one_receipt_keeps_the_others(self):  # EDGE-06
        self.inventory_on()
        purchase, first = self.flour_receipt('4')
        second = self.receive(purchase, [(self.item_id(purchase, self.flour), '6')],
                              warehouse_id=str(self.warehouse.id))
        self.revert(purchase, second)
        self.assertEqual(self.purchase_detail(purchase)['reception_status'], 'partial')
        self.assertEqual(self.balance(), Decimal('4'))
        self.assertEqual(self.client.get(purchase_url(purchase['id'], f'receipts/{first["id"]}/')).json()['status'],
                         'confirmed')

    def test_receipt_detail_offers_revert_only_when_confirmed(self):  # AC-11
        self.inventory_on()
        purchase, receipt = self.flour_receipt()
        url = purchase_url(purchase['id'], f'receipts/{receipt["id"]}/')
        body = self.client.get(url).json()
        self.assertEqual((body['can_revert'], body['reversal']), (True, None))
        self.assertEqual(body['movements'][0]['status'], 'confirmed')

    def test_reason_is_required(self):  # AC-09
        self.inventory_on()
        purchase, receipt = self.flour_receipt()
        for bad in ({'reason': ''}, {'reason': '   '}, {'reason': 'x' * 201}):
            self.assertIn('reason', self.revert(purchase, receipt, expected=400, **bad))
        response = self.client.post(self.revert_url(purchase, receipt), {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.movements(reverses_id__isnull=False).count(), 0)

    def test_second_reversal_is_409(self):  # AC-09
        self.inventory_on()
        purchase, receipt = self.flour_receipt()
        self.revert(purchase, receipt)
        body = self.revert(purchase, receipt, expected=409)
        self.assertEqual(body['code'], 'already_reverted')
        self.assertEqual(self.movements(reverses_id__isnull=False).count(), 1)

    def test_payments_are_not_touched(self):  # AC-08
        self.inventory_on()
        purchase, receipt = self.flour_receipt()
        response = self.client.post(purchase_url(purchase['id'], 'payments/'), {
            'payment_id': str(uuid4()), 'amount': '20.00', 'payment_method': 'CASH',
            'payment_date': dj_timezone.localdate().isoformat()}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        before = self.purchase_detail(purchase)
        self.revert(purchase, receipt)
        after = self.purchase_detail(purchase)
        for key in ('paid_total', 'balance', 'payment_status', 'total'):
            self.assertEqual(after[key], before[key], key)
        self.assertEqual(PaymentModel.objects.filter(purchase_id=purchase['id'], status='confirmed').count(), 1)

    def test_insufficient_stock_blocks_every_line(self):  # AC-07, INV-05
        self.inventory_on()
        purchase, receipt = self.flour_receipt('10')
        inventory.record_movement(
            self.company.id, product_id=self.flour.id, warehouse_id=self.warehouse.id, kind='out',
            quantity=Decimal('8'), user_id=None, user_name='ana')
        body = self.revert(purchase, receipt, expected=409)
        self.assertEqual(body['code'], 'insufficient_stock')
        self.assertEqual(body['warehouse']['name'], 'Central')
        self.assertEqual(len(body['lines']), 1)
        line = body['lines'][0]
        self.assertEqual((line['product']['name'], line['unit']['abbreviation'], line['requested'], line['available']),
                         ('Harina', 'kg', '10.000', '2.000'))
        self.assertEqual(ReceiptModel.objects.get(pk=receipt['id']).status, 'confirmed')
        self.assertEqual(self.movements(reverses_id__isnull=False).count(), 0)
        self.assertEqual(self.purchase_detail(purchase)['reception_status'], 'partial')
        set_negative_stock(self.company, True)
        self.revert(purchase, receipt)
        self.assertEqual(self.balance(), Decimal('-8'))

    def test_documental_receipt_reverts_without_inventory(self):  # AC-10, INV-07
        purchase = self.confirmed_purchase()
        receipt = self.receive(purchase, [(self.item_id(purchase, self.bag), '4')])
        self.assertEqual(receipt['inventory_mode'], 'documental')
        body = self.revert(purchase, receipt)
        self.assertEqual((body['status'], body['movements']), ('reverted', None))
        self.assertEqual(self.purchase_detail(purchase)['reception_status'], 'not_received')
        self.assertEqual(StockMovementModel.objects.count(), 0)

    def test_receipt_without_controlled_lines_in_inventory_mode(self):  # EDGE-01
        self.inventory_on()
        purchase = self.confirmed_purchase()
        receipt = self.receive(purchase, [(self.item_id(purchase, self.bag), '4')])
        body = self.revert(purchase, receipt)
        self.assertEqual((body['status'], body['movements']), ('reverted', []))

    def test_inventory_disabled_blocks_a_receipt_that_moved_stock(self):  # AC-10
        self.inventory_on()
        purchase, receipt = self.flour_receipt()
        from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
        from modules.modularity.tests.test_enforcement import set_enabled
        set_enabled(self.company, DEFAULT_ENABLED_KEYS + ('purchases',))
        detail = self.client.get(purchase_url(purchase['id'], f'receipts/{receipt["id"]}/')).json()
        self.assertFalse(detail['can_revert'])
        body = self.revert(purchase, receipt, expected=409)
        self.assertEqual(body['code'], 'inventory_unavailable')
        self.assertEqual(ReceiptModel.objects.get(pk=receipt['id']).status, 'confirmed')

    def test_inactive_warehouse_does_not_block_the_reversal(self):  # EDGE-03
        self.inventory_on()
        purchase, receipt = self.flour_receipt()
        from modules.inventory.infrastructure.django.models import WarehouseModel
        WarehouseModel.objects.filter(pk=self.warehouse.pk).update(active=False)
        self.revert(purchase, receipt)
        self.assertEqual(self.balance(), Decimal('0'))

    def test_failure_after_the_ledger_rolls_everything_back(self):  # consistencia entre módulos
        self.inventory_on()
        purchase, receipt = self.flour_receipt()
        with mock.patch('modules.purchases.infrastructure.django.receipt_repository.DjangoReceiptRepository.'
                        'mark_reverted', side_effect=RuntimeError('boom')):
            self.client.raise_request_exception = False
            response = self.client.post(self.revert_url(purchase, receipt), {'reason': 'Error'}, format='json')
        self.assertEqual(response.status_code, 500)
        self.assertEqual(self.movements(reverses_id__isnull=False).count(), 0)
        self.assertEqual(self.balance(), Decimal('4'))

    def test_unknown_and_foreign_receipts_are_404(self):  # AC-13
        self.inventory_on()
        purchase, receipt = self.flour_receipt()
        other = self.confirmed_purchase()
        self.assertEqual(self.client.post(purchase_url(other['id'], f'receipts/{receipt["id"]}/revert/'),
                                          {'reason': 'x'}, format='json').status_code, 404)
        self.assertEqual(self.client.post(purchase_url(purchase['id'], f'receipts/{uuid4()}/revert/'),
                                          {'reason': 'x'}, format='json').status_code, 404)
        self.assertEqual(self.client.post(purchase_url(uuid4(), f'receipts/{receipt["id"]}/revert/'),
                                          {'reason': 'x'}, format='json').status_code, 404)

    def test_other_company_cannot_revert(self):  # AC-13
        from modules.accounts.testing import authenticate, make_admin, make_company
        from modules.purchases.tests.test_purchase_api import enable_purchases
        self.inventory_on()
        purchase, receipt = self.flour_receipt()
        intruder = make_company('Empresa B')
        enable_purchases(intruder)
        authenticate(self.client, make_admin(intruder, username='bea'))
        self.assertEqual(self.client.post(self.revert_url(purchase, receipt), {'reason': 'x'},
                                          format='json').status_code, 404)
        self.assertEqual(ReceiptModel.objects.get(pk=receipt['id']).status, 'confirmed')

    def test_purchases_module_disabled_blocks_the_endpoint(self):  # AC-14
        from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
        from modules.modularity.tests.test_enforcement import set_enabled
        self.inventory_on()
        purchase, receipt = self.flour_receipt()
        set_enabled(self.company, DEFAULT_ENABLED_KEYS + ('inventory',))
        self.assertEqual(self.client.post(self.revert_url(purchase, receipt), {'reason': 'x'},
                                          format='json').status_code, 403)

    def test_cancelling_after_reverting_everything_is_possible(self):  # AC-06
        self.inventory_on()
        purchase, receipt = self.flour_receipt()
        self.revert(purchase, receipt)
        self.assertIn('cancel', self.purchase_detail(purchase)['allowed_actions'])


@skipUnless(connection.vendor == 'postgresql', 'El bloqueo de fila requiere PostgreSQL.')
class ReceiptRevertConcurrencyTests(TransactionTestCase):
    """AC-09 con conexiones reales: el bloqueo de la compra deja un único ganador."""

    def setUp(self):
        self.company_id = uuid4()
        supplier = SupplierModel.objects.create(company_id=self.company_id, name='Sur')
        purchase = Purchase.create(supplier_id=supplier.id, purchase_date=TODAY,
                                   items=[ItemDraft(uuid4(), '10', '5.00', product_name='Harina')])
        purchase.confirm(NOW)
        self.purchase = DjangoPurchaseRepository(self.company_id).save(purchase)
        receipts = DjangoReceiptRepository(self.company_id)
        with transaction.atomic():
            receipt = RegisterReception(DjangoPurchaseRepository(self.company_id), receipts, FakeProducts(),
                                        FakeStock(enabled=False)).execute(
                self.purchase.id, uuid4(), TODAY, [ReceiptLineInput(self.purchase.items[0].id, '4')], None, ACTOR,
                TODAY)[0]
        self.receipt_id = receipt.id

    def test_two_simultaneous_reversals_have_a_single_winner(self):
        barrier = threading.Barrier(2)
        results = []

        def run():
            try:
                barrier.wait()
                with transaction.atomic():
                    RevertReception(DjangoPurchaseRepository(self.company_id),
                                    DjangoReceiptRepository(self.company_id), FakeStock(enabled=False)).execute(
                        self.purchase.id, self.receipt_id, 'Error', ACTOR, NOW)
                results.append('ok')
            except Exception as exc:  # noqa: BLE001 - se informa al test
                results.append(exc)
            finally:
                close_old_connections()

        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(10)
        self.assertEqual(results.count('ok'), 1, results)
        self.assertEqual(sum(isinstance(r, ReceiptAlreadyReverted) for r in results), 1, results)
        self.assertEqual(ReceiptModel.objects.get(pk=self.receipt_id).status, 'reverted')


@skipUnless(connection.vendor == 'postgresql', 'El bloqueo de fila requiere PostgreSQL.')
class InventoryReceiptRevertConcurrencyTests(TransactionTestCase):
    """AC-09 / INV-05 con el libro real: compra → almacén, un único ganador y un único juego de contramovimientos."""

    def setUp(self):
        from modules.accounts.testing import make_company
        from modules.inventory.infrastructure.django.models import WarehouseModel
        from modules.inventory.tests.test_movements import make_product
        from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
        from modules.modularity.tests.test_enforcement import set_enabled
        from modules.purchases.infrastructure.adapters import ProductCatalogAdapter, StockEntryAdapter
        company = make_company('Empresa Q')
        self.company_id = company.id
        set_enabled(company, DEFAULT_ENABLED_KEYS + ('purchases', 'inventory'))
        product = make_product(company)
        self.warehouse = WarehouseModel.objects.create(company_id=company.id, name='Central', is_default=True)
        supplier = SupplierModel.objects.create(company_id=company.id, name='Sur')
        purchase = Purchase.create(supplier_id=supplier.id, purchase_date=TODAY,
                                   items=[ItemDraft(product.id, '10', '5.00', product_name='Arroz')])
        purchase.confirm(NOW)
        self.purchase = DjangoPurchaseRepository(company.id).save(purchase)
        self.adapter = StockEntryAdapter
        with transaction.atomic():
            receipt = RegisterReception(
                DjangoPurchaseRepository(company.id), DjangoReceiptRepository(company.id),
                ProductCatalogAdapter(company.id), StockEntryAdapter(company.id)).execute(
                self.purchase.id, uuid4(), TODAY, [ReceiptLineInput(self.purchase.items[0].id, '4')],
                self.warehouse.id, ACTOR, TODAY)[0]
        self.receipt_id = receipt.id

    def test_two_simultaneous_reversals_with_the_real_ledger_have_a_single_winner(self):
        barrier = threading.Barrier(2)
        results = []

        def run():
            try:
                barrier.wait()
                with transaction.atomic():
                    RevertReception(DjangoPurchaseRepository(self.company_id),
                                    DjangoReceiptRepository(self.company_id),
                                    self.adapter(self.company_id)).execute(
                        self.purchase.id, self.receipt_id, 'Error', ACTOR, NOW)
                results.append('ok')
            except Exception as exc:  # noqa: BLE001 - se informa al test
                results.append(exc)
            finally:
                close_old_connections()

        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(15)
        self.assertEqual(results.count('ok'), 1, results)
        self.assertEqual(sum(isinstance(r, ReceiptAlreadyReverted) for r in results), 1, results)
        self.assertEqual(StockMovementModel.objects.filter(reverses_id__isnull=False).count(), 1)
        self.assertEqual(StockMovementModel.objects.filter(status='reversed').count(), 1)
        balance = inventory.get_balance(self.company_id, self.purchase.items[0].product_id, self.warehouse.id)
        self.assertEqual(balance, Decimal('0'))


class RevertAuthorizationTests(ReceiptApiTestCase):
    """AC-13: un usuario sin empresa (p. ej. `createsuperuser`) no accede a los endpoints de reversión."""

    def test_user_without_company_gets_403(self):
        from django.contrib.auth import get_user_model
        from modules.accounts.testing import PASSWORD, authenticate
        self.inventory_on()
        purchase = self.confirmed_purchase()
        receipt = self.receive(purchase, [(self.item_id(purchase, self.bag), '1')])
        outsider = get_user_model().objects.create_user(username='sinempresa', password=PASSWORD)
        authenticate(self.client, outsider)
        for url in (purchase_url(purchase['id'], f'receipts/{receipt["id"]}/revert/'),
                    f'/api/stock-movements/{uuid4()}/reverse/'):
            self.assertEqual(self.client.post(url, {'reason': 'x'}, format='json').status_code, 403, url)

    def test_anonymous_gets_401(self):
        self.client.credentials()
        self.assertEqual(self.client.post(f'/api/stock-movements/{uuid4()}/reverse/', {'reason': 'x'},
                                          format='json').status_code, 401)
