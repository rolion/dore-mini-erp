import threading
from datetime import datetime, timezone as dt_timezone
from unittest import mock
from decimal import Decimal
from uuid import uuid4

from django.db import connection
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APIClient

from modules.accounts.testing import make_admin
from modules.customers.infrastructure.django.models import CustomerModel
from modules.dentistry.infrastructure.models import PatientModel
from modules.modularity.infrastructure.django.repositories import DjangoCompanyModuleRepository
from modules.receivables.infrastructure.django.models import AllocationModel, ObligationModel, PaymentModel
from modules.service_catalog.infrastructure.django.models import ServiceModel

QUOTES = '/api/quotations/proformas/'
DENTAL = '/api/dentistry/'
BASE = '/api/receivables/'


class ReceivablesApiTests(TransactionTestCase):
    def setUp(self):
        self.admin = make_admin(username='rec-admin')
        self.other = make_admin(username='rec-other')
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        modules = DjangoCompanyModuleRepository(self.admin.company_id)
        modules.enabled_keys()
        for key in ('catalog', 'services', 'quotations', 'dentistry', 'receivables'):
            modules.enable(key)
        company = self.admin.company_id
        self.customer = CustomerModel.objects.create(company_id=company, name='Rosa Pérez')
        PatientModel.objects.create(company_id=company, customer_id=self.customer.pk, created_by=self.admin.pk,
                                    updated_by=self.admin.pk)
        self.a = ServiceModel.objects.create(company_id=company, name='Limpieza', base_price=Decimal('100.00'),
                                             duration_minutes=30)
        self.b = ServiceModel.objects.create(company_id=company, name='Corona', base_price=Decimal('200.00'),
                                             duration_minutes=60)
        self.c = ServiceModel.objects.create(company_id=company, name='Blanqueamiento', base_price=Decimal('50.00'),
                                             duration_minutes=60)

    # --- helpers -----------------------------------------------------------------------------------------------
    def quote(self, accept=(0, 1), reject=(2,)):
        body = self.client.post(QUOTES, {'customer_id': str(self.customer.pk), 'date': '2026-11-03', 'lines': [
            {'service_id': str(s.pk), 'quantity': '1'} for s in (self.a, self.b, self.c)]}, format='json').json()
        p = self.client.post(f"{QUOTES}{body['id']}/present/").json()
        self.decide(QUOTES, p, accept, 'accepted')
        if reject:
            self.decide(QUOTES, p, reject, 'rejected')
        return self.client.get(f"{QUOTES}{p['id']}/").json()

    def decide(self, root, p, indexes, decision):
        data = {'idempotency_key': str(uuid4()), 'decision': decision,
                'line_ids': [p['lines'][i]['id'] for i in indexes]}
        if decision == 'accepted':
            data.update({'accepted_by_name': 'Rosa Pérez', 'medium': 'in_person'})
        response = self.client.post(f"{root}{p['id']}/decisions/", data, format='json')
        self.assertEqual(response.status_code, 201, response.content)

    def detail(self, number, kind='quotation'):
        return self.client.get(f'{BASE}commitments/{kind}/{number}/')

    def pay(self, number, allocations, amount=None, kind='quotation', key=None, client=None, **extra):
        amount = amount if amount is not None else sum(Decimal(v) for _, v in allocations)
        data = {'idempotency_key': str(key or uuid4()), 'amount': str(amount), 'payment_method': 'CASH',
                'allocations': [{'line_id': line, 'amount': str(v)} for line, v in allocations], **extra}
        return (client or self.client).post(f'{BASE}commitments/{kind}/{number}/payments/', data, format='json')

    # AC-01, AC-08
    def test_advance_and_installment_leave_the_balance(self):
        p = self.quote(accept=(1,), reject=(2,))  # solo Corona (200) aceptado; Limpieza pendiente; Blanq. rechazado
        view = self.detail(p['number']).json()
        self.assertEqual(view['totals'], {'proposed': '350.00', 'accepted': '200.00', 'pending': '100.00',
                                          'rejected': '50.00', 'paid': '0.00', 'balance': '200.00'})
        line = p['lines'][1]['id']
        first = self.pay(p['number'], [(line, '120.00')])
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(first.json()['totals']['balance'], '80.00')
        self.assertEqual(first.json()['payment']['receipt_number'], 'CB-000001')
        second = self.pay(p['number'], [(line, '30.00')])
        body = second.json()
        self.assertEqual((body['totals']['paid'], body['totals']['balance'], body['payment_status']),
                         ('150.00', '50.00', 'partial'))
        self.assertEqual(len(body['payments']), 2)
        self.assertEqual(ObligationModel.objects.count(), 1)
        self.assertEqual(self.detail(p['number']).json()['proforma_id'], p['id'])  # AC-10 / API-01

    # AC-02
    def test_double_submit_does_not_duplicate_income(self):
        p = self.quote()
        key, line = uuid4(), p['lines'][0]['id']
        self.assertEqual(self.pay(p['number'], [(line, '40.00')], key=key).status_code, 201)
        retry = self.pay(p['number'], [(line, '40.00')], key=key)
        self.assertEqual((retry.status_code, retry.json()['replayed']), (200, True))
        self.assertEqual(PaymentModel.objects.count(), 1)
        self.assertEqual(self.pay(p['number'], [(line, '41.00')], key=key).status_code, 409)

    # AC-03
    def test_concurrent_payments_never_exceed_the_balance(self):
        p = self.quote(accept=(0, 1, 2), reject=())
        line = p['lines'][1]['id']  # 200
        self.assertEqual(self.pay(p['number'], [(line, '50.00')]).status_code, 201)  # saldo 150
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
        paid = sum(a.amount for a in AllocationModel.objects.all())
        self.assertEqual(paid, Decimal('150.00'))

    # AC-04
    def test_rejected_and_pending_lines_are_not_collectible(self):
        p = self.quote(accept=(0,), reject=(2,))  # índice 1 queda pendiente
        view = self.detail(p['number']).json()
        self.assertEqual([l['collectible'] for l in view['lines']], [True, False, False])
        for index in (1, 2):
            response = self.pay(p['number'], [(p['lines'][index]['id'], '10.00')])
            self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(PaymentModel.objects.count(), 0)

    # AC-07
    def test_allocations_must_match_the_amount_and_the_line_balance(self):
        p = self.quote()
        line = p['lines'][0]['id']
        self.assertEqual(self.pay(p['number'], [(line, '60.00')], amount='70.00').status_code, 400)
        self.assertEqual(self.pay(p['number'], [(line, '100.01')]).status_code, 400)
        self.assertEqual(self.pay(p['number'], [(line, '10.005')]).status_code, 400)
        self.assertEqual(self.pay(p['number'], [(line, '10.00')], payment_method='BITCOIN').status_code, 400)
        self.assertEqual(self.pay(p['number'], [(line, '10.00')], payment_date='2999-01-01').status_code, 400)

    # AC-05
    def test_new_version_keeps_one_obligation_and_what_was_collected(self):
        p = self.quote(accept=(0, 1), reject=(2,))
        self.pay(p['number'], [(p['lines'][0]['id'], '60.00')])
        v2 = self.client.post(f"{QUOTES}{p['id']}/new-version/").json()
        self.assertEqual(self.client.post(f"{QUOTES}{v2['id']}/present/").status_code, 200)
        view = self.detail(p['number']).json()
        self.assertEqual((view['version'], view['totals']['paid'], view['totals']['balance']),
                         (2, '60.00', '240.00'))
        line_v2 = next(l for l in view['lines'] if l['description'] == 'Limpieza')['line_id']
        self.assertEqual(self.pay(p['number'], [(line_v2, '40.00')]).status_code, 201)
        self.assertEqual(ObligationModel.objects.count(), 1)
        self.assertEqual(self.detail(p['number']).json()['totals']['paid'], '100.00')
        self.assertEqual(self.detail(p['number']).json()['proforma_id'], v2['id'])  # sigue la versión vigente

    # AC-06
    def test_line_with_payments_cannot_be_rectified_to_rejected(self):
        p = self.quote()
        line = p['lines'][0]['id']
        self.pay(p['number'], [(line, '10.00')])
        blocked = self.client.post(f"{QUOTES}{p['id']}/lines/{line}/rectify/", {
            'idempotency_key': str(uuid4()), 'decision': 'rejected', 'reason': 'Cambio'}, format='json')
        self.assertEqual(blocked.status_code, 409, blocked.content)
        free = p['lines'][1]['id']  # sin cobros: sigue pudiéndose rectificar
        ok = self.client.post(f"{QUOTES}{p['id']}/lines/{free}/rectify/", {
            'idempotency_key': str(uuid4()), 'decision': 'rejected', 'reason': 'Cambio'}, format='json')
        self.assertEqual(ok.status_code, 201, ok.content)

    # AC-09
    def test_list_filters_by_customer_status_and_date(self):
        p = self.quote(accept=(0,), reject=())
        self.pay(p['number'], [(p['lines'][0]['id'], '100.00')])
        q = self.quote(accept=(1,), reject=())
        self.pay(q['number'], [(q['lines'][1]['id'], '10.00')])
        rows = self.client.get(f'{BASE}obligations/').json()['results']
        self.assertEqual({r['number']: r['payment_status'] for r in rows},
                         {p['number']: 'paid', q['number']: 'partial'})
        self.assertEqual(len(self.client.get(f'{BASE}obligations/?status=partial').json()['results']), 1)
        self.assertEqual(len(self.client.get(f'{BASE}obligations/?customer_id={uuid4()}').json()['results']), 0)
        self.assertEqual(len(self.client.get(f'{BASE}obligations/?customer_id={self.customer.pk}').json()['results']), 2)
        self.assertEqual(self.client.get(f'{BASE}obligations/?date_from=2999-01-01').json()['count'], 0)
        self.assertEqual(self.client.get(f'{BASE}obligations/?status=nope').status_code, 400)

    # AC-10
    def test_company_isolation_and_disabled_module(self):
        p = self.quote()
        stranger = APIClient()
        stranger.force_authenticate(self.other)
        DjangoCompanyModuleRepository(self.other.company_id).enabled_keys()
        for key in ('catalog', 'services', 'quotations', 'receivables'):
            DjangoCompanyModuleRepository(self.other.company_id).enable(key)
        self.assertEqual(stranger.get(f"{BASE}commitments/quotation/{p['number']}/").status_code, 404)
        self.assertEqual(self.pay(p['number'], [(p['lines'][0]['id'], '10.00')], client=stranger).status_code, 404)
        DjangoCompanyModuleRepository(self.admin.company_id).disable('receivables')
        self.assertEqual(self.detail(p['number']).status_code, 403)

    def test_draft_proforma_is_not_collectible_and_unknown_kind_is_404(self):
        body = self.client.post(QUOTES, {'customer_id': str(self.customer.pk), 'date': '2026-11-03', 'lines': [
            {'service_id': str(self.a.pk), 'quantity': '1'}]}, format='json').json()
        self.assertEqual(self.detail(body['number']).json()['allowed_actions'], [])
        self.assertEqual(self.pay(body['number'], [(body['lines'][0]['id'], '10.00')]).status_code, 409)
        self.assertEqual(self.detail(body['number'], kind='other').status_code, 404)

    # Odontología: misma semántica con la proforma de pieza dental
    def test_dental_proforma_can_be_collected_too(self):
        url = f'{DENTAL}patients/{self.customer.pk}/proformas/'
        body = self.client.post(url, {'date': '2026-11-04', 'lines': [
            {'service_id': str(self.a.pk), 'quantity': '1', 'dental_piece': '18'}]}, format='json').json()
        p = self.client.post(f"{DENTAL}proformas/{body['id']}/present/").json()
        accept = self.client.post(f"{DENTAL}proformas/{p['id']}/decisions/", {
            'idempotency_key': str(uuid4()), 'decision': 'accepted', 'line_ids': [p['lines'][0]['id']],
            'accepted_by_name': 'Rosa', 'medium': 'in_person'}, format='json')
        self.assertEqual(accept.status_code, 201, accept.content)
        response = self.pay(p['number'], [(p['lines'][0]['id'], '30.00')], kind='dental')
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()['totals']['balance'], '70.00')
        self.assertEqual(response.json()['lines'][0]['piece'], '18')
        self.assertEqual(response.json()['proforma_id'], p['id'])
        blocked = self.client.post(f"{DENTAL}proformas/{p['id']}/lines/{p['lines'][0]['id']}/rectify/", {
            'idempotency_key': str(uuid4()), 'decision': 'rejected', 'reason': 'x'}, format='json')
        self.assertEqual(blocked.status_code, 409, blocked.content)


    # REV-01: «hoy» respeta TIME_ZONE y no el día UTC
    @override_settings(TIME_ZONE='Pacific/Kiritimati')  # UTC+14
    def test_payment_date_uses_the_configured_time_zone(self):
        p = self.quote()
        line = p['lines'][0]['id']
        instant = datetime(2026, 11, 5, 23, 0, tzinfo=dt_timezone.utc)  # local: 6 nov 13:00
        with mock.patch('django.utils.timezone.now', return_value=instant):
            default = self.pay(p['number'], [(line, '10.00')])
            self.assertEqual(default.status_code, 201, default.content)
            self.assertEqual(default.json()['payment']['payment_date'], '2026-11-06')
            self.assertEqual(self.pay(p['number'], [(line, '10.00')], payment_date='2026-11-06').status_code, 201)
            self.assertEqual(self.pay(p['number'], [(line, '10.00')], payment_date='2026-11-07').status_code, 400)

    # REV-03: la lista oculta solo lo no autorizado y no traga otros errores
    def test_list_hides_disabled_sources_but_does_not_swallow_other_errors(self):
        q = self.quote()
        self.pay(q['number'], [(q['lines'][0]['id'], '10.00')])
        url = f'{DENTAL}patients/{self.customer.pk}/proformas/'
        body = self.client.post(url, {'date': '2026-11-04', 'lines': [{'service_id': str(self.a.pk), 'quantity': '1'}]},
                                format='json').json()
        d = self.client.post(f"{DENTAL}proformas/{body['id']}/present/").json()
        self.client.post(f"{DENTAL}proformas/{d['id']}/decisions/", {
            'idempotency_key': str(uuid4()), 'decision': 'accepted', 'line_ids': [d['lines'][0]['id']],
            'accepted_by_name': 'Rosa', 'medium': 'in_person'}, format='json')
        self.pay(d['number'], [(d['lines'][0]['id'], '10.00')], kind='dental')
        self.assertEqual(len(self.client.get(f'{BASE}obligations/').json()['results']), 2)
        DjangoCompanyModuleRepository(self.admin.company_id).disable('dentistry')
        rows = self.client.get(f'{BASE}obligations/').json()['results']
        self.assertEqual([r['kind'] for r in rows], ['quotation'])
        with mock.patch('modules.receivables.api.views._authorize', side_effect=RuntimeError('boom')):
            with self.assertRaises(RuntimeError):
                self.client.get(f'{BASE}obligations/')
