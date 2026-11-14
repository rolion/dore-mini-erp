"""PB-ACC-003: pagos de pedidos con el libro de entradas e idempotencia (AC-01..AC-11 del plan)."""
from datetime import date
from decimal import Decimal
from unittest import mock
from uuid import uuid4

from django.db import transaction
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from modules.accounting import services as accounting
from modules.accounting.application.use_cases import ConfigureMethod
from modules.accounting.domain.account import Account
from modules.accounting.infrastructure.django.models import EntryModel
from modules.accounting.infrastructure.django.repositories import DjangoAccountRepository, DjangoMethodMappingRepository
from modules.accounting.tests.test_concurrency import _run_together
from modules.catalog.infrastructure.django.models import ProductModel
from modules.accounts.testing import authenticate, make_admin, make_company
from modules.inventory.infrastructure.django.models import StockMovementModel
from modules.modularity.infrastructure.django.models import CompanyModuleModel, CompanySettingsModel
from modules.sales.application.commands import AddOrderItem, CreateOrder, RegisterPayment
from modules.sales.application.ports import Actor
from modules.sales.domain.exceptions import OrderRuleViolation
from modules.sales.domain.order import Order, payment_digest
from modules.sales.infrastructure.adapters import PaymentLedgerAdapter, SystemClock
from modules.sales.infrastructure.django.models import PaymentModel
from modules.sales.infrastructure.django.repositories import DjangoOrderRepository
from modules.sales.tests.fakes import FakeCustomers, FakeProducts, FixedClock, InMemoryOrderRepository
from modules.sales.tests.test_api import SalesApiTestCase, url


def enable(company, *keys):
    CompanySettingsModel.objects.get_or_create(company_id=company.id)
    for key in keys:
        CompanyModuleModel.objects.get_or_create(company_id=company.id, module_key=key)


def configure(company, method, account, active=True):
    with transaction.atomic():
        ConfigureMethod(DjangoAccountRepository(company.id), DjangoMethodMappingRepository(company.id)).execute(
            method, account.id, active)


class LedgerFixtures:
    def setup_accounting(self):
        enable(self.company, 'accounting', 'sales', 'customers')
        accounts = DjangoAccountRepository(self.company.id)
        self.caja = accounts.save(Account.create('Caja', 'BOB'))
        self.banco = accounts.save(Account.create('Banco', 'BOB'))
        configure(self.company, 'CASH', self.caja)
        configure(self.company, 'QR', self.banco)

    def entries(self, company=None):
        return EntryModel.objects.filter(company_id=(company or self.company).id).order_by('created_at')

    def order_300(self):
        return self.order_with_item(price='150.00', quantity=2)


class PaymentLedgerApiTests(LedgerFixtures, SalesApiTestCase):
    def setUp(self):
        super().setUp()
        self.setup_accounting()

    def test_two_payments_create_two_entries_and_settle_the_order(self):  # AC-01, AC-08
        order = self.order_300()
        self.pay(order, '100.00', 'CASH', payment_date='2026-11-01')
        paid = self.pay(order, '200.00', 'QR')
        self.assertEqual((paid['balance'], paid['payment_status']), ('0.00', 'PAID'))
        rows = list(self.entries())
        self.assertEqual([(r.amount, r.account_id, r.origin_kind, r.currency) for r in rows],
                         [(Decimal('100.00'), self.caja.id, 'PRODUCT', 'BOB'),
                          (Decimal('200.00'), self.banco.id, 'PRODUCT', 'BOB')])
        self.assertEqual(str(rows[0].payment_date), '2026-11-01')
        self.assertEqual(rows[0].origin_document_ref, order['id'])
        self.assertEqual(rows[0].recorded_by_name, 'ana')
        self.assertEqual(rows[0].origin_id, PaymentModel.objects.order_by('created_at').first().id)

    def test_partial_payment_creates_only_its_amount(self):  # AC-02
        order = self.order_300()
        self.pay(order, '50.00')
        self.assertEqual([r.amount for r in self.entries()], [Decimal('50.00')])

    def test_other_actions_create_no_entries_and_cancel_keeps_payments(self):  # AC-03, AC-11
        order = self.order_300()
        self.act(order, 'prepare')
        self.assertEqual(self.entries().count(), 0)
        self.pay(order, '100.00')
        self.act(order, 'ready')
        self.act(order, 'cancel', {'reason': 'Ya no lo quiere'})
        self.assertEqual(self.entries().count(), 1)
        self.assertEqual(PaymentModel.objects.count(), 1)
        self.assertEqual(StockMovementModel.objects.count(), 0)

    def test_same_key_and_data_replays_without_new_payment_or_entry(self):  # AC-04, EDGE-01
        order = self.order_300()
        key = str(uuid4())
        first = self.pay(order, '100.00', idempotency_key=key)
        again = self.pay(order, '100.00', expected_status=200, idempotency_key=key)
        self.assertEqual(first['paid_total'], again['paid_total'])
        self.assertEqual((PaymentModel.objects.count(), self.entries().count()), (1, 1))
        self.pay(order, '200.00')
        self.pay(order, '100.00', expected_status=200, idempotency_key=key)  # ya saldado
        self.assertEqual((PaymentModel.objects.count(), self.entries().count()), (2, 2))

    def test_same_key_with_other_data_is_a_conflict(self):  # AC-04
        order = self.order_300()
        key = str(uuid4())
        self.pay(order, '100.00', idempotency_key=key)
        response = self.pay(order, '90.00', expected_status=409, idempotency_key=key)
        self.assertEqual(response['code'], 'idempotency_key_reused')
        self.assertEqual(self.entries().count(), 1)

    def test_same_key_on_another_order_is_a_new_payment(self):  # EDGE-02
        key = str(uuid4())
        self.pay(self.order_300(), '10.00', idempotency_key=key)
        self.pay(self.order_300(), '10.00', idempotency_key=key)
        self.assertEqual(self.entries().count(), 2)

    def test_malformed_key_is_rejected(self):  # EDGE-03
        self.pay(self.order_300(), '10.00', expected_status=400, idempotency_key='no-es-uuid')

    def test_method_without_account_is_rejected_without_persistence(self):  # AC-06, EDGE-05
        order = self.order_300()
        response = self.pay(order, '10.00', 'OTHER', expected_status=409)
        self.assertEqual(response['code'], 'payment_method_without_account')
        self.assertIn('Contabilidad', response['detail'])
        self.assertEqual((PaymentModel.objects.count(), self.entries().count()), (0, 0))
        self.assertEqual(self.get(order)['paid_total'], '0.00')

    def test_inactive_mapping_or_account_is_rejected(self):  # AC-06
        order = self.order_300()
        ConfigureMethod(DjangoAccountRepository(self.company.id), DjangoMethodMappingRepository(self.company.id)) \
            .execute('CASH', self.caja.id, False)
        self.pay(order, '10.00', 'CASH', expected_status=409)
        self.assertEqual(PaymentModel.objects.count(), 0)

    def test_ledger_failure_rolls_back_the_whole_payment(self):  # AC-07
        order = self.order_300()
        with mock.patch('modules.sales.infrastructure.adapters.accounting_services.record_entry',
                        side_effect=RuntimeError('boom')):
            with self.assertRaises(RuntimeError):
                self.pay(order, '10.00')
        self.assertEqual((PaymentModel.objects.count(), self.entries().count()), (0, 0))
        self.assertEqual(self.get(order)['paid_total'], '0.00')

    def test_ledger_rejection_is_a_conflict_and_persists_nothing(self):  # AC-07
        order = self.order_300()
        error = accounting.EntryValidationError({'currency': ['La moneda debe ser BOB.']})
        with mock.patch('modules.sales.infrastructure.adapters.accounting_services.record_entry', side_effect=error):
            response = self.pay(order, '10.00', expected_status=409)
        self.assertEqual(response['code'], 'ledger_rejected')
        self.assertEqual(PaymentModel.objects.count(), 0)

    def test_changing_the_mapping_keeps_previous_entries(self):  # AC-08
        order = self.order_300()
        self.pay(order, '10.00', 'CASH')
        configure(self.company, 'CASH', self.banco)
        self.pay(order, '20.00', 'CASH')
        self.assertEqual([r.account_id for r in self.entries()], [self.caja.id, self.banco.id])

    def test_accounting_disabled_keeps_the_previous_flow(self):  # AC-09
        CompanyModuleModel.objects.filter(company_id=self.company.id, module_key='accounting').delete()
        order = self.order_300()
        with mock.patch('modules.sales.infrastructure.adapters.accounting_services') as accounting_mock:
            self.pay(order, '10.00', 'OTHER')
            accounting_mock.resolve_account.assert_not_called()
        self.assertEqual((PaymentModel.objects.count(), self.entries().count()), (1, 0))

    def test_payment_without_key_still_works_with_accounting(self):  # AC-09
        self.pay(self.order_300(), '10.00')
        self.assertEqual(self.entries().count(), 1)

    def test_other_company_data_is_never_used(self):  # AC-10
        other = make_company('Empresa B')
        enable(other, 'accounting', 'sales', 'customers')
        client_b = APIClient()
        authenticate(client_b, make_admin(other, username='beto'))
        order = self.order_300()
        # Un pedido de la empresa A no existe para la empresa B.
        response = client_b.post(url(order['id'], 'payments/'), {'amount': '10.00', 'payment_method': 'CASH'},
                                 format='json')
        self.assertEqual(response.status_code, 404)
        # Empresa B no mapeó CASH: su propio cobro se rechaza aunque A sí lo tenga configurado (no usa la cuenta de A).
        product = ProductModel.objects.create(company_id=other.id, name='Pack B', description='',
                                              sale_price=Decimal('50.00'), active=True, can_sell=True)
        order_b = client_b.post('/api/orders/', {'sales_channel': 'WHATSAPP'}, format='json').json()
        client_b.post(url(order_b['id'], 'items/'), {'product_id': str(product.id), 'quantity': 1}, format='json')
        rejected = client_b.post(url(order_b['id'], 'payments/'), {'amount': '10.00', 'payment_method': 'CASH'},
                                 format='json')
        self.assertEqual((rejected.status_code, rejected.json()['code']), (409, 'payment_method_without_account'))
        # Con su propia cuenta, la entrada de B queda en B y nunca en la cuenta de A.
        configure(other, 'CASH', DjangoAccountRepository(other.id).save(Account.create('Caja B', 'BOB')))
        paid = client_b.post(url(order_b['id'], 'payments/'), {'amount': '10.00', 'payment_method': 'CASH'},
                             format='json')
        self.assertEqual(paid.status_code, 201, paid.content)
        self.assertEqual((self.entries(other).count(), self.entries().count()), (1, 0))
        self.assertNotEqual(self.entries(other).get().account_id, self.caja.id)

    def test_ledger_conflict_is_a_409_and_persists_nothing(self):  # AC-07
        order = self.order_300()
        with mock.patch('modules.sales.infrastructure.adapters.accounting_services.record_entry',
                        side_effect=accounting.EntryConflict(['amount'])):
            response = self.pay(order, '10.00', expected_status=409)
        self.assertEqual(response['code'], 'ledger_conflict')
        self.assertEqual((PaymentModel.objects.count(), self.entries().count()), (0, 0))

    def test_cancelled_order_rejects_new_key_but_replays_the_old_one(self):  # EDGE-01, EDGE-04
        order = self.order_300()
        key = str(uuid4())
        self.pay(order, '100.00', idempotency_key=key)
        self.act(order, 'cancel', {'reason': 'Ya no lo quiere'})
        self.pay(order, '100.00', expected_status=200, idempotency_key=key)
        rejected = self.pay(order, '50.00', expected_status=409, idempotency_key=str(uuid4()))
        self.assertEqual(rejected['code'], 'order_cancelled')
        self.assertEqual((PaymentModel.objects.count(), self.entries().count()), (1, 1))

    def test_adding_items_and_delivering_create_no_entries(self):  # AC-03
        order = self.order_300()
        self.add_item(order, quantity=1)
        self.act(order, 'prepare')
        self.act(order, 'ready')
        self.act(order, 'deliver')
        self.assertEqual(self.entries().count(), 0)

    def test_unauthenticated_is_rejected(self):  # AC-10
        self.client.credentials()
        response = self.client.post(url(str(uuid4()), 'payments/'), {'amount': '1.00'}, format='json')
        self.assertIn(response.status_code, (401, 403))

    def test_sales_disabled_blocks_payment(self):  # AC-10
        order = self.order_300()
        CompanyModuleModel.objects.filter(company_id=self.company.id, module_key='sales').delete()
        response = self.client.post(url(order['id'], 'payments/'), {'amount': '10.00'}, format='json')
        self.assertEqual(response.status_code, 403)


class PaymentLedgerApplicationTests(TransactionTestCase):
    """Orden y atomicidad del comando con doble en memoria del libro (AC-06, AC-07, AC-09)."""

    class FakeLedger:
        def __init__(self, available=True, error=None):
            self.available, self.error, self.calls = available, error, []

        def is_available(self):
            return self.available

        def record(self, order_id, payment, actor):
            self.calls.append((order_id, payment.amount))
            if self.error:
                raise self.error

    def setUp(self):
        self.repository = InMemoryOrderRepository()
        self.clock = FixedClock()
        products, customers = FakeProducts(), FakeCustomers()
        order = CreateOrder(self.repository, customers, self.clock).execute('WHATSAPP')
        product = products.add(price='100.00')
        self.order = AddOrderItem(self.repository, products).execute(order.id, product.id, 3)

    def test_ledger_error_leaves_nothing_saved(self):
        ledger = self.FakeLedger(error=OrderRuleViolation('payment_method_without_account', 'x'))
        saves = self.repository.saves
        with self.assertRaises(OrderRuleViolation):
            RegisterPayment(self.repository, self.clock, ledger).execute(self.order.id, '10.00', 'CASH')
        self.assertEqual((self.repository.saves, len(self.repository.get(self.order.id).payments)), (saves, 0))

    def test_unavailable_ledger_is_not_called(self):
        ledger = self.FakeLedger(available=False)
        RegisterPayment(self.repository, self.clock, ledger).execute(self.order.id, '10.00', 'CASH')
        self.assertEqual(ledger.calls, [])

    def test_replay_does_not_call_the_ledger_again(self):
        ledger, key = self.FakeLedger(), uuid4()
        command = RegisterPayment(self.repository, self.clock, ledger)
        command.execute(self.order.id, '10.00', 'CASH', None, '', key)
        self.assertFalse(command.replayed)
        command.execute(self.order.id, '10.00', 'CASH', None, '', key)
        self.assertTrue(command.replayed)
        self.assertEqual(len(ledger.calls), 1)

    def test_digest_ignores_surrounding_spaces(self):
        self.assertEqual(payment_digest('10.00', 'CASH', None, ' a '), payment_digest('10.00', 'CASH', None, 'a'))
        self.assertNotEqual(payment_digest('10.00', 'CASH', None, ''), payment_digest('11.00', 'CASH', None, ''))


class PaymentLedgerConcurrencyTests(LedgerFixtures, TransactionTestCase):
    """AC-04 y AC-05: envíos simultáneos con BD real."""

    def setUp(self):
        self.company = make_company('Concurrente')
        self.setup_accounting()
        self.user = make_admin(self.company, 'ana')
        repository = DjangoOrderRepository(self.company.id)
        order = Order.create('WHATSAPP', date.today())
        order.add_item(uuid4(), 'Pack', Decimal('150.00'), 2)
        order.start_preparation()
        self.order = repository.save(order)

    def pay(self, amount, key):
        use_case = RegisterPayment(DjangoOrderRepository(self.company.id), SystemClock(),
                                   PaymentLedgerAdapter(self.company.id))
        return lambda: use_case.execute(self.order.id, amount, 'CASH', None, '', key, Actor(self.user.pk, 'ana'))

    def test_double_submit_with_the_same_key_creates_one_payment_and_one_entry(self):  # AC-04
        key = uuid4()
        outcomes = _run_together(self.pay('100.00', key), self.pay('100.00', key))
        self.assertEqual(outcomes, [None, None])
        self.assertEqual((PaymentModel.objects.count(), self.entries().count()), (1, 1))

    def test_distinct_payments_never_exceed_the_balance(self):  # AC-05
        outcomes = _run_together(self.pay('200.00', uuid4()), self.pay('200.00', uuid4()))
        self.assertEqual(sum(o is None for o in outcomes), 1)
        self.assertEqual(sum(o is not None for o in outcomes), 1)
        self.assertEqual((PaymentModel.objects.count(), self.entries().count()), (1, 1))
        self.assertEqual(self.entries().get().amount, Decimal('200.00'))
