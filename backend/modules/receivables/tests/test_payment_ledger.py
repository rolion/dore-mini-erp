"""PB-COB-002: pagos de proformas de servicios con el libro de entradas (AC-01..AC-10 del plan)."""
import threading
from decimal import Decimal
from unittest import mock
from uuid import uuid4

from django.db import connection, transaction
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from modules.accounting import services as accounting
from modules.accounting.application.use_cases import ConfigureMethod
from modules.accounting.domain.account import Account
from modules.accounting.infrastructure.django.models import EntryModel
from modules.accounting.infrastructure.django.repositories import DjangoAccountRepository, DjangoMethodMappingRepository
from modules.modularity.infrastructure.django.repositories import DjangoCompanyModuleRepository
from modules.receivables.infrastructure.django.models import AllocationModel, PaymentModel
from modules.receivables.tests.test_api import BASE, ReceivablesApiTests as _Base


def configure(company_id, method, account, active=True):
    with transaction.atomic():
        ConfigureMethod(DjangoAccountRepository(company_id), DjangoMethodMappingRepository(company_id)).execute(
            method, account.id, active)


class ServicePaymentLedgerTests(TransactionTestCase):
    setUp = _Base.setUp
    quote = _Base.quote
    decide = _Base.decide
    detail = _Base.detail
    pay = _Base.pay

    def enable_accounting(self):
        company = self.admin.company_id
        DjangoCompanyModuleRepository(company).enable('accounting')
        accounts = DjangoAccountRepository(company)
        self.caja = accounts.save(Account.create('Caja', 'BOB'))
        self.banco = accounts.save(Account.create('Banco', 'BOB'))
        configure(company, 'CASH', self.caja)
        configure(company, 'QR', self.banco)

    def entries(self, company=None):
        return EntryModel.objects.filter(company_id=company or self.admin.company_id).order_by('created_at')

    # AC-01
    def test_advance_installment_and_final_payment_create_three_entries(self):
        self.enable_accounting()
        p = self.quote(accept=(0, 1), reject=(2,))  # 100 + 200 = 300
        self.assertEqual(self.entries().count(), 0)  # aceptar no crea entradas
        a, b = p['lines'][0]['id'], p['lines'][1]['id']
        for allocations in ([(a, '100.00')], [(b, '50.00')], [(b, '150.00')]):
            self.assertEqual(self.pay(p['number'], allocations).status_code, 201)
        self.assertEqual([e.amount for e in self.entries()], [Decimal('100.00'), Decimal('50.00'), Decimal('150.00')])
        self.assertEqual(self.detail(p['number']).json()['payment_status'], 'paid')

    # AC-02, AC-07
    def test_distributed_payment_has_one_receipt_one_entry_and_matches_the_payment(self):
        self.enable_accounting()
        p = self.quote()
        lines = [(p['lines'][0]['id'], '100.00'), (p['lines'][1]['id'], '60.00')]
        response = self.pay(p['number'], lines, payment_date='2026-11-10')
        self.assertEqual(response.status_code, 201)
        payment = PaymentModel.objects.get()
        entry = self.entries().get()
        self.assertEqual((entry.origin_kind, entry.origin_id, entry.origin_document_ref, entry.receipt_number),
                         ('SERVICE', payment.id, p['number'], payment.receipt_number))
        self.assertEqual((entry.amount, entry.currency, entry.account_id, entry.payment_method),
                         (Decimal('160.00'), 'BOB', self.caja.id, 'CASH'))
        self.assertEqual((str(entry.payment_date), entry.recorded_by), ('2026-11-10', self.admin.pk))
        self.assertEqual(AllocationModel.objects.count(), 2)
        configure(self.admin.company_id, 'CASH', self.banco)  # el mapeo nuevo solo afecta a los próximos pagos
        self.pay(p['number'], [(p['lines'][1]['id'], '10.00')])
        self.assertEqual([e.account_id for e in self.entries()], [self.caja.id, self.banco.id])

    # AC-02 (proforma dental)
    def test_dental_payment_creates_its_entry(self):
        self.enable_accounting()
        dental = '/api/dentistry/'
        body = self.client.post(f'{dental}patients/{self.customer.pk}/proformas/', {'date': '2026-11-04', 'lines': [
            {'service_id': str(self.a.pk), 'quantity': '1', 'dental_piece': '18'}]}, format='json').json()
        p = self.client.post(f"{dental}proformas/{body['id']}/present/").json()
        accept = self.client.post(f"{dental}proformas/{p['id']}/decisions/", {
            'idempotency_key': str(uuid4()), 'decision': 'accepted', 'line_ids': [p['lines'][0]['id']],
            'accepted_by_name': 'Rosa', 'medium': 'in_person'}, format='json')
        self.assertEqual(accept.status_code, 201, accept.content)
        response = self.pay(p['number'], [(p['lines'][0]['id'], '30.00')], kind='dental')
        self.assertEqual(response.status_code, 201, response.content)
        entry = self.entries().get()
        self.assertEqual((entry.origin_kind, entry.origin_document_ref, entry.amount),
                         ('SERVICE', p['number'], Decimal('30.00')))

    # AC-10
    def test_payments_appear_in_the_ledger_api_with_correct_totals(self):
        self.enable_accounting()
        p = self.quote()
        self.pay(p['number'], [(p['lines'][0]['id'], '40.00')])
        self.pay(p['number'], [(p['lines'][1]['id'], '60.00')])
        listing = self.client.get('/api/accounting/entries/').json()
        row = listing['results'][0]
        self.assertEqual((row['origin']['kind'], row['source']['document_ref']), ('SERVICE', p['number']))
        self.assertEqual({r['source']['receipt_number'] for r in listing['results']},
                         set(PaymentModel.objects.values_list('receipt_number', flat=True)))
        self.assertNotIn('reference', row)
        total = listing['totals'][0]
        self.assertEqual((total['currency'], total['count'], total['amount'], total['by_origin']['SERVICE']),
                         ('BOB', 2, '100.00', '100.00'))

    # AC-03
    def test_retry_and_double_submit_do_not_duplicate_payment_or_entry(self):
        self.enable_accounting()
        p = self.quote()
        key, line = uuid4(), p['lines'][0]['id']
        self.assertEqual(self.pay(p['number'], [(line, '40.00')], key=key).status_code, 201)
        self.assertEqual(self.pay(p['number'], [(line, '40.00')], key=key).status_code, 200)
        self.assertEqual(self.pay(p['number'], [(line, '41.00')], key=key).status_code, 409)
        self.assertEqual((PaymentModel.objects.count(), self.entries().count()), (1, 1))

    def test_concurrent_same_key_creates_one_payment_and_one_entry(self):
        self.enable_accounting()
        p = self.quote()
        key, line = uuid4(), p['lines'][0]['id']
        results = []

        def worker():
            client = APIClient()
            client.force_authenticate(self.admin)
            try:
                results.append(self.pay(p['number'], [(line, '40.00')], key=key, client=client).status_code)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(sorted(results), [200, 201])
        self.assertEqual((PaymentModel.objects.count(), self.entries().count()), (1, 1))

    # AC-04
    def test_concurrent_different_payments_respect_the_balance(self):
        self.enable_accounting()
        p = self.quote(accept=(0, 1, 2), reject=())
        line = p['lines'][1]['id']
        self.assertEqual(self.pay(p['number'], [(line, '50.00')]).status_code, 201)
        results = []

        def worker():
            client = APIClient()
            client.force_authenticate(self.admin)
            try:
                results.append(self.pay(p['number'], [(line, '100.00')], client=client).status_code)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(sorted(results), [201, 400])
        self.assertEqual((PaymentModel.objects.count(), self.entries().count()), (2, 2))

    # AC-05
    def test_method_without_account_rejects_everything_and_can_be_retried(self):
        self.enable_accounting()
        p = self.quote()
        line, key = p['lines'][0]['id'], uuid4()
        data = {'idempotency_key': str(key), 'amount': '30.00', 'payment_method': 'CARD',
                'allocations': [{'line_id': line, 'amount': '30.00'}]}
        url = f"{BASE}commitments/quotation/{p['number']}/payments/"
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'payment_method_without_account')
        self.assertEqual((PaymentModel.objects.count(), AllocationModel.objects.count(), self.entries().count()),
                         (0, 0, 0))
        self.assertEqual(self.detail(p['number']).json()['payment_status'], 'pending')
        configure(self.admin.company_id, 'CARD', self.banco)  # corregir el mapeo y reintentar con la misma clave
        self.assertEqual(self.client.post(url, data, format='json').status_code, 201)
        self.assertEqual((PaymentModel.objects.count(), self.entries().count()), (1, 1))

    # AC-06
    def test_ledger_failure_rolls_back_and_retry_creates_one_pair(self):
        self.enable_accounting()
        p = self.quote()
        line, key = p['lines'][0]['id'], uuid4()
        with mock.patch.object(accounting, 'record_entry', side_effect=accounting.EntryConflict(['amount'])):
            response = self.pay(p['number'], [(line, '30.00')], key=key)
        self.assertEqual((response.status_code, response.json()['code']), (409, 'ledger_conflict'))
        self.assertEqual((PaymentModel.objects.count(), self.entries().count()), (0, 0))
        with mock.patch.object(accounting, 'record_entry', side_effect=RuntimeError('boom')):
            with self.assertRaises(RuntimeError):
                self.pay(p['number'], [(line, '30.00')], key=key)
        self.assertEqual((PaymentModel.objects.count(), self.entries().count()), (0, 0))
        self.assertEqual(self.pay(p['number'], [(line, '30.00')], key=key).status_code, 201)
        self.assertEqual((PaymentModel.objects.count(), self.entries().count()), (1, 1))

    # AC-08
    def test_other_company_cannot_pay_or_see_entries(self):
        self.enable_accounting()
        p = self.quote()
        self.pay(p['number'], [(p['lines'][0]['id'], '30.00')])
        modules = DjangoCompanyModuleRepository(self.other.company_id)
        modules.enabled_keys()
        for key in ('catalog', 'services', 'quotations', 'dentistry', 'receivables'):
            modules.enable(key)
        other = APIClient()
        other.force_authenticate(self.other)
        self.assertEqual(self.pay(p['number'], [(p['lines'][0]['id'], '10.00')], client=other).status_code, 404)
        self.assertEqual(self.entries(self.other.company_id).count(), 0)

    # AC-09, EDGE-01
    def test_accounting_disabled_keeps_previous_behaviour_and_replay_adds_no_entry(self):
        p = self.quote()
        line, key = p['lines'][0]['id'], uuid4()
        self.assertEqual(self.pay(p['number'], [(line, '30.00')], key=key).status_code, 201)
        self.enable_accounting()  # se habilita después: el pago previo no genera entrada ni en el replay
        self.assertEqual(self.pay(p['number'], [(line, '30.00')], key=key).status_code, 200)
        self.assertEqual(self.entries().count(), 0)
        self.assertEqual(self.pay(p['number'], [(line, '10.00')]).status_code, 201)
        self.assertEqual(self.entries().count(), 1)

    # AC-05: mapeo inactivo y cuenta inactiva
    def test_inactive_mapping_or_inactive_account_is_rejected_without_persisting(self):
        self.enable_accounting()
        p = self.quote()
        line = p['lines'][0]['id']
        configure(self.admin.company_id, 'QR', self.banco, active=False)
        data = {'idempotency_key': str(uuid4()), 'amount': '30.00', 'payment_method': 'QR',
                'allocations': [{'line_id': line, 'amount': '30.00'}]}
        url = f"{BASE}commitments/quotation/{p['number']}/payments/"
        response = self.client.post(url, data, format='json')
        self.assertEqual((response.status_code, response.json()['code']), (409, 'payment_method_without_account'))
        configure(self.admin.company_id, 'QR', self.banco)
        with mock.patch.object(accounting, 'resolve_account', return_value=None):
            self.assertEqual(self.client.post(url, {**data, 'idempotency_key': str(uuid4())},
                                              format='json').status_code, 409)
        self.assertEqual((PaymentModel.objects.count(), self.entries().count()), (0, 0))

    # AC-06: la validación del libro
    def test_ledger_validation_error_returns_ledger_rejected(self):
        self.enable_accounting()
        p = self.quote()
        error = accounting.EntryValidationError({'currency': ['Moneda no válida.']})
        with mock.patch.object(accounting, 'record_entry', side_effect=error):
            response = self.pay(p['number'], [(p['lines'][0]['id'], '30.00')])
        self.assertEqual((response.status_code, response.json()['code']), (409, 'ledger_rejected'))
        self.assertEqual((PaymentModel.objects.count(), self.entries().count()), (0, 0))

    # AC-09: sin Ventas habilitado el cobro funciona y no mueve stock ni ventas
    def test_collecting_works_with_sales_disabled_and_creates_no_sales(self):
        self.enable_accounting()
        company = self.admin.company_id
        DjangoCompanyModuleRepository(company).disable('sales')
        self.assertNotIn('sales', DjangoCompanyModuleRepository(company).enabled_keys())
        p = self.quote()
        self.assertEqual(self.pay(p['number'], [(p['lines'][0]['id'], '30.00')]).status_code, 201)
        self.assertEqual(self.entries().get().origin_kind, 'SERVICE')

    # EDGE-02: lo cobrado no se pierde al intentar rechazar la línea
    def test_rejecting_a_paid_line_is_blocked_and_keeps_payment_and_entry(self):
        self.enable_accounting()
        p = self.quote()
        line = p['lines'][0]['id']
        self.pay(p['number'], [(line, '30.00')])
        blocked = self.client.post(f"/api/quotations/proformas/{p['id']}/lines/{line}/rectify/", {
            'idempotency_key': str(uuid4()), 'decision': 'rejected', 'reason': 'x'}, format='json')
        self.assertEqual(blocked.status_code, 409, blocked.content)
        self.assertEqual((PaymentModel.objects.count(), self.entries().count()), (1, 1))
