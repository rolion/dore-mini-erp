import threading

from django.db import close_old_connections, connection, transaction
from django.test import TransactionTestCase

from modules.accounts.testing import make_company
from modules.modularity.application.settings_use_cases import Actor, UpdateModuleSettings
from modules.modularity.infrastructure.django.models import SettingChangeModel
from modules.modularity.infrastructure.django.repositories import (
    DjangoCompanyModuleRepository,
    DjangoCompanySettingRepository,
    DjangoSettingChangeRepository,
)

PERCENT = 'sales.max_discount_percent'


class ConcurrentSaveTests(TransactionTestCase):
    """EDGE-03: dos administradores guardan a la vez; cada registro lleva el valor anterior real."""

    def test_simultaneous_saves_chain_old_and_new_values(self):
        company = make_company('Empresa A')
        DjangoCompanyModuleRepository(company.id).enabled_keys()  # siembra los módulos por defecto
        barrier = threading.Barrier(2)
        errors = []

        def save(value):
            try:
                use_case = UpdateModuleSettings(
                    DjangoCompanySettingRepository(company.id), DjangoSettingChangeRepository(company.id),
                    DjangoCompanyModuleRepository(company.id))
                barrier.wait(timeout=10)
                with transaction.atomic():
                    use_case.execute('sales', {PERCENT: value}, Actor(None, f'user-{value}'))
            except Exception as exc:  # noqa: BLE001 - se reporta en el hilo principal
                errors.append(exc)
            finally:
                close_old_connections()
                connection.close()

        threads = [threading.Thread(target=save, args=(v,)) for v in ('10', '20')]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        self.assertEqual(errors, [])
        rows = list(SettingChangeModel.objects.filter(company_id=company.id).order_by('changed_at', 'id'))
        self.assertEqual(len(rows), 2)
        first, second = rows
        self.assertEqual(first.old_value, '100.00 %')
        self.assertEqual(second.old_value, first.new_value)  # sin el bloqueo ambos dirían «100.00 %»
        final = DjangoCompanySettingRepository(company.id).values()[PERCENT]
        self.assertEqual(f'{final} %', second.new_value)
