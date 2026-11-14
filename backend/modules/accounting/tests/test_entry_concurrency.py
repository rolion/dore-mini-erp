"""PB-ACC-002: concurrencia del registro de entradas (AC-02)."""
from uuid import uuid4

from django.test import TransactionTestCase

from modules.accounting import services
from modules.accounting.domain.account import Account
from modules.accounting.infrastructure.django.models import EntryModel
from modules.accounting.infrastructure.django.repositories import DjangoAccountRepository
from modules.accounting.tests.test_concurrency import _run_together
from modules.accounting.tests.test_entry_service import entry_input
from modules.accounts.testing import make_company


class ConcurrentEntryTests(TransactionTestCase):
    def setUp(self):
        self.company = make_company('A')
        self.caja = DjangoAccountRepository(self.company.id).save(Account.create('Caja', 'BOB'))

    def test_two_simultaneous_requests_for_the_same_origin_create_one_entry(self):  # AC-02
        data = entry_input(self.caja, origin_id=uuid4())
        results = []
        outcomes = _run_together(*[lambda: results.append(services.record_entry(self.company.id, data))] * 2)
        self.assertEqual(outcomes, [None, None])
        self.assertEqual(sorted(r.created for r in results), [False, True])
        self.assertEqual(EntryModel.objects.filter(company_id=self.company.id).count(), 1)

    def test_simultaneous_requests_for_different_origins_with_the_same_id_create_two(self):  # AC-02
        shared = uuid4()
        outcomes = _run_together(
            lambda: services.record_entry(self.company.id, entry_input(self.caja, origin_kind='PRODUCT', origin_id=shared)),
            lambda: services.record_entry(self.company.id, entry_input(self.caja, origin_kind='SERVICE', origin_id=shared)),
        )
        self.assertEqual(outcomes, [None, None])
        self.assertEqual(EntryModel.objects.count(), 2)
