"""PB-INV-002: almacenes por empresa."""
from threading import Barrier, Thread
from unittest import mock
from uuid import uuid4

from django.db import connection
from django.test import SimpleTestCase, TransactionTestCase
from rest_framework.test import APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.inventory.application.use_cases import DeactivateWarehouse
from modules.inventory.domain.exceptions import WarehouseConflict, WarehouseValidationError
from modules.inventory.domain.warehouse import Warehouse
from modules.inventory.infrastructure.django.models import WarehouseModel
from modules.inventory.infrastructure.django.repositories import DjangoWarehouseRepository
from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
from modules.modularity.tests.test_enforcement import set_enabled

URL = '/api/warehouses/'


class WarehouseDomainTests(SimpleTestCase):
    def test_name_is_required(self):
        with self.assertRaises(WarehouseValidationError):
            Warehouse.create('  ')

    def test_default_cannot_be_deactivated_and_inactive_cannot_be_default(self):  # INV-06
        warehouse = Warehouse.create('Central')
        warehouse.make_default()
        with self.assertRaises(WarehouseConflict) as ctx:
            warehouse.deactivate()
        self.assertEqual(ctx.exception.code, 'warehouse_is_default')
        other = Warehouse.create('Otro')
        other.deactivate()
        with self.assertRaises(WarehouseConflict) as ctx:
            other.make_default()
        self.assertEqual(ctx.exception.code, 'warehouse_inactive')


class FakeActivity:
    def __init__(self, balance=False, receipts=False):
        self.balance, self.receipts = balance, receipts

    def has_nonzero_balance(self, warehouse_id):
        return self.balance

    def has_pending_receipts(self, warehouse_id):
        return self.receipts


class WarehouseApiTestCase(APITestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        authenticate(self.client, make_admin(self.company, username='ana'))
        set_enabled(self.company, [*DEFAULT_ENABLED_KEYS, 'inventory'])

    def create(self, name='Sucursal', **extra):
        response = self.client.post(URL, {'name': name, **extra}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()


class WarehouseApiTests(WarehouseApiTestCase):
    def test_company_has_a_default_warehouse(self):  # AC-08
        results = self.client.get(URL).json()['results']
        self.assertEqual([(w['name'], w['is_default'], w['active']) for w in results],
                         [('Almacén principal', True, True)])
        self.assertEqual(self.client.get(URL).json()['count'], 1)  # idempotente

    def test_create_with_and_without_default(self):  # AC-08
        second = self.create()
        self.assertFalse(second['is_default'])
        third = self.create('Bodega', description=' Fondo ', is_default=True)
        self.assertTrue(third['is_default'])
        self.assertEqual(third['description'], 'Fondo')
        defaults = [w['name'] for w in self.client.get(URL).json()['results'] if w['is_default']]
        self.assertEqual(defaults, ['Bodega'])

    def test_make_default_moves_the_mark(self):  # AC-08
        second = self.create()
        response = self.client.post(f"{URL}{second['id']}/make-default/")
        self.assertTrue(response.json()['is_default'])
        self.assertEqual(WarehouseModel.objects.filter(company_id=self.company.id, is_default=True).count(), 1)

    def test_make_default_on_inactive_is_409(self):  # EDGE-05
        second = self.create()
        self.client.post(f"{URL}{second['id']}/deactivate/")
        response = self.client.post(f"{URL}{second['id']}/make-default/")
        self.assertEqual((response.status_code, response.json()['code']), (409, 'warehouse_inactive'))

    def test_default_cannot_be_deactivated(self):  # AC-09
        default = self.client.get(URL).json()['results'][0]
        response = self.client.post(f"{URL}{default['id']}/deactivate/")
        self.assertEqual((response.status_code, response.json()['code']), (409, 'warehouse_is_default'))
        response = self.client.patch(f"{URL}{default['id']}/", {'is_default': False}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_deactivate_and_activate_keep_the_warehouse(self):  # AC-09
        second = self.create()
        self.assertFalse(self.client.post(f"{URL}{second['id']}/deactivate/").json()['active'])
        self.assertEqual([w['name'] for w in self.client.get(URL, {'active': 'true'}).json()['results']],
                         ['Almacén principal'])
        self.assertEqual(len(self.client.get(URL).json()['results']), 2)
        self.assertTrue(self.client.post(f"{URL}{second['id']}/activate/").json()['active'])

    def test_names_are_unique_case_insensitively(self):  # EDGE-02
        self.create('Central')
        response = self.client.post(URL, {'name': 'CENTRAL'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('name', response.json())

    def test_edit_and_search(self):
        second = self.create()
        response = self.client.patch(f"{URL}{second['id']}/", {'name': 'Tienda', 'description': 'Calle 1'}, format='json')
        self.assertEqual((response.json()['name'], response.json()['description']), ('Tienda', 'Calle 1'))
        self.assertEqual([w['name'] for w in self.client.get(URL, {'search': 'tien'}).json()['results']], ['Tienda'])

    def test_other_company_cannot_see_or_touch_warehouses(self):  # AC-08, INV-09
        second = self.create()
        other = make_company('Empresa B')
        authenticate(self.client, make_admin(other, username='beto'))
        set_enabled(other, ['inventory'])
        names = [w['name'] for w in self.client.get(URL).json()['results']]
        self.assertEqual(names, ['Almacén principal'])
        for method, suffix in (('get', ''), ('patch', ''), ('post', 'deactivate/'), ('post', 'make-default/')):
            response = getattr(self.client, method)(f"{URL}{second['id']}/{suffix}", {}, format='json') \
                if method != 'get' else self.client.get(f"{URL}{second['id']}/")
            self.assertEqual(response.status_code, 404, (method, suffix))
        self.assertEqual(WarehouseModel.objects.filter(company_id=self.company.id).count(), 1 + 1)

    def test_needs_inventory_enabled(self):  # EDGE-04
        set_enabled(self.company, DEFAULT_ENABLED_KEYS)
        self.assertEqual(self.client.get(URL).status_code, 403)

    def test_unknown_warehouse_is_404(self):
        self.assertEqual(self.client.get(f'{URL}{uuid4()}/').status_code, 404)


class DeactivateWithActivityTests(WarehouseApiTestCase):
    def deactivate(self, activity):
        repository = DjangoWarehouseRepository(self.company.id)
        repository.ensure_default()
        warehouse = repository.save(Warehouse.create('Secundario'))
        return DeactivateWarehouse(repository, activity).execute(warehouse.id)

    def test_balance_blocks_deactivation(self):  # AC-09, INV-07
        with self.assertRaises(WarehouseConflict) as ctx:
            self.deactivate(FakeActivity(balance=True))
        self.assertEqual(ctx.exception.code, 'warehouse_has_stock')

    def test_pending_receipts_block_deactivation(self):  # AC-09, INV-07
        with self.assertRaises(WarehouseConflict) as ctx:
            self.deactivate(FakeActivity(receipts=True))
        self.assertEqual(ctx.exception.code, 'warehouse_pending_receipts')

    def test_without_activity_it_deactivates(self):
        self.assertFalse(self.deactivate(FakeActivity()).active)


class ConcurrentSeedTests(TransactionTestCase):
    def test_simultaneous_first_reads_seed_a_single_default(self):  # EDGE-01
        company = make_company('Empresa C')
        barrier = Barrier(2)

        def seed():
            try:
                barrier.wait()
                DjangoWarehouseRepository(company.id).ensure_default()
            finally:
                connection.close()

        threads = [Thread(target=seed) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(WarehouseModel.objects.filter(company_id=company.id, is_default=True).count(), 1)
        self.assertEqual(WarehouseModel.objects.filter(company_id=company.id).count(), 1)
