import threading

from django.db import close_old_connections, connection, transaction
from django.test import TransactionTestCase

from modules.accounting.application.use_cases import ConfigureMethod, DeactivateAccount
from modules.accounting.domain.account import Account, AccountConflict, AccountValidationError
from modules.accounting.infrastructure.django.models import MethodMappingModel
from modules.accounting.infrastructure.django.repositories import DjangoAccountRepository, DjangoMethodMappingRepository
from modules.accounts.testing import make_company


def _run_together(*jobs):
    """Ejecuta los trabajos en hilos que arrancan a la vez; devuelve las excepciones de cada uno."""
    barrier = threading.Barrier(len(jobs))
    outcomes = [None] * len(jobs)

    def wrap(index, job):
        try:
            barrier.wait(timeout=10)
            with transaction.atomic():
                job()
        except Exception as exc:  # noqa: BLE001 - se examina en el hilo principal
            outcomes[index] = exc
        finally:
            close_old_connections()
            connection.close()

    threads = [threading.Thread(target=wrap, args=(i, job)) for i, job in enumerate(jobs)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return outcomes


class ConcurrentMappingTests(TransactionTestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        self.accounts = DjangoAccountRepository(self.company.id)
        self.mappings = DjangoMethodMappingRepository(self.company.id)

    def test_two_simultaneous_puts_on_the_same_method_leave_one_destination(self):  # EDGE-06
        first, second = (self.accounts.save(Account.create(name, 'BOB')) for name in ('Banco A', 'Banco B'))
        outcomes = _run_together(
            lambda: ConfigureMethod(self.accounts, self.mappings).execute('QR', first.id, True),
            lambda: ConfigureMethod(self.accounts, self.mappings).execute('QR', second.id, True),
        )
        self.assertEqual(outcomes, [None, None])
        rows = MethodMappingModel.objects.filter(company_id=self.company.id, method='QR')
        self.assertEqual(rows.count(), 1)
        self.assertIn(rows.get().account_id, (first.id, second.id))

    def test_deactivating_and_assigning_the_same_account_never_leaves_an_active_method_on_an_inactive_account(self):
        account = self.accounts.save(Account.create('Banco', 'BOB'))
        outcomes = _run_together(
            lambda: DeactivateAccount(self.accounts, self.mappings).execute(account.id),
            lambda: ConfigureMethod(self.accounts, self.mappings).execute('QR', account.id, True),
        )
        for outcome in outcomes:
            self.assertTrue(outcome is None or isinstance(outcome, (AccountConflict, AccountValidationError)), outcome)
        stored = self.accounts.get(account.id)
        mapping = self.mappings.get('QR')
        self.assertFalse(mapping.is_active and mapping.account_id == account.id and not stored.is_active)
