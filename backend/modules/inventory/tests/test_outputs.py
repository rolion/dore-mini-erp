"""PB-INT-002: salidas de un documento en lote (`record_outputs`): todas o ninguna, idempotentes."""
from decimal import Decimal

from modules.inventory import services as inventory
from modules.inventory.domain.exceptions import InsufficientStock, MovementConflict, MovementValidationError
from modules.inventory.infrastructure.django.models import StockMovementModel

from .policy import set_negative_stock
from .test_movements import LedgerTestCase, make_product


class RecordOutputsTests(LedgerTestCase):
    def setUp(self):
        super().setUp()
        self.other = make_product(self.company, 'Harina')

    def entry(self, product, quantity):
        inventory.record_movement(
            self.company.id, product_id=product.id, warehouse_id=self.warehouse.id, kind='in',
            quantity=Decimal(quantity), user_id=None, user_name='ana')

    def outputs(self, lines, source_id='o1', warehouse=None):
        return inventory.record_outputs(
            self.company.id, warehouse_id=(warehouse or self.warehouse).id, lines=lines, source_type='sales_order',
            source_id=source_id, user_id=None, user_name='ana', reference='P-1')

    def out_count(self):
        return StockMovementModel.objects.filter(kind='out').count()

    def test_registers_every_line_with_the_line_identity(self):  # AC-01, AC-10
        self.entry(self.product, '5')
        self.entry(self.other, '2')
        results = self.outputs([(self.product.id, Decimal('4')), (self.other.id, Decimal('2'))])
        self.assertEqual([created for _, created in results], [True, True])
        self.assertEqual(
            sorted((m.source_line, m.reference, m.quantity) for m in StockMovementModel.objects.filter(kind='out')),
            sorted([(str(self.product.id), 'P-1', Decimal('4')), (str(self.other.id), 'P-1', Decimal('2'))]))
        self.assertEqual(self.balance(), Decimal('1'))

    def test_a_short_line_registers_nothing_and_all_short_lines_are_reported(self):  # AC-02, AC-05
        self.entry(self.product, '5')
        with self.assertRaises(InsufficientStock) as ctx:
            self.outputs([(self.product.id, Decimal('4')), (self.other.id, Decimal('3'))])
        self.assertEqual([(s.product_id, s.requested, s.available) for s in ctx.exception.shortages],
                         [(self.other.id, Decimal('3'), Decimal('0'))])
        self.assertEqual(self.out_count(), 0)
        with self.assertRaises(InsufficientStock) as ctx:
            self.outputs([(self.product.id, Decimal('9')), (self.other.id, Decimal('3'))])
        self.assertEqual(len(ctx.exception.shortages), 2)
        self.assertEqual(self.out_count(), 0)

    def test_allowed_policy_goes_negative(self):  # AC-03
        set_negative_stock(self.company, True)
        self.entry(self.product, '5')
        self.outputs([(self.product.id, Decimal('4'))], 'o1')
        self.outputs([(self.product.id, Decimal('4'))], 'o2')
        self.assertEqual(self.balance(), Decimal('-3'))

    def test_repeating_the_operation_returns_the_existing_exits(self):  # AC-04
        self.entry(self.product, '5')
        first = self.outputs([(self.product.id, Decimal('4'))])
        again = self.outputs([(self.product.id, Decimal('4'))])
        self.assertEqual([c for _, c in again], [False])
        self.assertEqual(again[0][0].id, first[0][0].id)
        self.assertEqual((self.out_count(), self.balance()), (1, Decimal('1')))

    def test_repeating_with_another_quantity_is_a_conflict(self):  # AC-04
        self.entry(self.product, '9')
        self.outputs([(self.product.id, Decimal('4'))])
        with self.assertRaises(MovementConflict) as ctx:
            self.outputs([(self.product.id, Decimal('5'))])
        self.assertEqual(ctx.exception.code, 'source_operation_mismatch')

    def test_invalid_lines_register_nothing(self):  # AC-05, AC-07
        self.entry(self.product, '5')
        free = make_product(self.company, 'Servicio', tracks_stock=False)
        with self.assertRaises(MovementValidationError):
            self.outputs([(self.product.id, Decimal('1')), (free.id, Decimal('1'))])
        self.warehouse.active = False
        self.warehouse.save()
        with self.assertRaises(MovementValidationError):
            self.outputs([(self.product.id, Decimal('1'))])
        self.assertEqual(self.out_count(), 0)

    def test_facade_reads(self):  # AC-11, AC-12
        self.entry(self.product, '5')
        self.outputs([(self.product.id, Decimal('4'))])
        balances = inventory.get_balances(self.company.id, self.warehouse.id, [self.product.id, self.other.id])
        self.assertEqual(balances, {self.product.id: Decimal('1'), self.other.id: Decimal('0')})
        self.assertEqual(set(inventory.get_stock_products(self.company.id, [self.product.id])), {self.product.id})
        moved = inventory.list_movements_for_source(self.company.id, 'sales_order', 'o1')
        self.assertEqual([(m.product_name, m.warehouse_name, m.quantity, m.reference) for m in moved],
                         [(self.product.name, self.warehouse.name, Decimal('4'), 'P-1')])
        self.assertEqual(inventory.list_movements_for_source(self.company.id, 'sales_order', 'zz'), [])
        self.assertFalse(inventory.allow_negative_stock(self.company.id))
