"""INV-01: al entregar se valoriza la salida al costo promedio y se asienta Costo de ventas / Inventario."""
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from modules.accounting import services as accounting
from modules.accounting.tests.journal_support import make_account
from modules.costing.domain.valuation import ValuationAdoption, parse_lines
from modules.costing.infrastructure.django.models import CostEventModel
from modules.costing.infrastructure.django.repositories import DjangoAdoptionRepository
from modules.inventory import services as inventory
from modules.inventory.tests.test_movements import make_product, make_warehouse
from modules.sales.application.ports import Actor
from modules.sales.infrastructure.adapters import DeliveryCostingAdapter
from modules.sales.tests.test_payment_ledger import enable
from modules.sales.tests.test_sales_posting import PostingApiBase

D = Decimal
COST = 'INVENTORY_SALE_COST'


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
