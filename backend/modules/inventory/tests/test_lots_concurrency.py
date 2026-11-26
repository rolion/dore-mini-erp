"""Carreras de lotes (AC-03, AC-07, INV-01): PostgreSQL real e hilos."""
from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal

from django.test import TransactionTestCase

from modules.accounting.tests.test_concurrency import _run_together
from modules.accounts.testing import make_company
from modules.catalog.infrastructure.django.models import ProductModel, UnitModel
from modules.inventory import services as inventory
from modules.inventory.domain.exceptions import InsufficientStock
from modules.inventory.infrastructure.django.models import StockLotModel, WarehouseModel
from modules.sales.tests.periods import open_test_period

RACERS = 6
WHEN = datetime(2026, 11, 26, 15, 0, tzinfo=dt_timezone.utc)


class LotConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        open_test_period(self.company.id, start=date(2026, 1, 1), end=date(2026, 12, 31))
        unit = UnitModel.objects.create(company_id=self.company.id, name='Unidad', abbreviation='u',
                                        allows_fractions=False)
        self.product = ProductModel.objects.create(
            company_id=self.company.id, name='Cuñapé', sale_price=Decimal('1'), tracks_stock=True, base_unit=unit).id
        self.warehouse = WarehouseModel.objects.create(company_id=self.company.id, name='Central').id

    def create(self, index):
        def job():
            inventory.create_lot(
                self.company.id, product_id=self.product, warehouse_id=self.warehouse, quantity=Decimal('10'),
                source_type='production_order', source_id=f'OP-{index}', user_id=None, user_name='ana',
                occurred_at=WHEN)
        return job

    def test_simultaneous_lots_get_distinct_consecutive_numbers(self):  # AC-03
        outcomes = _run_together(*[self.create(i) for i in range(RACERS)])
        self.assertEqual(outcomes, [None] * RACERS)
        numbers = sorted(StockLotModel.objects.values_list('number', flat=True))
        self.assertEqual(numbers, list(range(1, RACERS + 1)))

    def test_the_same_source_created_at_once_makes_one_lot(self):  # AC-02
        _run_together(self.create(1), self.create(1))
        self.assertEqual(StockLotModel.objects.count(), 1)
        self.create(2)()  # el siguiente lote es el número 2: la carrera no gastó ningún número
        self.assertEqual(sorted(StockLotModel.objects.values_list('number', flat=True)), [1, 2])

    def test_two_outputs_of_the_same_lot_cannot_both_take_the_last_units(self):  # AC-07, INV-01
        lot = inventory.create_lot(
            self.company.id, product_id=self.product, warehouse_id=self.warehouse, quantity=Decimal('10'),
            source_type='production_order', source_id='OP-0', user_id=None, user_name='ana', occurred_at=WHEN)[0]
        inventory.release_lot(self.company.id, lot.id, user_id=None, user_name='ana')

        def take(index):
            def job():
                inventory.record_movement(
                    self.company.id, product_id=self.product, warehouse_id=self.warehouse, kind='out',
                    quantity=Decimal('6'), user_id=None, user_name='ana', source_type='sales_order',
                    source_id=f'P-{index}', lot_id=lot.id)
            return job

        outcomes = _run_together(take(1), take(2), take(3))
        failures = [o for o in outcomes if o is not None]
        self.assertEqual(len(failures), 2)
        self.assertTrue(all(isinstance(f, InsufficientStock) for f in failures))
        self.assertEqual(inventory.get_lot(self.company.id, lot.id).physical_quantity, Decimal('4'))
