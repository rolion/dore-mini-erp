"""CONT-10: API de períodos fiscales (AC-01..05, AC-08) y permisos."""
from unittest import mock
from uuid import uuid4

from django.contrib.auth import get_user_model

from rest_framework.test import APIClient

from modules.accounting.infrastructure.django.models import EntryModel
from modules.accounting.tests.test_api import AccountingApiBase
from modules.accounts.testing import authenticate, make_admin

URL = '/api/accounting/fiscal-periods/'


class FiscalPeriodApiTests(AccountingApiBase):
    def create(self, client, name='2026', start='2026-01-01', end='2026-12-31'):
        return client.post(URL, {'name': name, 'start_date': start, 'end_date': end}, format='json')

    def test_creates_an_open_period_and_lists_latest_first(self):  # AC-01
        self.assertEqual(self.create(self.client_a, '2025', '2025-01-01', '2025-12-31').status_code, 201)
        response = self.create(self.client_a)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['status'], 'OPEN')
        self.assertEqual([p['name'] for p in self.client_a.get(URL).data], ['2026', '2025'])

    def test_rejects_inverted_dates_bad_names_and_duplicates(self):  # AC-02
        self.assertIn('end_date', self.create(self.client_a, start='2026-02-01', end='2026-01-01').data)
        self.assertEqual(self.create(self.client_a, name='').status_code, 400)
        self.assertEqual(self.client_a.post(URL, {'name': 'x', 'start_date': 'ayer', 'end_date': '2026-01-01'},
                                            format='json').status_code, 400)
        self.assertEqual(self.create(self.client_a).status_code, 201)
        dup = self.create(self.client_a, name='  2026'.upper().lower(), start='2027-01-01', end='2027-12-31')
        self.assertEqual(dup.status_code, 400)
        self.assertIn('name', dup.data)

    def test_rejects_every_kind_of_overlap_but_allows_contiguous_periods(self):  # AC-03
        self.create(self.client_a, 'Q1', '2026-01-01', '2026-03-31')
        for i, (start, end) in enumerate([('2026-01-01', '2026-03-31'), ('2026-02-01', '2026-02-10'),
                                          ('2025-12-01', '2026-06-30'), ('2026-03-31', '2026-04-30'),
                                          ('2025-12-01', '2026-01-01')]):
            response = self.create(self.client_a, f'X{i}', start, end)
            self.assertEqual(response.status_code, 409, (start, end))
            self.assertEqual((response.data['code'], response.data['periods']), ('period_overlap', ['Q1']))
        self.assertEqual(self.create(self.client_a, 'Q2', '2026-04-01', '2026-06-30').status_code, 201)

    def test_two_companies_can_use_the_same_ranges_and_names(self):  # AC-04
        self.assertEqual(self.create(self.client_a).status_code, 201)
        other = self.create(self.client_b)
        self.assertEqual(other.status_code, 201, other.data)
        self.assertEqual(len(self.client_b.get(URL).data), 1)

    def test_other_company_cannot_see_edit_or_close_a_period(self):  # AC-04
        period_id = self.create(self.client_a).data['id']
        for call in (self.client_b.get(f'{URL}{period_id}/'),
                     self.client_b.patch(f'{URL}{period_id}/', {'name': 'x'}, format='json'),
                     self.client_b.post(f'{URL}{period_id}/close/'),
                     self.client_b.post(f'{URL}{period_id}/reopen/')):
            self.assertEqual(call.status_code, 404)

    def test_close_reopen_and_closed_period_is_immutable(self):  # AC-05
        period_id = self.create(self.client_a).data['id']
        closed = self.client_a.post(f'{URL}{period_id}/close/')
        self.assertEqual((closed.status_code, closed.data['status'], closed.data['closed_by_name']), (200, 'CLOSED', 'ana'))
        self.assertEqual(self.client_a.post(f'{URL}{period_id}/close/').data['code'], 'period_invalid_state')
        edit = self.client_a.patch(f'{URL}{period_id}/', {'name': 'Otro'}, format='json')
        self.assertEqual((edit.status_code, edit.data['code']), (409, 'period_closed'))
        reopened = self.client_a.post(f'{URL}{period_id}/reopen/')
        self.assertEqual((reopened.data['status'], reopened.data['reopened_by_name']), ('OPEN', 'ana'))
        self.assertEqual(self.client_a.post(f'{URL}{period_id}/reopen/').data['code'], 'period_invalid_state')
        self.assertEqual(self.client_a.patch(f'{URL}{period_id}/', {'name': 'Otro'}, format='json').status_code, 200)

    def test_closing_creates_no_ledger_records(self):  # INV-07
        period_id = self.create(self.client_a).data['id']
        self.client_a.post(f'{URL}{period_id}/close/')
        self.assertEqual(EntryModel.objects.count(), 0)

    def test_editing_limits_checks_overlap_with_other_periods(self):  # AC-03
        self.create(self.client_a, 'Q1', '2026-01-01', '2026-03-31')
        q2 = self.create(self.client_a, 'Q2', '2026-04-01', '2026-06-30').data['id']
        self.assertEqual(self.client_a.patch(f'{URL}{q2}/', {'start_date': '2026-03-31'}, format='json').status_code, 409)
        ok = self.client_a.patch(f'{URL}{q2}/', {'end_date': '2026-07-31'}, format='json')
        self.assertEqual((ok.status_code, str(ok.data['end_date'])), (200, '2026-07-31'))
        self.assertEqual(self.client_a.patch(f'{URL}{q2}/', {'end_date': '2026-03-01'}, format='json').status_code, 400)

    def test_limits_change_is_blocked_when_entries_would_fall_outside(self):  # AC-08
        period_id = self.create(self.client_a).data['id']
        usage = mock.Mock()
        usage.entries_outside.return_value = 2
        with mock.patch('modules.accounting.api.views.JournalPeriodUsage', return_value=usage):
            blocked = self.client_a.patch(f'{URL}{period_id}/', {'end_date': '2026-06-30'}, format='json')
            self.assertEqual((blocked.status_code, blocked.data['code']), (409, 'period_has_entries'))
            usage.entries_outside.return_value = 0
            self.assertEqual(self.client_a.patch(f'{URL}{period_id}/', {'end_date': '2026-06-30'},
                                                 format='json').status_code, 200)
            usage.entries_outside.reset_mock()
            self.client_a.patch(f'{URL}{period_id}/', {'name': 'Solo nombre'}, format='json')
            usage.entries_outside.assert_not_called()
        self.assertEqual(str(self.client_a.get(f'{URL}{period_id}/').data['end_date']), '2026-06-30')

    def test_non_admin_members_cannot_use_any_endpoint(self):  # Authorization
        period_id = self.create(self.client_a).data['id']
        member = self.login(make_admin(self.company_a, 'mario', role='member'))
        self.assertEqual(member.get(URL).status_code, 403)
        self.assertEqual(self.create(member, 'otro', '2027-01-01', '2027-12-31').status_code, 403)
        self.assertEqual(member.patch(f'{URL}{period_id}/', {'name': 'x'}, format='json').status_code, 403)
        self.assertEqual(member.post(f'{URL}{period_id}/close/').status_code, 403)
        self.client_a.post(f'{URL}{period_id}/close/')
        self.assertEqual(member.post(f'{URL}{period_id}/reopen/').status_code, 403)
        self.assertEqual(self.client_a.get(f'{URL}{period_id}/').data['status'], 'CLOSED')

    def test_requires_authentication_and_a_company(self):  # Authorization
        self.assertEqual(APIClient().get(URL).status_code, 401)
        no_company = get_user_model().objects.create_user(username='sin-empresa', password='x-Pass-123')
        client = APIClient()
        authenticate(client, no_company)
        self.assertEqual(client.get(URL).status_code, 403)
        self.assertEqual(client.post(f'{URL}{uuid4()}/reopen/').status_code, 403)
