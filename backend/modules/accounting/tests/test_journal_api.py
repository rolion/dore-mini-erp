"""CONT-11: API del libro de asientos (AC-01..07): alta manual, lista estable, detalle y reversión."""
from decimal import Decimal

from django.db import transaction

from modules.accounting import services
from modules.accounting.infrastructure.django.models import JournalEntryModel, JournalLineModel
from modules.accounting.infrastructure.django.repositories import DjangoFiscalPeriodRepository
from modules.accounting.tests.journal_support import DAY, automatic, entry_input, make_account, make_period
from modules.accounting.tests.test_api import AccountingApiBase
from modules.accounting.tests.test_entries_api import enable
from modules.modularity.infrastructure.django.models import CompanyModuleModel

URL = '/api/accounting/journal-entries/'


class JournalApiTests(AccountingApiBase):
    def setUp(self):
        super().setUp()
        enable(self.company_a, 'accounting')
        enable(self.company_b, 'accounting')
        self.cash = make_account(self.company_a.id, 'Caja', code='111001')
        self.bank = make_account(self.company_a.id, 'Banco', code='111002')
        self.income = make_account(self.company_a.id, 'Ingresos servicios', 'INCOME', code='411001')
        make_period(self.company_a.id)
        make_period(self.company_b.id)

    def body(self, bank='300.00', **extra):
        data = {'accounting_date': '2026-05-10', 'description': 'Servicio', 'lines': [
            {'account_id': str(self.cash.id), 'debit': '200.00'},
            {'account_id': str(self.bank.id), 'debit': bank},
            {'account_id': str(self.income.id), 'credit': '500.00'}]}
        data.update(extra)
        return data

    def post(self, **kwargs):
        return self.client_a.post(URL, self.body(**kwargs), format='json')

    def seed(self, count, **overrides):
        ids = []
        for index in range(count):
            with transaction.atomic():
                ids.append(services.post_journal_entry(
                    self.company_a.id, entry_input(self.cash, self.bank, self.income, description=f'M{index}',
                                                   **overrides)).entry.id)
        return ids

    def test_registers_a_manual_service_entry(self):  # AC-01
        response = self.post()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual((response.data['total'], response.data['source'], response.data['origin']),
                         ('500.00', 'MANUAL', None))
        self.assertEqual([(l['account']['code'], l['debit'], l['credit']) for l in response.data['lines']],
                         [('111001', '200.00', '0.00'), ('111002', '300.00', '0.00'), ('411001', '0.00', '500.00')])
        self.assertTrue(response.data['can_reverse'])
        self.assertEqual(response.data['period']['name'], 'Q2')

    def test_unbalanced_entry_is_rejected_without_partial_writes(self):  # AC-02
        response = self.post(bank='299.00')
        self.assertEqual(response.status_code, 400)
        self.assertIn('lines', response.data)
        self.assertEqual((JournalEntryModel.objects.count(), JournalLineModel.objects.count()), (0, 0))

    def test_rejects_invalid_shapes(self):  # AC-02
        base = self.body()
        bad = [dict(base, description=' '), dict(base, accounting_date='ayer'), dict(base, lines=[]),
               dict(base, lines=base['lines'][:1]),
               self.body(bank='-300.00'), self.body(bank='300.001'),
               dict(base, accounting_date='2026-09-01')]  # sin período
        for data in bad:
            self.assertEqual(self.client_a.post(URL, data, format='json').status_code, 400, data)
        both = self.body()
        both['lines'][0]['credit'] = '1.00'
        self.assertEqual(self.client_a.post(URL, both, format='json').status_code, 400)
        self.assertEqual(JournalEntryModel.objects.count(), 0)

    def test_manual_entry_cannot_carry_an_origin(self):  # INV-06
        response = self.post(origin_kind='SALE', origin_id='7b2a6c1e-0d7b-4c2c-9f64-3b0f5c6e8a11')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['source'], 'MANUAL')
        self.assertIsNone(JournalEntryModel.objects.get().origin_id)

    def test_foreign_account_is_rejected(self):  # AC-04
        other = make_account(self.company_b.id, 'Caja ajena', code='111009')
        data = self.body()
        data['lines'][0]['account_id'] = str(other.id)
        self.assertEqual(self.client_a.post(URL, data, format='json').status_code, 400)

    def test_pagination_is_stable_with_equal_dates_and_timestamps(self):  # AC-03
        ids = self.seed(5)
        JournalEntryModel.objects.update(created_at=JournalEntryModel.objects.first().created_at)
        expected = [str(i) for i in JournalEntryModel.objects.order_by('-accounting_date', '-created_at', '-id')
                    .values_list('id', flat=True)]
        seen, page = [], 1
        while True:
            response = self.client_a.get(URL, {'page': page, 'page_size': 2})
            self.assertEqual(response.status_code, 200)
            seen += [row['id'] for row in response.data['results']]
            if not response.data['next']:
                break
            page += 1
        self.assertEqual((seen, response.data['count']), (expected, 5))
        self.assertEqual(set(seen), {str(i) for i in ids})

    def test_orders_by_accounting_date_descending(self):  # AC-03
        with transaction.atomic():
            for day in (10, 12, 11):
                services.post_journal_entry(self.company_a.id, entry_input(
                    self.cash, self.bank, self.income, accounting_date=DAY.replace(day=day)))
        dates = [row['accounting_date'] for row in self.client_a.get(URL).data['results']]
        self.assertEqual(dates, ['2026-05-12', '2026-05-11', '2026-05-10'])

    def test_filters_by_dates_account_and_source(self):  # AC-03
        self.seed(1)
        with transaction.atomic():
            services.post_journal_entry(self.company_a.id, entry_input(
                self.cash, self.bank, self.income, accounting_date=DAY.replace(day=20), **automatic()))
        other = make_account(self.company_a.id, 'Otra', code='111003')

        def count(**params):
            response = self.client_a.get(URL, params)
            self.assertEqual(response.status_code, 200, response.data)
            return response.data['count']

        self.assertEqual((count(), count(source='MANUAL'), count(source='AUTOMATIC')), (2, 1, 1))
        self.assertEqual((count(date_from='2026-05-15'), count(date_to='2026-05-15'),
                          count(date_from='2026-05-10', date_to='2026-05-10')), (1, 1, 1))
        self.assertEqual((count(account_id=str(self.cash.id)), count(account_id=str(other.id))), (2, 0))
        self.assertEqual(count(origin_kind='SERVICE_PAYMENT'), 1)

    def test_invalid_filters_are_a_400(self):  # AC-03
        for params in ({'source': 'X'}, {'date_from': '2026-06-01', 'date_to': '2026-05-01'},
                       {'account_id': 'no'}, {'account_id': str(make_account(self.company_b.id, 'Z', code='1').id)}):
            self.assertEqual(self.client_a.get(URL, params).status_code, 400, params)

    def test_other_company_sees_nothing(self):  # AC-04
        entry_id = self.post().data['id']
        self.assertEqual(self.client_b.get(URL).data['count'], 0)
        self.assertEqual(self.client_b.get(f'{URL}{entry_id}/').status_code, 404)
        reverse = {'reversal_date': '2026-05-11', 'reason': 'x'}
        self.assertEqual(self.client_b.post(f'{URL}{entry_id}/reverse/', reverse, format='json').status_code, 404)

    def test_there_are_no_edit_or_delete_routes(self):  # AC-06
        entry_id = self.post().data['id']
        for method in ('put', 'patch', 'delete'):
            self.assertEqual(getattr(self.client_a, method)(f'{URL}{entry_id}/', {}, format='json').status_code, 405)
        self.assertEqual(self.client_a.put(URL, {}, format='json').status_code, 405)

    def test_detail_of_an_automatic_entry_has_origin_and_no_edit(self):  # AC-05
        with transaction.atomic():
            posted = services.post_journal_entry(self.company_a.id, entry_input(
                self.cash, self.bank, self.income, **automatic(origin_kind='PRODUCT')))
        enabled = self.client_a.get(f'{URL}{posted.entry.id}/')
        self.assertEqual((enabled.data['source'], enabled.data['origin']['kind'], enabled.data['origin']['available']),
                         ('AUTOMATIC', 'PRODUCT', False))
        enable(self.company_a, 'sales')
        self.assertTrue(self.client_a.get(f'{URL}{posted.entry.id}/').data['origin']['available'])
        self.assertEqual(enabled.data['created_by_name'], 'Ana')

    def test_reverses_once_and_links_both_entries(self):  # AC-05, AC-07
        entry_id = self.post().data['id']
        payload = {'reversal_date': '2026-05-12', 'reason': 'Error de captura'}
        first = self.client_a.post(f'{URL}{entry_id}/reverse/', payload, format='json')
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual((first.data['reverses_id'], first.data['reversal_reason'], first.data['can_reverse']),
                         (entry_id, 'Error de captura', False))
        self.assertEqual([(l['debit'], l['credit']) for l in first.data['lines']],
                         [('0.00', '200.00'), ('0.00', '300.00'), ('500.00', '0.00')])
        again = self.client_a.post(f'{URL}{entry_id}/reverse/', payload, format='json')
        self.assertEqual((again.status_code, again.data['id']), (200, first.data['id']))
        original = self.client_a.get(f'{URL}{entry_id}/').data
        self.assertEqual((original['reversed_by_id'], original['can_reverse']), (first.data['id'], False))
        row = next(r for r in self.client_a.get(URL).data['results'] if r['id'] == entry_id)
        self.assertEqual(row['reversed_by_id'], first.data['id'])
        self.assertEqual(JournalEntryModel.objects.count(), 2)

    def test_reversal_validations(self):  # AC-07
        entry_id = self.post().data['id']
        url = f'{URL}{entry_id}/reverse/'
        for payload in ({'reversal_date': '2026-05-12'}, {'reversal_date': '2026-05-12', 'reason': '  '},
                        {'reason': 'x'}, {'reversal_date': '2026-12-01', 'reason': 'x'}):
            self.assertEqual(self.client_a.post(url, payload, format='json').status_code, 400, payload)
        reversal = self.client_a.post(url, {'reversal_date': '2026-05-12', 'reason': 'x'}, format='json').data['id']
        self.assertEqual(self.client_a.post(f'{URL}{reversal}/reverse/', {'reversal_date': '2026-05-13',
                                                                         'reason': 'x'}, format='json').status_code, 400)

    def test_reversal_in_a_closed_period_is_rejected(self):  # AC-07
        entry_id = self.post().data['id']
        period = DjangoFiscalPeriodRepository(self.company_a.id).all()[0]
        self.assertEqual(self.client_a.post(f'/api/accounting/fiscal-periods/{period.id}/close/').status_code, 200)
        response = self.client_a.post(f'{URL}{entry_id}/reverse/', {'reversal_date': '2026-05-12', 'reason': 'x'},
                                      format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('reversal_date', response.data)
        self.assertEqual(self.client_a.post(URL, self.body(), format='json').status_code, 400)

    def test_requires_the_accounting_module(self):
        CompanyModuleModel.objects.filter(company_id=self.company_a.id, module_key='accounting').delete()
        self.assertEqual(self.client_a.get(URL).status_code, 403)
        self.assertEqual(self.post().status_code, 403)

    def test_requires_authentication(self):
        from rest_framework.test import APIClient
        self.assertIn(APIClient().get(URL).status_code, (401, 403))

    def test_amounts_are_exact_decimals(self):
        response = self.post(bank='300.10', lines=None) if False else None
        data = self.body(bank='0.10')
        data['lines'][2]['credit'] = '200.10'
        created = self.client_a.post(URL, data, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(Decimal(created.data['total']), Decimal('200.10'))
