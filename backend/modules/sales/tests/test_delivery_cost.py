"""INV-01: al entregar se valoriza la salida al costo promedio y se asienta Costo de ventas / Inventario."""
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from django.db import transaction
from django.test import TransactionTestCase
from django.utils import timezone

from modules.accounting import services as accounting
from modules.accounting.tests.journal_support import make_account
from modules.accounting.tests.test_concurrency import _run_together
from modules.accounts.testing import make_company
from modules.costing.domain.valuation import ValuationAdoption, parse_lines
from modules.costing.infrastructure.django.models import CostEventModel
from modules.costing.infrastructure.django.repositories import DjangoAdoptionRepository
from modules.inventory import services as inventory
from modules.inventory.tests.test_movements import make_product, make_warehouse
from modules.sales.application.ports import Actor
from modules.sales.infrastructure.adapters import DeliveryCostingAdapter, StockOutputAdapter
from modules.sales.tests.test_payment_ledger import enable
from modules.sales.tests.test_sales_posting import PostingApiBase

D = Decimal
COST = 'INVENTORY_SALE_COST'
YESTERDAY = timezone.localdate() - timedelta(days=1)


class DeliveryCostTestCase(PostingApiBase):
    def setUp(self):
        super().setUp()
        enable(self.company, 'inventory', 'costing')
        self.warehouse = make_warehouse(self.company)
        self.flour = make_product(self.company, 'Harina')
        self.flour.sale_price = D('150.00')
        self.flour.save()
        self.inventory_account = make_account(self.company.id, 'Inventario', 'ASSET', '113001')
        self.cost_account = make_account(self.company.id, 'Costo de ventas', 'COST', '510001')
        accounting.set_role_account(self.company.id, 'INVENTORY', self.inventory_account.id)
        accounting.set_role_account(self.company.id, 'COST_OF_SALES', self.cost_account.id)
        inventory.record_movement(self.company.id, product_id=self.flour.id, warehouse_id=self.warehouse.id,
                                  kind='in', quantity=D('10'), user_id=None, user_name='ana')

    def adopt(self, value='1000.00', zero=False):
        lines = parse_lines([{'product_id': self.flour.id, 'reconciled_quantity': '10', 'total_value': value,
                              'declared_zero': zero, 'source': None}])
        DjangoAdoptionRepository(self.company.id).save(
            ValuationAdoption.adopt(uuid4(), timezone.now(), None, 'ana', lines))

    def stock_order(self, quantity=1):
        order = self.create()
        self.add_item(order, self.flour, quantity)
        self.act(order, 'prepare')
        self.act(order, 'ready')
        return order

    def deliver_stock(self, order, expected_status=200):
        return self.act(order, 'deliver', {'warehouse_id': str(self.warehouse.id)}, expected_status)

    def balance(self):
        return inventory.get_balance(self.company.id, self.flour.id, self.warehouse.id)


class DeliveryCostPostingTests(DeliveryCostTestCase):
    def test_selling_at_150_with_cost_100_posts_cost_100_against_inventory(self):  # AC-01
        self.adopt()
        order = self.stock_order()
        self.deliver_stock(order)
        order_id = uuid_of(order)
        self.assertEqual(self.books.lines(COST, order_id), sorted([
            (self.cost_account.id, D('100.00'), D('0.00')), (self.inventory_account.id, D('0.00'), D('100.00'))]))
        self.assertEqual(self.books.net(self.inventory_account), (D('0.00'), D('100.00')))
        # el ingreso 150 sigue siendo el asiento de VEN-01
        self.assertEqual(self.books.net(self.books.ingresos), (D('0.00'), D('150.00')))
        self.assertEqual(self.balance(), D('9'))

    def test_the_cost_uses_the_updated_average_for_several_units(self):  # AC-01
        self.adopt()
        order = self.stock_order(3)
        self.deliver_stock(order)
        self.assertEqual(self.books.net(self.cost_account), (D('300.00'), D('0.00')))

    def test_retrying_the_posting_does_not_duplicate_cost_stock_or_entry(self):  # AC-02
        self.adopt()
        order = self.stock_order()
        self.deliver_stock(order)
        self.deliver_stock(order, 409)  # ya entregado
        delivered = SimpleNamespace(id=uuid_of(order), code=order['code'], delivered_date=timezone.localdate())
        with transaction.atomic():
            DeliveryCostingAdapter(self.company.id).cost_delivery(
                delivered, [(self.flour.id, D('1'))], Actor(None, 'ana'))
        self.assertEqual((self.books.journal(COST).count(), CostEventModel.objects.filter(kind='out').count(),
                          self.balance()), (1, 1, D('9')))

    def test_a_missing_account_configuration_blocks_the_delivery_and_leaves_no_trace(self):  # AC-04, AC-05
        self.adopt()
        from modules.accounting.infrastructure.django.models import PostingAccountModel
        PostingAccountModel.objects.filter(company_id=self.company.id, scope='ROLE', key='COST_OF_SALES').delete()
        order = self.stock_order()
        body = self.deliver_stock(order, 409)
        self.assertEqual(body['code'], 'posting_configuration_missing')
        self.assertEqual((self.balance(), CostEventModel.objects.count(), self.books.journal(COST).count(),
                          self.get(order)['status']), (D('10'), 0, 0, 'READY'))

    def test_a_closed_fiscal_period_blocks_and_rolls_back_everything(self):  # AC-04
        self.adopt()
        order = self.stock_order()
        from modules.accounting.infrastructure.django.models import FiscalPeriodModel
        FiscalPeriodModel.objects.filter(company_id=self.company.id).update(status='CLOSED')
        self.deliver_stock(order, 409)
        self.assertEqual((self.balance(), CostEventModel.objects.count(), self.get(order)['status']),
                         (D('10'), 0, 'READY'))

    def test_without_an_adopted_valuation_the_delivery_is_blocked_with_an_actionable_message(self):  # AC-05
        order = self.stock_order()
        body = self.deliver_stock(order, 409)
        self.assertEqual(body['code'], 'inventory_cost_unavailable')
        self.assertIn('Costeo', body['detail'])
        self.assertEqual((self.balance(), self.books.journal(COST).count()), (D('10'), 0))

    def test_with_costing_disabled_the_delivery_is_blocked_under_accounting_coverage(self):  # AC-05
        from modules.modularity.infrastructure.django.models import CompanyModuleModel
        CompanyModuleModel.objects.filter(company_id=self.company.id, module_key='costing').delete()
        order = self.stock_order()
        self.assertEqual(self.deliver_stock(order, 409)['code'], 'inventory_cost_unavailable')

    def test_a_declared_zero_cost_records_the_event_but_posts_no_entry(self):  # AC-09
        self.adopt(value='0', zero=True)
        order = self.stock_order()
        self.deliver_stock(order)
        self.assertEqual((self.books.journal(COST).count(), CostEventModel.objects.filter(kind='out').count()),
                         (0, 1))

    def test_non_stock_products_need_no_cost_or_configuration(self):  # AC-08
        order = self.ready('40.00')
        self.deliver(order)
        self.assertEqual((self.books.journal(COST).count(), CostEventModel.objects.count()), (0, 0))


class DeliveryCostEdgeTests(DeliveryCostTestCase):
    def test_insufficient_stock_leaves_no_cost_event_or_entry(self):  # AC-06
        self.adopt()
        order = self.stock_order(11)
        self.assertEqual(self.deliver_stock(order, 409)['code'], 'insufficient_stock')
        self.assertEqual((CostEventModel.objects.count(), self.books.journal(COST).count(), self.balance()),
                         (0, 0, D('10')))

    def test_a_delivery_before_the_cutoff_dates_the_cost_on_that_day_and_posts_nothing(self):  # EDGE (REV-03)
        self.adopt()
        past = SimpleNamespace(id=uuid4(), code='P-PAST', delivered_date=YESTERDAY)
        with transaction.atomic():
            DeliveryCostingAdapter(self.company.id).cost_delivery(
                past, [(self.flour.id, D('1'))], Actor(None, 'ana'))
        event = CostEventModel.objects.get(kind='out')
        self.assertEqual((self.books.journal(COST).count(), timezone.localtime(event.occurred_at).date()),
                         (0, YESTERDAY))

    def test_one_product_without_cost_blocks_the_whole_order_and_names_it(self):  # INV-04, AC-05
        self.adopt()
        sugar = make_product(self.company, 'Azúcar')
        inventory.record_movement(self.company.id, product_id=sugar.id, warehouse_id=self.warehouse.id, kind='in',
                                  quantity=D('5'), user_id=None, user_name='ana')
        order = self.create()
        self.add_item(order, self.flour, 1)
        self.add_item(order, sugar, 1)
        self.act(order, 'prepare')
        self.act(order, 'ready')
        body = self.deliver_stock(order, 409)
        self.assertEqual(body['code'], 'inventory_cost_unavailable')
        self.assertIn('Azúcar', body['detail'])
        self.assertEqual((self.balance(), CostEventModel.objects.count(), self.get(order)['status']),
                         (D('10'), 0, 'READY'))


class DeliveryCostWithoutCoverageTests(DeliveryCostTestCase):
    def setUp(self):
        super().setUp()
        from modules.modularity.infrastructure.django.models import CompanyModuleModel
        CompanyModuleModel.objects.filter(company_id=self.company.id, module_key='accounting').delete()

    def test_without_accounting_the_delivery_works_as_before_and_records_cost_when_available(self):  # AC-08
        self.adopt()
        order = self.stock_order()
        self.deliver_stock(order)
        self.assertEqual((self.books.journal(COST).count(), CostEventModel.objects.filter(kind='out').count(),
                          self.balance()), (0, 1, D('9')))

    def test_without_accounting_and_without_cost_the_delivery_is_not_blocked(self):  # AC-08
        order = self.stock_order()
        self.deliver_stock(order)
        self.assertEqual((CostEventModel.objects.count(), self.balance()), (0, D('9')))

    def test_before_the_cutoff_nothing_is_posted(self):  # AC-08
        enable(self.company, 'accounting')
        from modules.accounting.infrastructure.django.models import SettingsModel
        SettingsModel.objects.update_or_create(company_id=self.company.id,
                                               defaults={'cutoff_date': timezone.localdate() + timedelta(days=30)})
        self.adopt()
        order = self.stock_order()
        self.deliver_stock(order)
        self.assertEqual(self.books.journal(COST).count(), 0)


def uuid_of(order):
    from uuid import UUID
    return UUID(order['id'])


class ConcurrentDeliveryCostTests(TransactionTestCase):
    """REV-01: entregas simultáneas de la misma empresa en almacenes distintos no se bloquean entre sí."""

    def setUp(self):
        self.company = make_company('Empresa A')
        enable(self.company, 'inventory', 'costing', 'sales')
        self.products, self.warehouses = [], []
        for name in ('Harina', 'Azúcar'):
            warehouse = make_warehouse(self.company, f'Almacén {name}')
            product = make_product(self.company, name)
            inventory.record_movement(self.company.id, product_id=product.id, warehouse_id=warehouse.id, kind='in',
                                      quantity=D('10'), user_id=None, user_name='ana')
            self.products.append(product)
            self.warehouses.append(warehouse)
        lines = parse_lines([{'product_id': p.id, 'reconciled_quantity': '10', 'total_value': '100.00',
                              'declared_zero': False, 'source': None} for p in self.products])
        DjangoAdoptionRepository(self.company.id).save(
            ValuationAdoption.adopt(uuid4(), timezone.now(), None, 'ana', lines))

    def deliver(self, index):
        def job():
            order = SimpleNamespace(id=uuid4(), code=f'P-{index}', delivered_date=timezone.localdate())
            actor = Actor(None, 'ana')
            line = [(self.products[index].id, D('1'))]
            StockOutputAdapter(self.company.id).register_outputs(
                self.warehouses[index].id, line, order.id, order.code, actor)
            DeliveryCostingAdapter(self.company.id).cost_delivery(order, line, actor)
        return job

    def test_two_deliveries_in_different_warehouses_both_complete(self):  # REV-01
        self.assertEqual(_run_together(self.deliver(0), self.deliver(1)), [None, None])
        self.assertEqual(CostEventModel.objects.filter(kind='out').count(), 2)
        self.assertEqual(sum(inventory.get_balance(self.company.id, p.id, w.id)
                             for p, w in zip(self.products, self.warehouses)), D('18'))
