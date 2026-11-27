"""INV-01: ledger de costo promedio móvil (dominio puro y fachada `costing.services`)."""
from decimal import Decimal
from uuid import uuid4

from django.db import transaction
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from modules.accounts.testing import make_company
from modules.costing import services as costing
from modules.costing.domain.cost import CostKind, CostUnavailable, line_cost, weighted_average
from modules.costing.domain.valuation import ValuationAdoption, parse_lines
from modules.costing.infrastructure.django.models import CostEventModel
from modules.costing.infrastructure.django.repositories import DjangoAdoptionRepository
from modules.inventory import services as inventory
from modules.inventory.tests.test_movements import make_product, make_warehouse

D = Decimal
RECEIPT = 'purchase_receipt'
ORDER = 'sales_order'


class CostDomainTests(SimpleTestCase):
    def test_weighted_average_mixes_balance_and_receipt(self):  # AC-03, INV-01
        self.assertEqual(weighted_average(D('10'), D('100'), D('10'), D('120')), D('110.000000'))
        self.assertEqual(weighted_average(D('3'), D('10'), D('1'), D('11')), D('10.250000'))

    def test_average_is_the_receipt_cost_without_a_positive_balance_or_known_average(self):  # EDGE
        self.assertEqual(weighted_average(D('0'), D('100'), D('5'), D('7')), D('7.000000'))
        self.assertEqual(weighted_average(D('-2'), D('100'), D('5'), D('7')), D('7.000000'))
        self.assertEqual(weighted_average(D('4'), None, D('5'), D('7')), D('7.000000'))

    def test_average_rounds_half_up_to_six_decimals(self):  # INV-01
        self.assertEqual(weighted_average(D('1'), D('1'), D('2'), D('2')), D('1.666667'))

    def test_line_cost_is_quantity_times_unit_cost_at_two_decimals(self):  # INV-01, INV-02
        self.assertEqual(line_cost(D('3'), D('33.333333')), D('100.00'))
        self.assertEqual(line_cost(D('0.5'), D('0.01')), D('0.01'))


class CostLedgerTestCase(TestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        self.other = make_company('Empresa B')
        self.warehouse = make_warehouse(self.company)
        self.product = make_product(self.company, 'Harina')

    def adopt(self, product=None, quantity='10', value='1000.00', zero=False, company=None):
        company = company or self.company
        product = product or self.product
        lines = parse_lines([{'product_id': product.id, 'reconciled_quantity': quantity, 'total_value': value,
                              'declared_zero': zero, 'source': None}])
        DjangoAdoptionRepository(company.id).save(
            ValuationAdoption.adopt(uuid4(), timezone.now(), None, 'ana', lines))

    def stock(self, quantity, product=None, kind='in'):
        inventory.record_movement(
            self.company.id, product_id=(product or self.product).id, warehouse_id=self.warehouse.id, kind=kind,
            quantity=D(quantity), user_id=None, user_name='ana')

    def receive(self, receipt, quantity, unit_cost, product=None):
        product = product or self.product
        self.stock(quantity, product)
        return costing.cost_receipt(self.company.id, source_type=RECEIPT, source_id=receipt,
                                    lines=[(product.id, D(quantity), D(unit_cost))])

    def out(self, order, quantity, product=None):
        return costing.cost_outputs(self.company.id, source_type=ORDER, source_id=order,
                                    lines=[((product or self.product).id, D(quantity))])


class CostOutputsTests(CostLedgerTestCase):
    def test_output_uses_the_adopted_unit_cost_and_not_the_sale_price(self):  # AC-01, INV-02
        self.stock('10')
        self.adopt()
        costed = self.out('o1', '1')
        self.assertEqual((costed.total, costed.lines[0].unit_cost, costed.lines[0].kind),
                         (D('100.00'), D('100.000000'), CostKind.OUT))

    def test_repeating_an_output_does_not_duplicate_events_or_change_the_total(self):  # AC-02, INV-03
        self.stock('10')
        self.adopt()
        first = self.out('o1', '2')
        self.receive('r1', '10', '200')  # el promedio cambia después de la primera salida
        again = self.out('o1', '2')
        self.assertEqual((again.total, first.total), (D('200.00'), D('200.00')))
        self.assertEqual(CostEventModel.objects.filter(kind='out').count(), 1)

    def test_output_does_not_change_the_average(self):  # INV-02
        self.stock('10')
        self.adopt()
        self.out('o1', '4')
        self.assertEqual(self.out('o2', '1').total, D('100.00'))

    def test_output_reversal_keeps_the_sale_cost_and_link_and_is_idempotent(self):  # AC-05 (devoluciones)
        self.stock('10')
        self.adopt()
        self.out('o1', '2')
        for _ in range(2):
            costing.reverse_output_cost(self.company.id, source_type=ORDER, source_id='o1')
        original = CostEventModel.objects.get(kind='out')
        reversal = CostEventModel.objects.get(kind='out_reversal')
        self.assertEqual((reversal.reverses_id, reversal.unit_cost, reversal.total_cost, reversal.quantity),
                         (original.id, D('100.000000'), D('200.00'), D('2.0000')))
        self.assertEqual(self.out('o2', '1').lines[0].unit_cost, D('100.000000'))

    def test_reversing_an_output_that_was_never_costed_does_nothing(self):  # AC-05
        costing.reverse_output_cost(self.company.id, source_type=ORDER, source_id='nunca')
        self.assertEqual(CostEventModel.objects.count(), 0)

    def test_without_an_adoption_there_is_no_cost(self):  # AC-05, INV-04
        self.stock('10')
        with self.assertRaises(CostUnavailable) as ctx:
            self.out('o1', '1')
        self.assertEqual(ctx.exception.reason, CostUnavailable.NOT_ADOPTED)
        self.assertFalse(costing.is_valued(self.company.id))
        self.assertEqual(CostEventModel.objects.count(), 0)

    def test_a_product_without_an_average_blocks_all_lines_and_writes_nothing(self):  # AC-05, INV-04
        self.adopt()
        other = make_product(self.company, 'Azúcar')
        with self.assertRaises(CostUnavailable) as ctx:
            costing.cost_outputs(self.company.id, source_type=ORDER, source_id='o1',
                                 lines=[(self.product.id, D('1')), (other.id, D('1'))])
        self.assertEqual((ctx.exception.reason, ctx.exception.product_ids),
                         (CostUnavailable.NO_AVERAGE, [other.id]))
        self.assertEqual(CostEventModel.objects.count(), 0)

    def test_a_declared_zero_cost_is_a_valid_zero_total(self):  # AC-09, INV-04
        self.adopt(value='0', zero=True)
        self.assertEqual(self.out('o1', '3').total, D('0.00'))

    def test_costs_are_isolated_per_company(self):  # AC-10, INV-06
        self.stock('10')
        self.adopt()
        other_product = make_product(self.other, 'Harina')
        self.adopt(other_product, value='500.00', company=self.other)
        other = costing.cost_outputs(self.other.id, source_type=ORDER, source_id='o1',
                                     lines=[(other_product.id, D('1'))])
        self.assertEqual(other.total, D('50.00'))
        self.assertEqual(self.out('o1', '1').total, D('100.00'))
        self.assertEqual(CostEventModel.objects.filter(company_id=self.other.id).count(), 1)


class CostReceiptTests(CostLedgerTestCase):
    def test_receipt_updates_the_weighted_average(self):  # AC-03
        self.stock('10')
        self.adopt()
        self.assertTrue(self.receive('r1', '10', '120'))
        self.assertEqual(self.out('o1', '1').lines[0].unit_cost, D('110.000000'))

    def test_without_an_adoption_the_receipt_is_ignored(self):  # AC-03
        self.assertFalse(self.receive('r1', '10', '120'))
        self.assertEqual(CostEventModel.objects.count(), 0)

    def test_retrying_a_receipt_does_not_move_the_average_again(self):  # AC-02, INV-03
        self.stock('10')
        self.adopt()
        self.receive('r1', '10', '120')
        costing.cost_receipt(self.company.id, source_type=RECEIPT, source_id='r1',
                             lines=[(self.product.id, D('10'), D('120'))])
        self.assertEqual(CostEventModel.objects.filter(kind='in').count(), 1)
        self.assertEqual(self.out('o1', '1').lines[0].unit_cost, D('110.000000'))

    def test_receipt_over_no_stock_sets_the_average_to_its_cost(self):  # EDGE
        other = make_product(self.company, 'Azúcar')
        self.adopt()
        self.receive('r1', '5', '7', other)
        self.assertEqual(self.out('o1', '2', other).total, D('14.00'))

    def test_reversal_keeps_the_original_cost_and_link_and_leaves_the_average(self):  # AC-07
        self.stock('10')
        self.adopt()
        self.receive('r1', '10', '120')
        costing.reverse_receipt_cost(self.company.id, source_type=RECEIPT, source_id='r1')
        costing.reverse_receipt_cost(self.company.id, source_type=RECEIPT, source_id='r1')  # idempotente
        original = CostEventModel.objects.get(kind='in')
        reversal = CostEventModel.objects.get(kind='in_reversal')
        self.assertEqual((reversal.reverses_id, reversal.unit_cost, reversal.total_cost, reversal.quantity),
                         (original.id, D('120.000000'), D('1200.00'), D('10.0000')))
        self.assertEqual(self.out('o1', '1').lines[0].unit_cost, D('110.000000'))

    def test_reversing_a_receipt_that_was_never_costed_does_nothing(self):  # AC-07
        costing.reverse_receipt_cost(self.company.id, source_type=RECEIPT, source_id='nunca')
        self.assertEqual(CostEventModel.objects.count(), 0)

    def test_failure_after_costing_rolls_back_the_event(self):  # AC-04
        self.stock('10')
        self.adopt()
        with self.assertRaises(RuntimeError), transaction.atomic():
            self.out('o1', '1')
            raise RuntimeError('fallo contable')
        self.assertEqual(CostEventModel.objects.count(), 0)


class CostIsolationTests(CostLedgerTestCase):
    def test_receipts_of_another_company_never_move_this_companys_average(self):  # AC-10, INV-06
        self.stock('10')
        self.adopt()
        other_product = make_product(self.other, 'Harina')
        self.adopt(other_product, value='500.00', company=self.other)
        other_warehouse = make_warehouse(self.other)
        for _ in range(2):  # 10 existentes valoradas + 10 recibidas
            inventory.record_movement(self.other.id, product_id=other_product.id, warehouse_id=other_warehouse.id,
                                      kind='in', quantity=D('10'), user_id=None, user_name='ana')
        costing.cost_receipt(self.other.id, source_type=RECEIPT, source_id='r1',
                             lines=[(other_product.id, D('10'), D('900'))])
        self.assertEqual(self.out('o1', '1').lines[0].unit_cost, D('100.000000'))
        self.assertEqual(costing.cost_outputs(self.other.id, source_type=ORDER, source_id='o1',
                                              lines=[(other_product.id, D('1'))]).lines[0].unit_cost,
                         D('475.000000'))

    def test_fractional_quantities_are_costed_with_two_decimals(self):  # EDGE
        self.stock('10')
        self.adopt()
        self.assertEqual(self.out('o1', '0.3333').total, D('33.33'))
