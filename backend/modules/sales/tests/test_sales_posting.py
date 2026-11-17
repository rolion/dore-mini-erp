"""VEN-01 (PLAN v3): Ventas reconoce el ingreso al entregar y registra como anticipos los cobros previos a la entrega.

Cada prueba usa Contabilidad real (cuentas por rol, métodos de pago, período abierto, `journal_balances`).
"""
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from django.db import transaction
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from modules.accounting import services as accounting
from modules.accounting.infrastructure.django.models import (
    AccountModel,
    EntryModel,
    FiscalPeriodModel,
    JournalEntryModel,
)
from modules.accounting.infrastructure.django.repositories import DjangoAccountRepository
from modules.accounting.tests.journal_support import make_account, make_period, money_account
from modules.accounting.tests.test_concurrency import _run_together
from modules.accounts.testing import authenticate, make_admin, make_company
from modules.catalog.infrastructure.django.models import ProductModel
from modules.modularity.infrastructure.django.models import CompanyModuleModel
from modules.sales.application.commands import DeliverOrder, MarkOrderReady, RegisterPayment, StartOrderPreparation
from modules.sales.application.ports import Actor
from modules.sales.domain.order import Order
from modules.sales.infrastructure.adapters import SalesPostingAdapter, SystemClock
from modules.sales.infrastructure.django.models import PaymentModel
from modules.sales.infrastructure.django.repositories import DjangoOrderRepository
from modules.sales.tests.test_api import SalesApiTestCase
from modules.sales.tests.test_payment_ledger import configure, enable

TODAY = timezone.localdate()
YESTERDAY = TODAY - timedelta(days=1)
ZERO = Decimal('0')


class Books:
    """Cuentas y configuración contable de una empresa de prueba."""

    def __init__(self, company, roles=True, advances=True):
        enable(company, 'accounting', 'sales', 'customers')
        accounts = DjangoAccountRepository(company.id)
        self.company = company
        self.caja = money_account(accounts, 'Caja', '110101', 'CASH')
        self.banco = money_account(accounts, 'Banco', '110102')
        self.cxc = make_account(company.id, 'Cuentas por cobrar', 'ASSET', '112001')
        self.ingresos = make_account(company.id, 'Ingresos por ventas', 'INCOME', '410001')
        self.anticipos = make_account(company.id, 'Anticipos de clientes', 'LIABILITY', '210001')
        make_period(company.id, 'Año', TODAY - timedelta(days=200), TODAY + timedelta(days=100))
        configure(company, 'CASH', self.caja)
        configure(company, 'QR', self.banco)
        if roles:
            accounting.set_role_account(company.id, 'RECEIVABLE', self.cxc.id)
            accounting.set_role_account(company.id, 'SALES_INCOME', self.ingresos.id)
        if advances:
            accounting.set_role_account(company.id, 'CUSTOMER_ADVANCES', self.anticipos.id)

    def journal(self, kind=None):
        rows = JournalEntryModel.objects.filter(company_id=self.company.id)
        return rows.filter(origin_kind=kind) if kind else rows

    def net(self, account):
        """(debe, haber) acumulados de la cuenta en el libro de asientos."""
        balance = accounting.journal_balances(self.company.id, [account.id]).get(account.id)
        return (balance.debit, balance.credit) if balance else (ZERO, ZERO)

    def lines(self, kind, origin_id):
        entry = self.journal(kind).get(origin_id=origin_id)
        return sorted((line.account_id, line.debit, line.credit) for line in entry.lines.all())


class PostingApiBase(SalesApiTestCase):
    def setUp(self):
        super().setUp()
        self.books = Books(self.company)

    def confirmed(self, price, quantity=1, **extra):
        order = self.order_with_item(price=price, quantity=quantity, **extra)
        self.act(order, 'prepare')
        return order

    def ready(self, price, quantity=1, **extra):
        order = self.confirmed(price, quantity, **extra)
        self.act(order, 'ready')
        return order

    def deliver(self, order, expected_status=200, **body):
        return self.act(order, 'deliver', body, expected_status)

    def payment_ids(self):
        return list(PaymentModel.objects.order_by('created_at').values_list('id', flat=True))


class StatesWithoutEntriesTests(SalesApiTestCase):
    def test_creating_editing_confirming_and_marking_ready_post_nothing_and_need_no_configuration(self):  # AC-02, AC-03
        books = Books(self.company, roles=False, advances=False)  # Contabilidad habilitada y sin cuentas por rol
        order = self.order_with_item(price='100.00', quantity=2)
        self.client.patch(f'/api/orders/{order["id"]}/', {'notes': 'Sin cebolla'}, format='json')
        self.act(order, 'discount', {'discount': '10.00'})
        self.act(order, 'prepare')
        self.act(order, 'ready')
        self.assertEqual((books.journal().count(), self.get(order)['status']), (0, 'READY'))

    def test_paying_an_unconfirmed_order_is_still_rejected_with_coverage(self):  # AC-02
        books = Books(self.company)
        order = self.order_with_item(price='100.00', quantity=1)
        body = self.pay(order, '10.00', expected_status=409)
        self.assertEqual(body['code'], 'order_not_confirmed')
        self.assertEqual((PaymentModel.objects.count(), books.journal().count()), (0, 0))

    def test_no_payment_is_required_to_deliver(self):  # AC-05
        books = Books(self.company)
        order = self.order_with_item(price='100.00', quantity=1)
        self.act(order, 'prepare')
        self.act(order, 'ready')
        self.act(order, 'deliver')
        self.assertEqual(self.get(order)['status'], 'DELIVERED')
        self.assertEqual(books.journal('SALE_DELIVERY').count(), 1)


class AdvanceTests(PostingApiBase):
    def test_a_payment_in_preparation_is_an_advance_money_against_advances(self):  # AC-04
        order = self.confirmed('500.00', 2)
        self.pay(order, '300.00', 'CASH')
        payment = self.payment_ids()[0]
        self.assertEqual(self.books.lines('SALE_ADVANCE', payment),
                         sorted([(self.books.caja.id, Decimal('300.00'), ZERO),
                                 (self.books.anticipos.id, ZERO, Decimal('300.00'))]))
        self.assertEqual((self.books.journal().count(), self.books.net(self.books.cxc)), (1, (ZERO, ZERO)))

    def test_a_payment_in_ready_is_the_same_kind_of_entry(self):  # AC-04
        order = self.ready('500.00', 2)
        self.pay(order, '300.00')
        self.assertEqual(self.books.journal('SALE_ADVANCE').count(), 1)

    def test_partial_and_mixed_payments_post_one_entry_each_with_their_method_account(self):  # AC-04
        order = self.confirmed('300.00')
        self.pay(order, '100.00', 'CASH')
        self.pay(order, '200.00', 'QR')
        self.assertEqual(self.books.net(self.books.caja), (Decimal('100.00'), ZERO))
        self.assertEqual(self.books.net(self.books.banco), (Decimal('200.00'), ZERO))
        self.assertEqual(self.books.net(self.books.anticipos), (ZERO, Decimal('300.00')))
        origins = set(self.books.journal('SALE_ADVANCE').values_list('origin_id', flat=True))
        self.assertEqual(origins, set(self.payment_ids()))

    def test_a_posted_advance_creates_no_entry_in_the_previous_ledger(self):  # INV-02
        self.pay(self.confirmed('100.00'), '100.00')
        self.assertEqual(EntryModel.objects.filter(company_id=self.company.id).count(), 0)

    def test_the_commercial_balance_still_limits_the_payment(self):  # INV-04
        order = self.confirmed('100.00')
        self.pay(order, '60.00')
        self.pay(order, '60.00', expected_status=400)
        self.assertEqual(self.books.journal('SALE_ADVANCE').count(), 1)

    def test_replaying_a_payment_does_not_duplicate_its_entry(self):  # AC-08
        order = self.confirmed('300.00')
        key = str(uuid4())
        self.pay(order, '100.00', idempotency_key=key)
        self.pay(order, '100.00', expected_status=200, idempotency_key=key)
        self.assertEqual((PaymentModel.objects.count(), self.books.journal('SALE_ADVANCE').count()), (1, 1))

    def test_without_the_advances_account_the_payment_is_rejected_and_nothing_is_saved(self):  # AC-04, AC-14
        company = make_company('Sin anticipos')
        Books(company, advances=False)
        client = APIClient()
        authenticate(client, make_admin(company, username='sin_anticipos'))
        product = ProductModel.objects.create(company_id=company.id, name='Pack', description='',
                                              sale_price=Decimal('100.00'), active=True, can_sell=True)
        order = client.post('/api/orders/', {'sales_channel': 'WHATSAPP'}, format='json').json()['id']
        client.post(f'/api/orders/{order}/items/', {'product_id': str(product.id), 'quantity': 1}, format='json')
        client.post(f'/api/orders/{order}/prepare/', {}, format='json')
        response = client.post(f'/api/orders/{order}/payments/', {'amount': '10.00', 'payment_method': 'CASH'},
                               format='json')
        self.assertEqual((response.status_code, response.json()['code']), (409, 'posting_configuration_missing'))
        self.assertEqual(response.json()['issues'][0]['role'], 'CUSTOMER_ADVANCES')
        self.assertEqual(PaymentModel.objects.filter(order_id=order).count(), 0)

    def test_a_method_without_account_is_rejected_with_its_issue(self):  # EDGE-06
        order = self.confirmed('100.00')
        body = self.pay(order, '10.00', 'OTHER', expected_status=409)
        self.assertEqual((body['code'], body['issues'][0]['code']), ('posting_configuration_missing',
                                                                      'method_unconfigured'))
        self.assertEqual(PaymentModel.objects.count(), 0)

    def test_a_payment_dated_before_the_coverage_is_rejected(self):  # EDGE-02
        order = self.confirmed('100.00')
        body = self.pay(order, '10.00', payment_date=str(YESTERDAY), expected_status=409)
        self.assertEqual(body['code'], 'payment_date_not_covered')
        self.assertEqual((PaymentModel.objects.count(), self.books.journal().count()), (0, 0))


class DeliveryTests(PostingApiBase):
    def test_case_a_delivery_without_previous_payments(self):  # AC-05
        order = self.ready('500.00', 2)
        self.deliver(order)
        self.assertEqual(self.books.lines('SALE_DELIVERY', UUID(order['id'])),
                         sorted([(self.books.cxc.id, Decimal('1000.00'), ZERO),
                                 (self.books.ingresos.id, ZERO, Decimal('1000.00'))]))

    def test_case_b_delivery_with_an_advance_of_300(self):  # AC-06
        order = self.ready('500.00', 2)
        self.pay(order, '300.00')
        self.deliver(order)
        self.assertEqual(self.books.lines('SALE_DELIVERY', UUID(order['id'])),
                         sorted([(self.books.anticipos.id, Decimal('300.00'), ZERO),
                                 (self.books.cxc.id, Decimal('700.00'), ZERO),
                                 (self.books.ingresos.id, ZERO, Decimal('1000.00'))]))
        self.assertEqual(self.books.net(self.books.anticipos), (Decimal('300.00'), Decimal('300.00')))  # aplicado

    def test_case_c_fully_prepaid_has_no_receivable_line(self):  # AC-07, INV-07
        order = self.ready('500.00', 2)
        self.pay(order, '400.00', 'CASH')
        self.pay(order, '600.00', 'QR')
        self.deliver(order)
        lines = self.books.lines('SALE_DELIVERY', UUID(order['id']))
        self.assertEqual(lines, sorted([(self.books.anticipos.id, Decimal('1000.00'), ZERO),
                                        (self.books.ingresos.id, ZERO, Decimal('1000.00'))]))
        self.assertEqual(self.books.net(self.books.cxc), (ZERO, ZERO))

    def test_delivering_does_not_move_cash_or_banks(self):  # AC-08
        order = self.ready('500.00', 2)
        self.pay(order, '300.00', 'CASH')
        before = (self.books.net(self.books.caja), self.books.net(self.books.banco))
        self.deliver(order)
        self.assertEqual((self.books.net(self.books.caja), self.books.net(self.books.banco)), before)

    def test_the_delivery_uses_the_total_after_discount(self):  # AC-06
        order = self.order_with_item(price='100.00', quantity=3)
        self.act(order, 'discount', {'discount': '20.00'})
        self.act(order, 'prepare')
        self.act(order, 'ready')
        self.pay(order, '80.00')
        self.deliver(order)
        self.assertEqual(self.books.net(self.books.ingresos), (ZERO, Decimal('280.00')))
        self.assertEqual(self.books.net(self.books.cxc), (Decimal('200.00'), ZERO))

    def test_delivering_twice_recognizes_the_income_once(self):  # AC-08
        order = self.ready('100.00')
        self.deliver(order)
        self.conflict(self.client.post(f'/api/orders/{order["id"]}/deliver/', {}, format='json'), 'invalid_transition')
        self.assertEqual(self.books.journal('SALE_DELIVERY').count(), 1)

    def test_a_payment_after_the_delivery_is_money_against_receivable_only(self):  # AC-09
        order = self.ready('500.00', 2)
        self.pay(order, '300.00', 'CASH')
        self.deliver(order)
        ingresos, anticipos = self.books.net(self.books.ingresos), self.books.net(self.books.anticipos)
        self.pay(order, '700.00', 'QR')
        later = self.payment_ids()[-1]
        self.assertEqual(self.books.lines('SALE_PAYMENT', later),
                         sorted([(self.books.banco.id, Decimal('700.00'), ZERO),
                                 (self.books.cxc.id, ZERO, Decimal('700.00'))]))
        self.assertEqual((self.books.net(self.books.ingresos), self.books.net(self.books.anticipos)),
                         (ingresos, anticipos))
        self.assertEqual(self.books.net(self.books.cxc), (Decimal('700.00'), Decimal('700.00')))

    def test_the_25_bs_sale_paid_when_delivering(self):  # AC-09
        order = self.ready('25.00')
        self.deliver(order)
        self.pay(order, '25.00', 'CASH')
        self.assertEqual(self.books.net(self.books.caja), (Decimal('25.00'), ZERO))
        self.assertEqual(self.books.net(self.books.ingresos), (ZERO, Decimal('25.00')))
        self.assertEqual(self.books.net(self.books.cxc), (Decimal('25.00'), Decimal('25.00')))

    def test_delivering_without_paying_leaves_the_receivable_pending(self):  # AC-09
        self.deliver(self.ready('25.00'))
        self.assertEqual(self.books.net(self.books.cxc), (Decimal('25.00'), ZERO))

    def test_incomplete_configuration_blocks_the_delivery_and_changes_nothing(self):  # AC-14
        order = self.ready('100.00')
        accounting.set_role_account(self.company.id, 'SALES_INCOME', None)
        body = self.deliver(order, expected_status=409)
        self.assertEqual((body['code'], body['issues'][0]['role']), ('posting_configuration_missing', 'SALES_INCOME'))
        self.assertEqual((self.get(order)['status'], self.books.journal().count()), ('READY', 0))

    def test_a_disabled_account_blocks_the_delivery_with_its_name(self):  # EDGE-04
        order = self.ready('100.00')
        AccountModel.objects.filter(pk=self.books.cxc.id).update(is_active=False)
        body = self.deliver(order, expected_status=409)
        self.assertEqual(body['code'], 'posting_configuration_missing')
        self.assertIn('Cuentas por cobrar', body['detail'])
        self.assertEqual(self.get(order)['status'], 'READY')

    def test_a_closed_period_blocks_the_delivery_and_changes_nothing(self):  # EDGE-03, AC-14
        order = self.ready('100.00')
        FiscalPeriodModel.objects.filter(company_id=self.company.id).update(status='CLOSED')
        body = self.deliver(order, expected_status=409)
        self.assertEqual(body['code'], 'fiscal_period_unavailable')
        self.assertEqual(self.get(order)['status'], 'READY')


class CancelAndLockTests(PostingApiBase):
    def test_cancelling_before_delivery_without_payments_posts_nothing(self):  # AC-11
        order = self.confirmed('100.00')
        self.act(order, 'cancel', {'reason': 'Ya no lo quiere'})
        self.assertEqual((self.get(order)['status'], self.books.journal().count()), ('CANCELLED', 0))

    def test_cancelling_with_posted_payments_is_rejected(self):  # AC-11
        order = self.confirmed('100.00')
        self.pay(order, '10.00')
        body = self.act(order, 'cancel', {'reason': 'Ya no lo quiere'}, expected_status=409)
        self.assertEqual(body['code'], 'order_has_payments_posted')
        self.assertEqual((self.get(order)['status'], self.books.journal().count()), ('IN_PREPARATION', 1))

    def test_a_delivered_order_cannot_be_cancelled_as_before(self):  # AC-11
        order = self.ready('100.00')
        self.deliver(order)
        body = self.act(order, 'cancel', {'reason': 'Error'}, expected_status=409)
        self.assertEqual(body['code'], 'invalid_transition')

    def test_a_confirmed_order_keeps_its_total_with_coverage(self):  # AC-12
        order = self.confirmed('100.00', 2)
        item_id = self.get(order)['items'][0]['id']
        responses = [
            self.client.post(f'/api/orders/{order["id"]}/items/', {'product_id': str(self.product().id), 'quantity': 1},
                             format='json'),
            self.client.patch(f'/api/orders/{order["id"]}/items/{item_id}/', {'quantity': 3}, format='json'),
            self.client.delete(f'/api/orders/{order["id"]}/items/{item_id}/'),
            self.client.post(f'/api/orders/{order["id"]}/discount/', {'discount': '5.00'}, format='json'),
        ]
        for response in responses:
            self.conflict(response, 'order_total_locked')
        edited = self.client.patch(f'/api/orders/{order["id"]}/', {'notes': 'Sin cebolla'}, format='json')
        self.assertEqual(edited.status_code, 200, edited.content)
        self.assertEqual(self.get(order)['total'], '200.00')

    def test_a_new_order_can_still_change_its_total(self):  # AC-12
        order = self.order_with_item(price='100.00', quantity=2)
        self.add_item(order, self.product(name='Otro'), 1)
        self.act(order, 'discount', {'discount': '5.00'})


class TransitionTests(PostingApiBase):
    def seed_old_recognition(self, order):
        """Reconocimiento al confirmar de la lógica anterior (pedidos históricos)."""
        with transaction.atomic():
            accounting.post_automatic_entry(self.company.id, 'SALE_RECOGNITION', UUID(order['id']), TODAY,
                                            'Venta histórica', Decimal(self.get(order)['total']))

    def test_an_order_recognized_at_confirm_is_not_recognized_again_and_its_payments_hit_receivable(self):  # AC-10
        order = self.ready('500.00', 2)
        self.seed_old_recognition(order)
        self.pay(order, '300.00', 'CASH')
        self.assertEqual(self.books.journal('SALE_PAYMENT').count(), 1)
        self.assertEqual(self.books.journal('SALE_ADVANCE').count(), 0)
        self.deliver(order)
        self.assertEqual(self.books.journal('SALE_DELIVERY').count(), 0)
        self.assertEqual(self.books.net(self.books.ingresos), (ZERO, Decimal('1000.00')))  # una sola vez

    def test_cancelling_an_order_recognized_at_confirm_reverses_its_original_recognition(self):  # AC-10
        order = self.confirmed('100.00')
        self.seed_old_recognition(order)
        self.act(order, 'cancel', {'reason': 'Error'})
        self.assertEqual(self.books.journal().count(), 2)
        self.assertEqual(self.books.net(self.books.ingresos), (Decimal('100.00'), Decimal('100.00')))

    def test_cancelling_an_order_recognized_at_confirm_with_payments_is_rejected(self):  # AC-10, AC-11
        order = self.confirmed('100.00')
        self.seed_old_recognition(order)
        self.pay(order, '10.00')
        body = self.act(order, 'cancel', {'reason': 'Error'}, expected_status=409)
        self.assertEqual(body['code'], 'order_has_payments_posted')

    def test_a_payment_without_entry_blocks_the_delivery_with_coverage(self):  # AC-13
        # Contabilidad deshabilitada: el cobro no deja asiento; luego se habilita y se entrega con cobertura.
        CompanyModuleModel.objects.filter(company_id=self.company.id, module_key='accounting').delete()
        order = self.ready('100.00')
        self.pay(order, '40.00')
        enable(self.company, 'accounting')
        body = self.deliver(order, expected_status=409)
        self.assertEqual(body['code'], 'order_has_unposted_payments')
        self.assertEqual((self.get(order)['status'], self.books.journal().count()), ('READY', 0))

    def test_a_delivery_without_coverage_and_with_advances_is_rejected(self):  # AC-13
        order = self.ready('100.00', order_date=str(YESTERDAY))
        self.pay(order, '40.00')  # anticipo con cobertura de hoy (el corte queda en hoy)
        body = self.deliver(order, expected_status=409, delivered_date=str(YESTERDAY))
        self.assertEqual(body['code'], 'delivery_date_not_covered')
        self.assertEqual(self.get(order)['status'], 'READY')

    def test_a_delivery_without_coverage_and_without_advances_posts_nothing(self):  # AC-13
        order = self.ready('100.00', order_date=str(YESTERDAY))
        accounting.coverage_status(self.company.id, TODAY)  # fija el corte de hoy
        self.deliver(order, delivered_date=str(YESTERDAY))
        self.assertEqual((self.get(order)['status'], self.books.journal().count()), ('DELIVERED', 0))

    def test_an_order_delivered_before_the_coverage_is_paid_in_the_previous_ledger_only(self):  # AC-13, EDGE-07
        CompanyModuleModel.objects.filter(company_id=self.company.id, module_key='accounting').delete()
        order = self.ready('100.00')
        self.deliver(order)
        enable(self.company, 'accounting')
        self.pay(order, '40.00')
        self.assertEqual(self.books.journal().count(), 0)
        rows = EntryModel.objects.filter(company_id=self.company.id)
        self.assertEqual([(r.origin_kind, r.account_id, r.amount) for r in rows],
                         [('PRODUCT', self.books.caja.id, Decimal('40.00'))])


class WithoutCoverageTests(SalesApiTestCase):
    def test_with_accounting_disabled_nothing_changes(self):  # AC-15
        enable(self.company, 'sales', 'customers')
        order = self.order_with_item(price='100.00', quantity=1)
        self.pay(order, '10.00')  # incluso sin confirmar, como antes
        self.act(order, 'prepare')
        self.pay(order, '10.00')
        self.act(order, 'ready')
        self.act(order, 'deliver')
        self.pay(order, '10.00')
        self.assertEqual((JournalEntryModel.objects.count(), EntryModel.objects.count()), (0, 0))

    def test_two_companies_are_independent(self):  # AC-16
        books_a = Books(self.company)
        other = make_company('Empresa B')
        books_b = Books(other, roles=False, advances=False)
        order = self.order_with_item(price='100.00', quantity=1)
        self.act(order, 'prepare')
        self.act(order, 'ready')
        self.act(order, 'deliver')
        self.assertEqual((books_a.journal().count(), books_b.journal().count()), (1, 0))


class PostingConcurrencyTests(TransactionTestCase):
    """AC-08: envíos simultáneos con BD real."""

    def setUp(self):
        self.company = make_company('Concurrente')
        self.books = Books(self.company)
        self.user = make_admin(self.company, 'ana')
        self.actor = Actor(self.user.pk, 'ana')
        self.repository = DjangoOrderRepository(self.company.id)
        order = Order.create('WHATSAPP', date.today())
        order.add_item(uuid4(), 'Pack', Decimal('150.00'), 2)
        self.order = self.repository.save(order)
        with transaction.atomic():
            StartOrderPreparation(self.repository).execute(self.order.id)

    def posting(self):
        return SalesPostingAdapter(self.company.id)

    def pay(self, amount, key):
        use_case = RegisterPayment(DjangoOrderRepository(self.company.id), SystemClock(), self.posting())
        return lambda: use_case.execute(self.order.id, amount, 'CASH', None, '', key, self.actor)

    def entries(self, kind):
        return self.books.journal(kind).count()

    def test_double_submit_with_the_same_key_posts_one_advance(self):
        key = uuid4()
        self.assertEqual(_run_together(self.pay('100.00', key), self.pay('100.00', key)), [None, None])
        self.assertEqual((PaymentModel.objects.count(), self.entries('SALE_ADVANCE')), (1, 1))

    def test_distinct_advances_never_exceed_the_balance(self):
        outcomes = _run_together(self.pay('200.00', uuid4()), self.pay('200.00', uuid4()))
        self.assertEqual(sum(o is None for o in outcomes), 1)
        self.assertEqual((PaymentModel.objects.count(), self.entries('SALE_ADVANCE')), (1, 1))

    def test_two_simultaneous_deliveries_recognize_the_income_once_and_apply_the_advance_once(self):
        with transaction.atomic():
            self.pay('100.00', uuid4())()
            MarkOrderReady(self.repository).execute(self.order.id)

        def deliver():
            use_case = DeliverOrder(DjangoOrderRepository(self.company.id), SystemClock(), None, self.posting())
            return use_case.execute(self.order.id, None, None, self.actor)

        outcomes = _run_together(deliver, deliver)
        self.assertEqual(sum(o is None for o in outcomes), 1)
        self.assertEqual(self.entries('SALE_DELIVERY'), 1)
        self.assertEqual(self.books.net(self.books.anticipos), (Decimal('100.00'), Decimal('100.00')))
        self.assertEqual(self.books.net(self.books.ingresos), (ZERO, Decimal('300.00')))
