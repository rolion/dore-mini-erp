"""PB-INV-007: política de stock negativo por empresa, aplicada a salidas, reversiones y ajustes."""
from decimal import Decimal
from uuid import uuid4

from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.inventory import services as inventory
from modules.inventory.api.insufficient_stock import InsufficientStockConflict
from modules.inventory.application.movement_ports import BlockNegativeStock
from modules.inventory.domain.exceptions import InsufficientStock, MovementConflict
from modules.inventory.infrastructure.django.models import StockMovementModel
from modules.modularity import services as modularity
from modules.modularity.domain import settings as domain
from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
from modules.modularity.tests.test_enforcement import set_enabled

from .policy import KEY, set_negative_stock
from .test_movements import LedgerTestCase


class PolicySettingDomainTests(SimpleTestCase):
    definition = domain.BY_SETTING_KEY[KEY]

    def test_default_is_blocked_and_kind_is_boolean(self):  # AC-01, INV-01
        self.assertEqual((self.definition.default, self.definition.kind), ('false', domain.BOOLEAN))
        self.assertFalse(BlockNegativeStock().allow_negative_stock())

    def test_only_explicit_booleans_are_valid(self):  # EDGE-04
        self.assertEqual(domain.validate(self.definition, True), 'true')
        self.assertEqual(domain.validate(self.definition, 'false'), 'false')
        for bad in ('si', 1, 0, None, '', 'True', []):
            with self.assertRaises(ValueError, msg=repr(bad)):
                domain.validate(self.definition, bad)

    def test_history_labels(self):  # AC-01
        self.assertEqual(domain.display(self.definition, 'false'), 'Bloqueado')
        self.assertEqual(domain.display(self.definition, 'true'), 'Permitido')


class PolicyFacadeTests(LedgerTestCase):
    def test_company_without_a_saved_value_is_blocked(self):  # AC-01
        self.assertFalse(modularity.get_inventory_settings(self.company.id).allow_negative_stock)

    def test_policy_is_per_company(self):  # AC-01
        set_negative_stock(self.company, True)
        self.assertTrue(modularity.get_inventory_settings(self.company.id).allow_negative_stock)
        self.assertFalse(modularity.get_inventory_settings(make_company('Otra').id).allow_negative_stock)

    def test_blocked_exit_carries_the_data_and_creates_nothing(self):  # AC-02, INV-02
        self.record('in', '2')
        with self.assertRaises(InsufficientStock) as ctx:
            self.record('out', '3')
        exc = ctx.exception
        self.assertEqual((exc.code, exc.product_id, exc.warehouse_id, exc.requested, exc.available),
                         ('insufficient_stock', self.product.id, self.warehouse.id, Decimal('3'), Decimal('2')))
        self.assertEqual(StockMovementModel.objects.count(), 1)
        self.assertEqual(self.balance(), Decimal('2'))

    def test_blocked_reversal_leaves_the_original_confirmed(self):  # AC-02
        entry, _ = self.record('in', '10')
        self.record('out', '8')
        with self.assertRaises(InsufficientStock) as ctx:
            inventory.reverse_movement(self.company.id, entry.id, user_id=None, user_name='ana')
        self.assertEqual((ctx.exception.requested, ctx.exception.available), (Decimal('10'), Decimal('2')))
        self.assertEqual(StockMovementModel.objects.get(pk=entry.id).status, 'confirmed')
        self.assertEqual(StockMovementModel.objects.count(), 2)

    def test_allowed_policy_lets_exit_and_reversal_go_negative(self):  # AC-03
        entry, _ = self.record('in', '10')
        self.record('out', '8')
        set_negative_stock(self.company, True)
        self.record('out', '5')
        self.assertEqual(self.balance(), Decimal('-3'))
        inventory.reverse_movement(self.company.id, entry.id, user_id=None, user_name='ana')
        self.assertEqual(self.balance(), Decimal('-13'))

    def test_exact_balance_is_allowed_and_entries_never_blocked(self):  # EDGE-01, INV-04, EDGE-06
        self.record('in', '4')
        self.record('out', '4')
        self.assertEqual(self.balance(), Decimal('0'))
        set_negative_stock(self.company, True)
        self.record('out', '1')
        set_negative_stock(self.company, False)
        self.record('in', '1')
        with self.assertRaises(MovementConflict):
            self.record('out', '5')
        self.assertEqual(self.balance(), Decimal('0'))

    def test_policy_is_read_on_every_exit(self):  # EDGE-05
        set_negative_stock(self.company, True)
        self.record('out', '1')
        set_negative_stock(self.company, False)
        with self.assertRaises(InsufficientStock):
            self.record('out', '1')


class InsufficientStockBodyTests(LedgerTestCase):
    def test_conflict_body_has_product_warehouse_requested_and_available(self):  # API-02
        exc = InsufficientStock('Sin saldo.', product_id=self.product.id, warehouse_id=self.warehouse.id,
                                requested=Decimal('5'), available=Decimal('2'))
        conflict = InsufficientStockConflict(exc, self.company.id)
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.detail['code'], 'insufficient_stock')
        self.assertEqual(conflict.detail['product'], {'id': str(self.product.id), 'name': 'Arroz'})
        self.assertEqual(conflict.detail['warehouse'], {'id': str(self.warehouse.id), 'name': 'Central'})
        self.assertEqual((conflict.detail['requested'], conflict.detail['available']), ('5.000', '2.000'))
        self.assertEqual(conflict.detail['unit'], {'abbreviation': 'kg'})

    def test_unknown_ids_do_not_break_the_body(self):
        exc = InsufficientStock('Sin saldo.', product_id=uuid4(), warehouse_id=uuid4(),
                                requested=Decimal('1'), available=Decimal('0'))
        conflict = InsufficientStockConflict(exc, self.company.id)
        self.assertEqual((conflict.detail['product']['name'], conflict.detail['warehouse']['name']), ('', ''))


class PolicySettingApiTests(APITestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        set_enabled(self.company, [*DEFAULT_ENABLED_KEYS, 'inventory'])
        authenticate(self.client, make_admin(self.company, username='ana', first_name='Ana', last_name='Pérez'))

    def test_setting_is_listed_with_blocked_default(self):  # AC-01
        item = self.client.get('/api/settings/inventory/').json()['settings'][0]
        self.assertEqual((item['key'], item['kind'], item['value'], item['default']),
                         (KEY, 'boolean', 'false', 'false'))
        self.assertTrue(item['label'] and 'entregas' in item['description'])

    def test_allowing_is_explicit_and_recorded_in_history(self):  # AC-01
        response = self.client.patch('/api/settings/inventory/', {'settings': {KEY: 'true'}}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(modularity.get_inventory_settings(self.company.id).allow_negative_stock)
        row = self.client.get('/api/settings/inventory/history/').json()['results'][0]
        self.assertEqual((row['old_value'], row['new_value'], row['changed_by']),
                         ('Bloqueado', 'Permitido', 'Ana Pérez'))

    def test_invalid_value_is_rejected_and_nothing_is_saved(self):  # EDGE-04
        response = self.client.patch('/api/settings/inventory/', {'settings': {KEY: 'si'}}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(modularity.get_inventory_settings(self.company.id).allow_negative_stock)

    def test_cannot_save_with_inventory_disabled(self):  # EDGE-03
        set_enabled(self.company, list(DEFAULT_ENABLED_KEYS))
        response = self.client.patch('/api/settings/inventory/', {'settings': {KEY: 'true'}}, format='json')
        self.assertEqual(response.status_code, 409)


class PolicyReadInsideLockTests(SimpleTestCase):
    """INV-03: la política se consulta con el bloqueo del almacén ya tomado (misma sección crítica que el saldo)."""

    def setUp(self):
        from contextlib import contextmanager

        from modules.inventory.application.movement_use_cases import RecordMovement, ReverseMovement
        from modules.inventory.application.movement_ports import ProductInfo
        from modules.inventory.domain.movement import MovementKind, StockMovement
        from modules.inventory.domain.warehouse import Warehouse

        test = self
        self.locked_now = False
        self.reads: list[bool] = []
        product_id, warehouse_id = uuid4(), uuid4()
        self.entry = StockMovement.record(
            product_id=product_id, warehouse_id=warehouse_id, kind=MovementKind.IN, quantity='5',
            occurred_at=__import__('django.utils.timezone', fromlist=['now']).now(), user_id=None, user_name='ana')

        class Repo:
            @contextmanager
            def locked(self, _warehouse_id):
                test.locked_now = True
                try:
                    yield
                finally:
                    test.locked_now = False

            def find_by_source(self, _movement):
                return None

            def balance(self, *_):
                return Decimal('0')

            def get(self, _movement_id):
                return test.entry

            def insert(self, movement):
                return movement

            def mark_reversed(self, _movement_id):
                return None

        class Warehouses:
            def get(self, _warehouse_id):
                return Warehouse(id=warehouse_id, name='Central') if 'id' in Warehouse.__dataclass_fields__ else None

        class Products:
            def get_products(self, ids):
                return {i: ProductInfo(id=i, name='Arroz', tracks_stock=True, unit_abbreviation='kg',
                                       allows_fractions=True) for i in ids}

        class Policy:
            def allow_negative_stock(self):
                test.reads.append(test.locked_now)
                return False

        self.product_id, self.warehouse_id = product_id, warehouse_id
        self.record = RecordMovement(Repo(), Warehouses(), Products(), Policy())
        self.reverse = ReverseMovement(Repo(), Policy())
        self.kind = MovementKind

    def test_record_reads_the_policy_while_locked(self):  # INV-03, EDGE-05
        with self.assertRaises(InsufficientStock):
            self.record.execute(product_id=self.product_id, warehouse_id=self.warehouse_id, kind=self.kind.OUT,
                                quantity='1', user_id=None, user_name='ana')
        self.assertEqual(self.reads, [True])

    def test_reverse_reads_the_policy_while_locked(self):  # INV-03
        with self.assertRaises(InsufficientStock):
            self.reverse.execute(self.entry.id, user_id=None, user_name='ana')
        self.assertEqual(self.reads, [True])
