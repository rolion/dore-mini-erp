"""CONT-02: el adaptador real del puerto `PeriodUsage` con asientos reales (AC-08)."""
from datetime import date

from modules.accounting.infrastructure.adapters import JournalPeriodUsage
from modules.accounting.tests.test_journal_service import JournalBase
from modules.accounting.tests.test_fiscal_periods_api import URL
from modules.accounts.testing import authenticate, make_admin
from rest_framework.test import APIClient


class JournalPeriodUsageTests(JournalBase):
    def test_counts_only_entries_that_would_fall_outside(self):  # AC-08
        self.post(accounting_date=date(2026, 4, 10))
        self.post(accounting_date=date(2026, 6, 20))
        usage = JournalPeriodUsage()
        args = (self.company.id, self.period.id)
        self.assertEqual(usage.entries_outside(*args, date(2026, 4, 1), date(2026, 6, 30)), 0)
        self.assertEqual(usage.entries_outside(*args, date(2026, 4, 11), date(2026, 6, 30)), 1)
        self.assertEqual(usage.entries_outside(*args, date(2026, 4, 11), date(2026, 6, 19)), 2)
        self.assertEqual(usage.entries_outside(self.other.id, self.period.id, date(2026, 5, 1), date(2026, 5, 2)), 0)

    def test_the_api_blocks_a_range_that_would_leave_entries_outside(self):  # AC-08
        self.post(accounting_date=date(2026, 6, 20))
        client = APIClient()
        authenticate(client, make_admin(self.company, 'ana'))
        blocked = client.patch(f'{URL}{self.period.id}/', {'end_date': '2026-06-10'}, format='json')
        self.assertEqual((blocked.status_code, blocked.data['code']), (409, 'period_has_entries'))
        ok = client.patch(f'{URL}{self.period.id}/', {'end_date': '2026-07-31'}, format='json')
        self.assertEqual(ok.status_code, 200)
