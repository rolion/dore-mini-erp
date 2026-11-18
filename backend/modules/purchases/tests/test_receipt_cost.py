"""INV-01: la recepción de una compra alimenta el costo promedio de Costeo sin generar asiento."""
from decimal import Decimal
from uuid import uuid4

from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from modules.accounting.infrastructure.django.models import JournalEntryModel
from modules.accounting.tests.test_concurrency import _run_together
from modules.accounts.testing import make_company
from modules.costing.domain.valuation import ValuationAdoption, parse_lines
from modules.costing.infrastructure.django.models import CostEventModel
from modules.costing.infrastructure.django.repositories import DjangoAdoptionRepository
from modules.inventory import services as inventory
from modules.inventory.tests.test_movements import make_product, make_warehouse
from modules.purchases.application.ports import Actor
from modules.purchases.domain.exceptions import StockShortage
from modules.purchases.infrastructure.adapters import StockEntryAdapter
from modules.sales.tests.test_payment_ledger import enable

D = Decimal


class ReceiptCostTests(TestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        enable(self.company, 'inventory', 'costing', 'purchases', 'accounting')
        self.warehouse = make_warehouse(self.company)
        self.product = make_product(self.company, 'Harina')
        self.adapter = StockEntryAdapter(self.company.id)
        self.actor = Actor(None, 'ana')

    def adopt(self):
        inventory.record_movement(self.company.id, product_id=self.product.id, warehouse_id=self.warehouse.id,
                                  kind='in', quantity=D('10'), user_id=None, user_name='ana')
        lines = parse_lines([{'product_id': self.product.id, 'reconciled_quantity': '10',
                              'total_value': '1000.00', 'declared_zero': False, 'source': None}])
        DjangoAdoptionRepository(self.company.id).save(
            ValuationAdoption.adopt(uuid4(), timezone.now(), None, 'ana', lines))

    def receive(self, receipt_id, unit_cost='120.00'):
        self.adapter.register_entries(self.warehouse.id, [(self.product.id, D('10'))], receipt_id, 'REC-1',
                                      self.actor, {self.product.id: D(unit_cost)})

    def test_receiving_updates_the_average_and_creates_no_journal_entry(self):  # AC-03, INV-05
        self.adopt()
        receipt = uuid4()
        self.receive(receipt)
        event = CostEventModel.objects.get(kind='in')
        self.assertEqual((event.source_id, event.unit_cost, event.average_after),
                         (str(receipt), D('120.000000'), D('110.000000')))
        self.assertEqual(JournalEntryModel.objects.filter(company_id=self.company.id).count(), 0)

    def test_receiving_without_an_adopted_valuation_only_moves_stock(self):  # AC-03
        self.receive(uuid4())
        self.assertEqual((CostEventModel.objects.count(),
                          inventory.get_balance(self.company.id, self.product.id, self.warehouse.id)),
                         (0, D('10')))

    def test_reversing_a_receipt_whose_stock_was_already_sold_is_rejected_without_a_reversal(self):  # AC-07
        self.adopt()
        receipt = uuid4()
        self.receive(receipt)
        inventory.record_movement(self.company.id, product_id=self.product.id, warehouse_id=self.warehouse.id,
                                  kind='out', quantity=D('15'), user_id=None, user_name='ana')
        with self.assertRaises(StockShortage):
            self.adapter.reverse_entries(receipt, 'Error de carga', self.actor)
        self.assertEqual(CostEventModel.objects.filter(kind='in_reversal').count(), 0)

    def test_reversing_the_receipt_links_a_reversal_at_the_original_cost(self):  # AC-07
        self.adopt()
        receipt = uuid4()
        self.receive(receipt)
        self.adapter.reverse_entries(receipt, 'Error de carga', self.actor)
        original = CostEventModel.objects.get(kind='in')
        reversal = CostEventModel.objects.get(kind='in_reversal')
        self.assertEqual((reversal.reverses_id, reversal.unit_cost), (original.id, original.unit_cost))
        self.assertEqual(JournalEntryModel.objects.filter(company_id=self.company.id).count(), 0)


class ConcurrentReceiptCostTests(TransactionTestCase):
    """REV-01: recepciones simultáneas de la misma empresa en almacenes distintos no se bloquean entre sí."""

    def setUp(self):
        self.company = make_company('Empresa A')
        enable(self.company, 'inventory', 'costing', 'purchases')
        self.pairs = []
        for name in ('Harina', 'Azúcar'):
            self.pairs.append((make_warehouse(self.company, f'Almacén {name}'), make_product(self.company, name)))
        DjangoAdoptionRepository(self.company.id).save(ValuationAdoption.adopt(
            uuid4(), timezone.now(), None, 'ana', parse_lines([{
                'product_id': product.id, 'reconciled_quantity': '10', 'total_value': '100.00',
                'declared_zero': False, 'source': None} for _, product in self.pairs])))
        for warehouse, product in self.pairs:
            inventory.record_movement(self.company.id, product_id=product.id, warehouse_id=warehouse.id, kind='in',
                                      quantity=D('10'), user_id=None, user_name='ana')

    def receive(self, index):
        warehouse, product = self.pairs[index]
        return lambda: StockEntryAdapter(self.company.id).register_entries(
            warehouse.id, [(product.id, D('10'))], uuid4(), f'REC-{index}', Actor(None, 'ana'),
            {product.id: D('20.00')})

    def test_two_receipts_in_different_warehouses_both_complete_with_the_right_average(self):  # REV-01
        self.assertEqual(_run_together(self.receive(0), self.receive(1)), [None, None])
        self.assertEqual(sorted(CostEventModel.objects.filter(kind='in').values_list('average_after', flat=True)),
                         [D('15.000000'), D('15.000000')])
