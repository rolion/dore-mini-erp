"""Devolución total con reversión de stock, costo y asientos (API + base de datos real)."""
from decimal import Decimal
from uuid import uuid4

from django.utils import timezone

from modules.accounting import services as accounting
from modules.accounting.infrastructure.django.models import FiscalPeriodModel
from modules.accounting.tests.journal_support import make_account
from modules.accounts.testing import authenticate, make_admin, make_company
from modules.costing.domain.valuation import ValuationAdoption, parse_lines
from modules.costing.infrastructure.django.models import CostEventModel
from modules.costing.infrastructure.django.repositories import DjangoAdoptionRepository
from modules.inventory import services as inventory
from modules.inventory.tests.test_movements import make_product, make_warehouse
from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
from modules.modularity.tests.test_enforcement import set_enabled
from modules.sales.tests.test_api import SalesApiTestCase, url
from modules.sales.tests.test_sales_posting import Books


class ReturnApiTestCase(SalesApiTestCase):
    def setUp(self):
        super().setUp()
        set_enabled(self.company, DEFAULT_ENABLED_KEYS + ('inventory', 'accounting', 'costing'))
        self.books = Books(self.company)
        accounting.set_role_account(
            self.company.id, 'INVENTORY', make_account(self.company.id, 'Inventario', 'ASSET', '113001').id)
        accounting.set_role_account(
            self.company.id, 'COST_OF_SALES', make_account(self.company.id, 'Costo de ventas', 'COST', '510001').id)
        self.warehouse = make_warehouse(self.company, 'Central')
        self.bags = make_product(self.company, 'Bolsas', allows_fractions=False, abbreviation='u')
        inventory.record_movement(self.company.id, product_id=self.bags.id, warehouse_id=self.warehouse.id,
                                  kind='in', quantity=Decimal('10'), user_id=None, user_name='ana')
        DjangoAdoptionRepository(self.company.id).save(ValuationAdoption.adopt(
            uuid4(), timezone.now(), None, 'ana', parse_lines([{
                'product_id': self.bags.id, 'reconciled_quantity': '10', 'total_value': '50.00',
                'declared_zero': False, 'source': None}])))

    def balance(self):
        return inventory.get_balance(self.company.id, self.bags.id, self.warehouse.id)

    def delivered(self, pay=None):
        order = self.create()
        self.add_item(order, self.bags, 2)
        self.act(order, 'prepare')
        if pay:
            self.pay(order, pay)
        self.act(order, 'ready')
        self.act(order, 'deliver', {'warehouse_id': str(self.warehouse.id)})
        return order

    def snapshot(self):
        return (self.balance(), self.books.journal().count(), CostEventModel.objects.count())


class ReturnTests(ReturnApiTestCase):
    def test_return_restores_stock_cost_and_entries_and_keeps_the_originals(self):  # AC-03, AC-04, AC-05, AC-09
        order = self.delivered()
        self.assertEqual(self.balance(), Decimal('8'))
        body = self.act(order, 'return', {'reason': 'Defectuoso'})
        self.assertEqual((body['status'], body['return_reason'], body['returned_by_name'], body['allowed_transitions']),
                         ('RETURNED', 'Defectuoso', 'ana', []))
        self.assertEqual(self.balance(), Decimal('10'))
        self.assertEqual(CostEventModel.objects.filter(kind='out_reversal').count(), 1)
        entries = body['reversal']['entries']
        self.assertEqual(sorted(e['event'] for e in entries), ['INVENTORY_SALE_COST', 'SALE_DELIVERY'])
        self.assertTrue(all(e['reversed_by_id'] for e in entries))
        self.assertEqual(len(body['items']), 1)
        self.assertTrue(all(m['reversed_by_id'] for m in body['reversal']['movements']))
        self.assertEqual(self.books.journal().count(), 4)  # 2 originales + 2 contrasientos

    def test_return_with_payments_requires_the_refund_and_counterposts_them(self):  # AC-02
        order = self.delivered(pay='20.00')
        before = self.snapshot()
        rejected = self.act(order, 'return', {'reason': 'Defectuoso'}, expected_status=409)
        self.assertEqual((rejected['code'], self.snapshot()), ('refund_acknowledgement_required', before))
        body = self.act(order, 'return', {'reason': 'Defectuoso', 'refund_acknowledged': True})
        self.assertEqual((body['status'], body['payment_status']), ('RETURNED', 'REFUNDED'))
        self.assertTrue(all(e['reversed_by_id'] for e in body['reversal']['entries']))

    def test_a_closed_period_rejects_the_return_and_changes_nothing(self):  # AC-04, AC-06
        order = self.delivered()
        before = self.snapshot()
        FiscalPeriodModel.objects.filter(company_id=self.company.id).update(status='CLOSED')
        body = self.act(order, 'return', {'reason': 'Defectuoso'}, expected_status=409)
        self.assertEqual(body['code'], 'fiscal_period_unavailable')
        self.assertEqual((self.snapshot(), self.get(order)['status']), (before, 'DELIVERED'))

    def test_repeating_the_return_does_not_duplicate_anything(self):  # AC-07
        order = self.delivered()
        self.act(order, 'return', {'reason': 'Defectuoso'})
        after = self.snapshot()
        body = self.act(order, 'return', {'reason': 'Defectuoso'}, expected_status=409)
        self.assertEqual((body['code'], self.snapshot()), ('invalid_transition', after))

    def test_the_reason_is_required_and_only_delivered_orders_can_be_returned(self):  # INV-01
        order = self.delivered()
        self.act(order, 'return', {'reason': ' '}, expected_status=400)
        open_order = self.create()
        self.add_item(open_order, self.bags, 1)
        body = self.act(open_order, 'return', {'reason': 'x'}, expected_status=409)
        self.assertEqual(body['code'], 'invalid_transition')

    def test_preview_lists_the_effects_and_writes_nothing(self):  # AC-11
        order = self.delivered(pay='20.00')
        before = self.snapshot()
        response = self.client.get(url(order['id'], 'return-preview/'))
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual((data['requires_refund_acknowledgement'], data['stock']['warehouse']['name'],
                          data['stock']['lines'][0]['quantity'], len(data['payments'])),
                         (True, 'Central', '2.0000', 1))
        self.assertEqual({e['event'] for e in data['entries']}, {'SALE_DELIVERY', 'INVENTORY_SALE_COST',
                                                                 'SALE_ADVANCE'})
        self.assertEqual((self.snapshot(), self.get(order)['status']), (before, 'DELIVERED'))

    def test_returned_sales_do_not_count_as_valid_sales(self):  # AC-10
        from modules.sales import services as sales_services
        order = self.delivered()
        today = timezone.localdate()
        self.assertEqual(sales_services.get_sales_totals(self.company.id, today, today).orders_count, 1)
        self.act(order, 'return', {'reason': 'Defectuoso'})
        self.assertEqual(sales_services.get_sales_totals(self.company.id, today, today).orders_count, 0)

    def test_another_company_cannot_return_or_preview_the_order(self):  # AC-08
        order = self.delivered()
        authenticate(self.client, make_admin(make_company('Empresa B'), username='beto'))
        self.assertEqual(self.client.post(url(order['id'], 'return/'), {'reason': 'x'}, format='json').status_code, 404)
        self.assertEqual(self.client.get(url(order['id'], 'return-preview/')).status_code, 404)


class CancelWithoutOutputTests(ReturnApiTestCase):
    def test_cancelling_an_order_without_a_stock_output_leaves_the_stock_intact(self):  # AC-01
        order = self.create()
        self.add_item(order, self.bags, 2)
        self.act(order, 'prepare')
        body = self.act(order, 'cancel', {'reason': 'Ya no lo quiere'})
        self.assertEqual((body['status'], body['cancelled_by_name'], self.balance()),
                         ('CANCELLED', 'ana', Decimal('10')))
