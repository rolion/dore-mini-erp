"""VEN-01: Ventas contabiliza por partida doble el reconocimiento (al confirmar) y cada cobro, sin duplicar ingresos.

Cada prueba usa Contabilidad real (cuentas por rol, métodos de pago, período abierto, `journal_balances`).
"""
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from django.db import transaction
from django.test import TransactionTestCase
from django.utils import timezone

from modules.accounting import services as accounting
from modules.accounting.infrastructure.django.models import EntryModel, JournalEntryModel
from modules.accounting.infrastructure.django.repositories import DjangoAccountRepository
from modules.accounting.tests.journal_support import make_account, make_period, money_account
from modules.accounting.tests.test_concurrency import _run_together
from modules.accounts.testing import make_admin, make_company
from modules.sales.application.commands import RegisterPayment, StartOrderPreparation
from modules.sales.application.ports import Actor
from modules.sales.domain.order import Order
from modules.sales.infrastructure.adapters import SalesPostingAdapter, SystemClock
from modules.sales.infrastructure.django.models import PaymentModel
from modules.sales.infrastructure.django.repositories import DjangoOrderRepository
from modules.sales.tests.test_api import SalesApiTestCase
from modules.sales.tests.test_payment_ledger import configure, enable

TODAY = timezone.localdate()


def setup_company_accounting(company, with_roles=True):
    """Contabilidad habilitada con cuentas, período abierto, métodos CASH/QR y (opcional) roles de Ventas."""
    enable(company, 'accounting', 'sales', 'customers')
    accounts = DjangoAccountRepository(company.id)
    caja = money_account(accounts, 'Caja', '110101', 'CASH')
    banco = money_account(accounts, 'Banco', '110102')
    cxc = make_account(company.id, 'Cuentas por cobrar', 'ASSET', '112001')
    ingresos = make_account(company.id, 'Ingresos por ventas', 'INCOME', '410001')
    make_period(company.id, 'Año', TODAY - timedelta(days=200), TODAY + timedelta(days=100))
    configure(company, 'CASH', caja)
    configure(company, 'QR', banco)
    if with_roles:
        accounting.set_role_account(company.id, 'RECEIVABLE', cxc.id)
        accounting.set_role_account(company.id, 'SALES_INCOME', ingresos.id)
    return caja, banco, cxc, ingresos


class PostingApiBase(SalesApiTestCase):
    def setUp(self):
        super().setUp()
        self.caja, self.banco, self.cxc, self.ingresos = setup_company_accounting(self.company)

    def journal(self, kind=None):
        rows = JournalEntryModel.objects.filter(company_id=self.company.id)
        return rows.filter(origin_kind=kind) if kind else rows

    def net(self, account):
        """(debe, haber) acumulados de la cuenta en el libro de asientos."""
        balance = accounting.journal_balances(self.company.id, [account.id]).get(account.id)
        return (balance.debit, balance.credit) if balance else (Decimal('0'), Decimal('0'))

    def order_of(self, price, quantity=1):
        return self.order_with_item(price=price, quantity=quantity)

    def confirmed(self, price, quantity=1):
        order = self.order_of(price, quantity)
        self.act(order, 'prepare')
        return order


class RecognitionAndPaymentTests(PostingApiBase):
    def test_credit_sale_of_1000_with_a_payment_of_300(self):  # AC-01
        order = self.confirmed('500.00', 2)
        self.pay(order, '300.00')
        self.assertEqual(self.net(self.ingresos), (Decimal('0'), Decimal('1000.00')))
        self.assertEqual(self.net(self.cxc), (Decimal('1000.00'), Decimal('300.00')))  # saldo por cobrar 700
        self.assertEqual(self.net(self.caja), (Decimal('300.00'), Decimal('0')))
        self.assertEqual((self.journal('SALE_RECOGNITION').count(), self.journal('SALE_PAYMENT').count()), (1, 1))

    def test_cash_sale_of_500_leaves_income_of_500_and_no_receivable(self):  # AC-02
        order = self.confirmed('250.00', 2)
        self.pay(order, '500.00')
        self.assertEqual(self.net(self.ingresos), (Decimal('0'), Decimal('500.00')))
        self.assertEqual(self.net(self.cxc), (Decimal('500.00'), Decimal('500.00')))
        self.assertEqual(self.net(self.caja), (Decimal('500.00'), Decimal('0')))

    def test_partial_and_mixed_payments_post_one_entry_each_with_their_method_account(self):  # AC-04
        order = self.confirmed('300.00')
        self.pay(order, '100.00', 'CASH')
        self.pay(order, '200.00', 'QR')
        self.assertEqual(self.net(self.caja), (Decimal('100.00'), Decimal('0')))
        self.assertEqual(self.net(self.banco), (Decimal('200.00'), Decimal('0')))
        payments = set(PaymentModel.objects.values_list('id', flat=True))
        self.assertEqual(set(self.journal('SALE_PAYMENT').values_list('origin_id', flat=True)), payments)
        recognition = self.journal('SALE_RECOGNITION').get()
        self.assertEqual(str(recognition.origin_id), order['id'])

    def test_the_recognition_uses_the_total_after_discount(self):  # AC-01
        order = self.order_of('100.00', 3)
        self.act(order, 'discount', {'discount': '20.00'})
        self.act(order, 'prepare')
        self.assertEqual(self.net(self.ingresos), (Decimal('0'), Decimal('280.00')))

    def test_a_posted_payment_creates_no_entry_in_the_previous_ledger(self):  # AC-10
        order = self.confirmed('100.00')
        self.pay(order, '100.00')
        self.assertEqual(EntryModel.objects.filter(company_id=self.company.id).count(), 0)

    def test_replaying_a_payment_or_the_confirmation_does_not_duplicate_entries(self):  # AC-03
        order = self.confirmed('300.00')
        key = str(uuid4())
        self.pay(order, '100.00', idempotency_key=key)
        self.pay(order, '100.00', expected_status=200, idempotency_key=key)
        self.conflict(self.client.post(f'/api/orders/{order["id"]}/prepare/', {}, format='json'), 'invalid_transition')
        self.assertEqual((self.journal('SALE_RECOGNITION').count(), self.journal('SALE_PAYMENT').count(),
                          PaymentModel.objects.count()), (1, 1, 1))

    def test_a_payment_cannot_exceed_the_pending_balance(self):  # INV-04
        order = self.confirmed('100.00')
        self.pay(order, '60.00')
        self.pay(order, '60.00', expected_status=400)
        self.assertEqual(self.journal('SALE_PAYMENT').count(), 1)

    def test_delivering_creates_no_entries(self):  # AC-12
        order = self.confirmed('100.00')
        self.act(order, 'ready')
        self.act(order, 'deliver')
        self.assertEqual(self.journal().count(), 1)


class MissingConfigurationTests(SalesApiTestCase):
    def test_confirming_without_configuration_is_a_conflict_with_issues_and_changes_nothing(self):  # AC-05
        setup_company_accounting(self.company, with_roles=False)
        order = self.order_with_item(price='100.00', quantity=1)
        body = self.act(order, 'prepare', expected_status=409)
        self.assertEqual(body['code'], 'posting_configuration_missing')
        self.assertEqual({i['code'] for i in body['issues']}, {'role_unconfigured'})
        self.assertIn('Ventas › Configuración › Asientos automáticos', body['detail'])
        self.assertEqual(self.get(order)['status'], 'NEW')
        self.assertEqual(JournalEntryModel.objects.count(), 0)

    def test_paying_with_a_method_without_account_is_a_conflict_and_persists_nothing(self):  # AC-05, EDGE-06
        setup_company_accounting(self.company)
        order = self.order_with_item(price='100.00', quantity=1)
        self.act(order, 'prepare')
        body = self.pay(order, '10.00', 'OTHER', expected_status=409)
        self.assertEqual(body['code'], 'posting_configuration_missing')
        self.assertEqual(body['issues'][0]['code'], 'method_unconfigured')
        self.assertEqual((PaymentModel.objects.count(), JournalEntryModel.objects.count()), (0, 1))

    def test_a_disabled_receivable_account_blocks_the_payment_with_its_name(self):  # AC-05, EDGE-04
        _, _, cxc, _ = setup_company_accounting(self.company)
        order = self.order_with_item(price='100.00', quantity=1)
        self.act(order, 'prepare')
        from modules.accounting.infrastructure.django.models import AccountModel
        AccountModel.objects.filter(pk=cxc.id).update(is_active=False)
        body = self.pay(order, '10.00', expected_status=409)
        self.assertEqual(body['code'], 'posting_configuration_missing')
        self.assertIn('Cuentas por cobrar', body['detail'])
        self.assertEqual(PaymentModel.objects.count(), 0)


class StateRulesTests(PostingApiBase):
    def test_paying_an_unconfirmed_order_is_rejected(self):  # AC-06
        order = self.order_of('100.00')
        body = self.pay(order, '10.00', expected_status=409)
        self.assertEqual(body['code'], 'order_not_confirmed')
        self.assertEqual((PaymentModel.objects.count(), self.journal().count()), (0, 0))

    def test_a_recognized_order_cannot_change_its_total(self):  # AC-07
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

    def test_cancelling_without_payments_reverses_the_recognition(self):  # AC-08
        order = self.confirmed('100.00')
        self.act(order, 'cancel', {'reason': 'Ya no lo quiere'})
        self.assertEqual(self.get(order)['status'], 'CANCELLED')
        self.assertEqual(self.journal().count(), 2)
        reversal = self.journal().exclude(reverses=None).get()
        self.assertEqual(reversal.reverses.origin_kind, 'SALE_RECOGNITION')
        self.assertEqual(self.net(self.ingresos), (Decimal('100.00'), Decimal('100.00')))

    def test_cancelling_with_posted_payments_is_rejected(self):  # AC-08
        order = self.confirmed('100.00')
        self.pay(order, '10.00')
        body = self.act(order, 'cancel', {'reason': 'Ya no lo quiere'}, expected_status=409)
        self.assertEqual(body['code'], 'order_has_payments_posted')
        self.assertEqual(self.get(order)['status'], 'IN_PREPARATION')
        self.assertEqual(self.journal().count(), 2)

    def test_cancelling_an_unconfirmed_order_works_as_before(self):  # AC-08
        order = self.order_of('100.00')
        self.act(order, 'cancel', {'reason': 'Ya no lo quiere'})
        self.assertEqual(self.journal().count(), 0)

    def test_the_reversal_uses_the_original_accounts_even_if_the_configuration_changed(self):  # AC-08, INV-05
        order = self.confirmed('100.00')
        otra = make_account(self.company.id, 'Otros ingresos', 'INCOME', '410002')
        accounting.set_role_account(self.company.id, 'SALES_INCOME', otra.id)
        self.act(order, 'cancel', {'reason': 'Error'})
        self.assertEqual(self.net(self.ingresos), (Decimal('100.00'), Decimal('100.00')))
        self.assertEqual(self.net(otra), (Decimal('0'), Decimal('0')))

    def test_a_payment_dated_before_the_coverage_is_rejected(self):  # AC-09
        order = self.confirmed('100.00')
        yesterday = str(TODAY - timedelta(days=1))
        body = self.pay(order, '10.00', payment_date=yesterday, expected_status=409)
        self.assertEqual(body['code'], 'payment_date_not_covered')
        self.assertEqual((PaymentModel.objects.count(), self.journal().count()), (0, 1))

    def test_a_closed_period_blocks_the_confirmation_and_changes_nothing(self):  # AC-09, INV-06
        from modules.accounting.infrastructure.django.models import FiscalPeriodModel
        FiscalPeriodModel.objects.filter(company_id=self.company.id).update(status='CLOSED')
        order = self.order_of('100.00')
        body = self.act(order, 'prepare', expected_status=409)
        self.assertEqual(body['code'], 'fiscal_period_unavailable')
        self.assertEqual(self.get(order)['status'], 'NEW')


class WithoutCoverageTests(SalesApiTestCase):
    def test_with_accounting_disabled_nothing_changes(self):  # AC-11
        enable(self.company, 'sales', 'customers')
        order = self.order_with_item(price='100.00', quantity=1)
        self.pay(order, '10.00')  # incluso sin confirmar, como antes
        self.act(order, 'prepare')
        self.pay(order, '10.00')
        self.act(order, 'ready')
        self.act(order, 'cancel', {'reason': 'x'}, expected_status=200)
        self.assertEqual((JournalEntryModel.objects.count(), EntryModel.objects.count()), (0, 0))

    def test_an_order_confirmed_before_the_coverage_is_paid_in_the_previous_ledger_only(self):  # AC-10, EDGE-02
        enable(self.company, 'sales', 'customers')
        order = self.order_with_item(price='100.00', quantity=1)
        self.act(order, 'prepare')  # sin Contabilidad: no hay reconocimiento
        caja, *_ = setup_company_accounting(self.company)
        self.pay(order, '40.00')
        self.assertEqual(JournalEntryModel.objects.count(), 0)
        rows = EntryModel.objects.filter(company_id=self.company.id)
        self.assertEqual([(r.origin_kind, r.account_id, r.amount) for r in rows],
                         [('PRODUCT', caja.id, Decimal('40.00'))])

    def test_confirming_with_coverage_an_order_paid_before_it_is_rejected(self):  # REV-01 (PLAN v2), AC-15
        enable(self.company, 'sales', 'customers')
        order = self.order_with_item(price='100.00', quantity=1)
        self.pay(order, '40.00')  # sin cobertura: no queda en ningún libro de partida doble
        setup_company_accounting(self.company)
        body = self.act(order, 'prepare', expected_status=409)
        self.assertEqual(body['code'], 'order_has_prior_payments')
        self.assertEqual(self.get(order)['status'], 'NEW')
        self.assertEqual(JournalEntryModel.objects.count(), 0)
        self.act(order, 'cancel', {'reason': 'Se recrea'})  # la salida indicada funciona

    def test_another_company_without_configuration_does_not_affect_this_one(self):  # AC-13
        setup_company_accounting(self.company)
        other = make_company('Empresa B')
        setup_company_accounting(other, with_roles=False)
        order = self.order_with_item(price='100.00', quantity=1)
        self.act(order, 'prepare')
        self.assertEqual(JournalEntryModel.objects.filter(company_id=self.company.id).count(), 1)
        self.assertEqual(JournalEntryModel.objects.filter(company_id=other.id).count(), 0)


class PostingConcurrencyTests(TransactionTestCase):
    """AC-03: envíos simultáneos con BD real."""

    def setUp(self):
        self.company = make_company('Concurrente')
        setup_company_accounting(self.company)
        self.user = make_admin(self.company, 'ana')
        repository = DjangoOrderRepository(self.company.id)
        order = Order.create('WHATSAPP', date.today())
        order.add_item(uuid4(), 'Pack', Decimal('150.00'), 2)
        self.order = repository.save(order)
        with transaction.atomic():
            StartOrderPreparation(repository, SystemClock(), SalesPostingAdapter(self.company.id)).execute(
                self.order.id, Actor(self.user.pk, 'ana'))

    def pay(self, amount, key):
        use_case = RegisterPayment(DjangoOrderRepository(self.company.id), SystemClock(),
                                   SalesPostingAdapter(self.company.id))
        return lambda: use_case.execute(self.order.id, amount, 'CASH', None, '', key, Actor(self.user.pk, 'ana'))

    def payments(self):
        return JournalEntryModel.objects.filter(company_id=self.company.id, origin_kind='SALE_PAYMENT')

    def test_double_submit_with_the_same_key_posts_one_payment(self):
        key = uuid4()
        self.assertEqual(_run_together(self.pay('100.00', key), self.pay('100.00', key)), [None, None])
        self.assertEqual((PaymentModel.objects.count(), self.payments().count()), (1, 1))

    def test_distinct_payments_never_exceed_the_balance(self):
        outcomes = _run_together(self.pay('200.00', uuid4()), self.pay('200.00', uuid4()))
        self.assertEqual(sum(o is None for o in outcomes), 1)
        self.assertEqual((PaymentModel.objects.count(), self.payments().count()), (1, 1))
        self.assertEqual(JournalEntryModel.objects.filter(company_id=self.company.id,
                                                          origin_kind='SALE_RECOGNITION').count(), 1)
