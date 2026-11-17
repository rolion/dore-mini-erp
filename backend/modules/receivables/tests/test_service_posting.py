"""SRV-01 (PLAN v1): servicios prestados y cobros odontológicos por partida doble, con Contabilidad real.

Líneas de la proforma de prueba: Limpieza 100, Corona 200, Blanqueamiento 50 (se aceptan las tres).
"""
import threading
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.db import connection
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from modules.accounting import services as accounting
from modules.accounting.domain.posting import events_for, get_event
from modules.accounting.infrastructure.django.models import (
    EntryModel, FiscalPeriodModel, JournalEntryModel, SettingsModel,
)
from modules.accounting.infrastructure.django.repositories import DjangoAccountRepository
from modules.accounting.tests.journal_support import make_account, make_period, money_account
from modules.accounts.testing import make_admin
from modules.modularity.infrastructure.django.repositories import DjangoCompanyModuleRepository
from modules.receivables.infrastructure.django.models import PaymentModel, RenderedServiceModel
from modules.receivables.tests.test_api import BASE, QUOTES, ReceivablesApiTests as _Base
from modules.receivables.tests.test_payment_ledger import configure

TODAY = timezone.localdate()
ZERO = Decimal('0')


class Books:
    """Cuentas y configuración contable de la empresa de prueba."""

    def __init__(self, company_id, roles=True, advances=True):
        DjangoCompanyModuleRepository(company_id).enable('accounting')
        accounts = DjangoAccountRepository(company_id)
        self.company_id = company_id
        self.caja = money_account(accounts, 'Caja', '110101', 'CASH')
        self.banco = money_account(accounts, 'Banco', '110102')
        self.cxc = make_account(company_id, 'Cuentas por cobrar', 'ASSET', '112001')
        self.ingresos = make_account(company_id, 'Ingresos por servicios', 'INCOME', '420001')
        self.anticipos = make_account(company_id, 'Anticipos de clientes', 'LIABILITY', '210001')
        make_period(company_id, 'Año', TODAY - timedelta(days=200), TODAY + timedelta(days=100))
        configure(company_id, 'CASH', self.caja)
        configure(company_id, 'QR', self.banco)
        if roles:
            accounting.set_role_account(company_id, 'RECEIVABLE', self.cxc.id)
            accounting.set_role_account(company_id, 'SERVICE_INCOME', self.ingresos.id)
        if advances:
            accounting.set_role_account(company_id, 'CUSTOMER_ADVANCES', self.anticipos.id)

    def journal(self, kind=None):
        rows = JournalEntryModel.objects.filter(company_id=self.company_id)
        return rows.filter(origin_kind=kind) if kind else rows

    def net(self, account):
        balance = accounting.journal_balances(self.company_id, [account.id]).get(account.id)
        return (balance.debit, balance.credit) if balance else (ZERO, ZERO)

    def lines(self, kind, origin_id):
        entry = self.journal(kind).get(origin_id=origin_id)
        return sorted((line.account_id, line.debit, line.credit) for line in entry.lines.all())


def D(value):
    return Decimal(value)


class ServicePostingTests(TransactionTestCase):
    quote = _Base.quote
    decide = _Base.decide
    detail = _Base.detail
    pay = _Base.pay

    def setUp(self):
        _Base.setUp(self)
        self.books = Books(self.admin.company_id)

    def accepted(self):
        return self.quote(accept=(0, 1, 2), reject=())

    def render(self, number, line, client=None, kind='quotation', **extra):
        return (client or self.client).post(f'{BASE}commitments/{kind}/{number}/services/',
                                            {'line_id': line, **extra}, format='json')

    # AC-01
    def test_catalog_has_the_service_events_and_roles(self):
        self.assertEqual([e.code for e in events_for('receivables')],
                         ['SERVICE_ADVANCE', 'SERVICE_RECOGNITION', 'SERVICE_PAYMENT'])
        self.assertEqual(get_event('SERVICE_RECOGNITION').role_codes,
                         ('RECEIVABLE', 'CUSTOMER_ADVANCES', 'SERVICE_INCOME'))
        self.assertEqual(get_event('SERVICE_ADVANCE').role_codes, ('MONEY', 'CUSTOMER_ADVANCES'))

    # AC-03
    def test_an_accepted_proforma_without_service_or_payment_posts_nothing(self):
        p = self.accepted()
        self.assertEqual(self.detail(p['number']).status_code, 200)
        self.assertEqual(self.books.journal().count(), 0)

    # AC-02 (tarjeta: servicio prestado, cobro en efectivo y por banco)
    def test_rendered_service_paid_in_cash_and_bank_recognizes_income_once(self):
        b = self.books
        p = self.accepted()
        corona = p['lines'][1]['id']  # 200
        rendered = self.render(p['number'], corona)
        self.assertEqual(rendered.status_code, 201, rendered.content)
        service_id = rendered.json()['service']['id']
        self.assertEqual(self.pay(p['number'], [(corona, '80.00')]).status_code, 201)
        last = self.pay(p['number'], [(corona, '120.00')], payment_method='QR')
        self.assertEqual(last.status_code, 201, last.content)
        self.assertEqual(b.net(b.ingresos), (ZERO, D('200.00')))
        self.assertEqual(b.net(b.cxc), (D('200.00'), D('200.00')))  # saldo por cobrar 0
        self.assertEqual((b.net(b.caja), b.net(b.banco)), ((D('80.00'), ZERO), (D('120.00'), ZERO)))
        self.assertEqual(b.net(b.anticipos), (ZERO, ZERO))
        self.assertEqual(b.lines('SERVICE_RECOGNITION', service_id),
                         sorted([(b.cxc.id, D('200.00'), ZERO), (b.ingresos.id, ZERO, D('200.00'))]))
        self.assertEqual(b.journal('SERVICE_PAYMENT').count(), 2)
        self.assertEqual(last.json()['totals']['recognized'], '200.00')

    # AC-05 (tarjeta: un anticipo no aumenta los ingresos antes de prestar)
    def test_advance_does_not_raise_income_until_the_service_is_rendered(self):
        b = self.books
        p = self.accepted()
        corona = p['lines'][1]['id']
        paid = self.pay(p['number'], [(corona, '80.00')])
        self.assertEqual(paid.status_code, 201, paid.content)
        self.assertEqual((b.net(b.ingresos), b.net(b.anticipos), b.net(b.caja)),
                         ((ZERO, ZERO), (ZERO, D('80.00')), (D('80.00'), ZERO)))
        rendered = self.render(p['number'], corona)
        service_id = rendered.json()['service']['id']
        self.assertEqual(b.lines('SERVICE_RECOGNITION', service_id), sorted([
            (b.anticipos.id, D('80.00'), ZERO), (b.cxc.id, D('120.00'), ZERO), (b.ingresos.id, ZERO, D('200.00'))]))
        self.assertEqual((b.net(b.ingresos), b.net(b.anticipos)), ((ZERO, D('200.00')), (D('80.00'), D('80.00'))))
        rest = self.pay(p['number'], [(corona, '120.00')])
        self.assertEqual(rest.status_code, 201, rest.content)
        self.assertEqual(b.net(b.cxc), (D('120.00'), D('120.00')))

    # AC-06
    def test_a_full_advance_leaves_no_receivable_line(self):
        b = self.books
        p = self.accepted()
        corona = p['lines'][1]['id']
        self.pay(p['number'], [(corona, '200.00')])
        service_id = self.render(p['number'], corona).json()['service']['id']
        self.assertEqual(b.lines('SERVICE_RECOGNITION', service_id),
                         sorted([(b.anticipos.id, D('200.00'), ZERO), (b.ingresos.id, ZERO, D('200.00'))]))
        self.assertEqual(b.net(b.cxc), (ZERO, ZERO))

    # AC-07
    def test_a_payment_across_rendered_and_unrendered_lines_posts_one_entry_per_path(self):
        b = self.books
        p = self.accepted()
        limpieza, corona = p['lines'][0]['id'], p['lines'][1]['id']
        self.render(p['number'], limpieza)  # 100 prestado, sin cobros
        paid = self.pay(p['number'], [(limpieza, '60.00'), (corona, '40.00')])
        self.assertEqual(paid.status_code, 201, paid.content)
        payment_id = paid.json()['payment']['id']
        self.assertEqual(b.lines('SERVICE_PAYMENT', payment_id),
                         sorted([(b.caja.id, D('60.00'), ZERO), (b.cxc.id, ZERO, D('60.00'))]))
        self.assertEqual(b.lines('SERVICE_ADVANCE', payment_id),
                         sorted([(b.caja.id, D('40.00'), ZERO), (b.anticipos.id, ZERO, D('40.00'))]))
        self.assertEqual(b.net(b.ingresos), (ZERO, D('100.00')))  # solo reconoce la prestación
        key = uuid4()
        before = b.journal().count()
        first = self.pay(p['number'], [(corona, '10.00')], key=key)
        self.assertEqual(self.pay(p['number'], [(corona, '10.00')], key=key).json()['replayed'], True)
        self.assertEqual((first.status_code, b.journal().count()), (201, before + 1))

    # AC-04
    def test_retry_does_not_duplicate_the_entry_and_a_posting_failure_rolls_the_payment_back(self):
        b = self.books
        p = self.accepted()
        line, key = p['lines'][1]['id'], uuid4()
        self.assertEqual(self.pay(p['number'], [(line, '50.00')], key=key).status_code, 201)
        self.assertEqual(self.pay(p['number'], [(line, '50.00')], key=key).status_code, 200)
        self.assertEqual((PaymentModel.objects.count(), b.journal('SERVICE_ADVANCE').count()), (1, 1))
        self.assertEqual(self.pay(p['number'], [(line, '51.00')], key=key).status_code, 409)
        accounting.set_role_account(b.company_id, 'CUSTOMER_ADVANCES', None)  # rompe la configuración
        failed = self.pay(p['number'], [(line, '20.00')])
        self.assertEqual((failed.status_code, failed.json()['code']), (409, 'posting_configuration_missing'))
        self.assertTrue(failed.json()['issues'])
        self.assertEqual((PaymentModel.objects.count(), b.journal().count()), (1, 1))

    # AC-08
    def test_marking_twice_is_idempotent_and_concurrent_requests_create_one_service(self):
        b = self.books
        p = self.accepted()
        corona = p['lines'][1]['id']
        first = self.render(p['number'], corona)
        again = self.render(p['number'], corona)
        self.assertEqual((first.status_code, again.status_code, again.json()['replayed']), (201, 200, True))
        self.assertEqual(first.json()['service']['id'], again.json()['service']['id'])
        self.assertEqual((RenderedServiceModel.objects.count(), b.journal('SERVICE_RECOGNITION').count()), (1, 1))

        limpieza = p['lines'][0]['id']
        results = []

        def worker():
            client = APIClient()
            client.force_authenticate(self.admin)
            try:
                results.append(self.render(p['number'], limpieza, client=client).status_code)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(sorted(results), [200, 201])
        self.assertEqual((RenderedServiceModel.objects.count(), b.journal('SERVICE_RECOGNITION').count()), (2, 2))

    # AC-08 (cobrar y prestar a la vez)
    def test_payment_and_service_in_parallel_leave_consistent_books(self):
        b = self.books
        p = self.accepted()
        corona = p['lines'][1]['id']
        outcomes = []

        def pay():
            client = APIClient()
            client.force_authenticate(self.admin)
            try:
                outcomes.append(self.pay(p['number'], [(corona, '70.00')], client=client).status_code)
            finally:
                connection.close()

        def render():
            client = APIClient()
            client.force_authenticate(self.admin)
            try:
                outcomes.append(self.render(p['number'], corona, client=client).status_code)
            finally:
                connection.close()

        threads = [threading.Thread(target=fn) for fn in (pay, render)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(sorted(outcomes), [201, 201])
        # Sea cual sea el orden: ingreso 200; el pago de 70 está en anticipo (y aplicado) o contra Cuentas por cobrar.
        self.assertEqual(b.net(b.ingresos), (ZERO, D('200.00')))
        receivable = b.net(b.cxc)
        self.assertEqual(receivable[0] - receivable[1], D('130.00'))

    # AC-09
    def test_missing_configuration_rejects_the_service_without_leaving_anything(self):
        accounting.set_role_account(self.books.company_id, 'SERVICE_INCOME', None)
        p = self.accepted()
        response = self.render(p['number'], p['lines'][1]['id'])
        self.assertEqual((response.status_code, response.json()['code']), (409, 'posting_configuration_missing'))
        self.assertEqual((RenderedServiceModel.objects.count(), self.books.journal().count()), (0, 0))
        self.assertFalse(self.detail(p['number']).json()['lines'][1]['rendered'])

    def test_a_closed_fiscal_period_rejects_a_service_dated_inside_it(self):
        p = self.accepted()
        FiscalPeriodModel.objects.filter(company_id=self.books.company_id).update(status='CLOSED')
        response = self.render(p['number'], p['lines'][1]['id'])
        self.assertEqual((response.status_code, response.json()['code']), (409, 'fiscal_period_unavailable'))
        self.assertEqual(RenderedServiceModel.objects.count(), 0)

    def test_a_payment_before_the_cutoff_cannot_be_applied_to_a_rendered_line(self):
        b = self.books
        p = self.accepted()
        corona = p['lines'][1]['id']
        SettingsModel.objects.update_or_create(
            company_id=b.company_id, defaults={'cutoff_date': TODAY + timedelta(days=30)})
        self.assertEqual(self.pay(p['number'], [(corona, '50.00')]).status_code, 201)  # libro anterior
        SettingsModel.objects.filter(company_id=b.company_id).update(cutoff_date=TODAY - timedelta(days=30))
        blocked = self.render(p['number'], corona)
        self.assertEqual((blocked.status_code, blocked.json()['code']), (409, 'service_has_unposted_payments'))
        self.assertEqual((RenderedServiceModel.objects.count(), b.journal().count()), (0, 0))

    # AC-10
    def test_without_accounting_everything_works_and_nothing_is_posted(self):
        DjangoCompanyModuleRepository(self.books.company_id).disable('accounting')
        p = self.accepted()
        corona = p['lines'][1]['id']
        self.assertEqual(self.pay(p['number'], [(corona, '50.00')]).status_code, 201)
        self.assertEqual(self.render(p['number'], corona).status_code, 201)
        self.assertEqual(self.pay(p['number'], [(corona, '150.00')]).status_code, 201)
        self.assertEqual(self.books.journal().count(), 0)
        self.assertEqual(self.detail(p['number']).json()['payment_status'], 'partial')

    def test_a_service_rendered_before_the_cutoff_creates_no_entry_and_later_payments_use_the_old_ledger(self):
        b = self.books
        p = self.accepted()
        corona = p['lines'][1]['id']
        SettingsModel.objects.update_or_create(
            company_id=b.company_id, defaults={'cutoff_date': TODAY + timedelta(days=30)})
        self.assertEqual(self.render(p['number'], corona).status_code, 201)
        self.assertEqual(self.pay(p['number'], [(corona, '50.00')]).status_code, 201)
        self.assertEqual((b.journal().count(), EntryModel.objects.filter(company_id=b.company_id).count()), (0, 1))

    # AC-11
    def test_a_rendered_line_cannot_be_rejected_and_only_accepted_lines_can_be_rendered(self):
        p = self.quote(accept=(0, 1), reject=(2,))
        corona, rejected = p['lines'][1]['id'], p['lines'][2]['id']
        self.assertEqual(self.render(p['number'], corona).status_code, 201)
        blocked = self.client.post(f"{QUOTES}{p['id']}/lines/{corona}/rectify/", {
            'idempotency_key': str(uuid4()), 'decision': 'rejected', 'reason': 'x'}, format='json')
        self.assertEqual(blocked.status_code, 409, blocked.content)
        self.assertEqual(self.render(p['number'], rejected).status_code, 400)
        self.assertEqual(self.render(p['number'], str(uuid4())).status_code, 400)
        future = self.render(p['number'], p['lines'][0]['id'], service_date=str(TODAY + timedelta(days=1)))
        self.assertEqual(future.status_code, 400)

    # AC-12
    def test_other_companies_cannot_see_or_mark_a_service(self):
        p = self.accepted()
        stranger = APIClient()
        stranger.force_authenticate(self.other)
        modules = DjangoCompanyModuleRepository(self.other.company_id)
        modules.enabled_keys()
        for key in ('catalog', 'services', 'quotations', 'receivables'):
            modules.enable(key)
        self.assertEqual(self.render(p['number'], p['lines'][1]['id'], client=stranger).status_code, 404)
        self.assertEqual(RenderedServiceModel.objects.count(), 0)

    def test_detail_reports_rendered_lines_and_allowed_actions(self):
        p = self.accepted()
        corona = p['lines'][1]['id']
        before = self.detail(p['number']).json()
        self.assertIn('render_service', before['allowed_actions'])
        self.render(p['number'], corona, service_date=str(TODAY - timedelta(days=1)))
        view = self.detail(p['number']).json()
        line = next(l for l in view['lines'] if l['line_id'] == corona)
        self.assertEqual((line['rendered'], line['service_date'], line['can_render']),
                         (True, str(TODAY - timedelta(days=1)), False))
        self.assertEqual(view['totals']['recognized'], '200.00')
