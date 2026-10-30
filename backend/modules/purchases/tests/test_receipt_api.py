"""PB-COM-004: recepciones parciales o completas, con y sin Inventario (BD real)."""
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from django.utils import timezone
from rest_framework.test import APIClient

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.expenses.infrastructure.django.models import ExpenseModel
from modules.inventory import services as inventory
from modules.inventory.infrastructure.django.models import StockMovementModel, WarehouseModel
from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
from modules.modularity.tests.test_enforcement import set_enabled
from modules.purchases.infrastructure.django.models import PurchaseModel, ReceiptItemModel, ReceiptModel
from modules.purchases.tests.test_purchase_api import LIST_URL, PurchaseApiTestCase, detail_url

ENABLED = DEFAULT_ENABLED_KEYS + ('purchases', 'inventory')


def purchase_url(purchase_id, suffix):
    return f'{LIST_URL}{purchase_id}/{suffix}'


class ReceiptApiTestCase(PurchaseApiTestCase):
    def setUp(self):
        super().setUp()
        self.warehouse = WarehouseModel.objects.create(company_id=self.company.id, name='Central', is_default=True)

    def inventory_on(self):
        set_enabled(self.company, ENABLED)

    def confirmed_purchase(self, items=None):
        items = items or [(self.flour, '10', '5.00'), (self.bag, '4', '2.00')]
        created = self.client.post(LIST_URL, {
            'supplier_id': str(self.supplier.id), 'purchase_date': '2026-10-20',
            'items': [{'product_id': str(p.id), 'quantity': q, 'unit_price': u} for p, q, u in items]},
            format='json').json()
        response = self.client.post(purchase_url(created['id'], 'confirm/'), format='json')
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def item_id(self, purchase, product):
        return next(i['id'] for i in purchase['items'] if i['product_id'] == str(product.id))

    def receive(self, purchase, lines, expected=201, receipt_id=None, **extra):
        body = {'receipt_id': str(receipt_id or uuid4()), 'receipt_date': timezone.localdate().isoformat(),
                'lines': [{'item_id': item, 'quantity': quantity} for item, quantity in lines], **extra}
        response = self.client.post(purchase_url(purchase['id'], 'receipts/'), body, format='json')
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()

    def purchase_detail(self, purchase):
        return self.client.get(detail_url(purchase['id'])).json()

    def movements(self, **filters):
        return StockMovementModel.objects.filter(company_id=self.company.id, **filters)


class RegisterReceiptTests(ReceiptApiTestCase):
    def test_partial_then_complete_reception_without_inventory(self):  # AC-01, AC-02, AC-07
        purchase = self.confirmed_purchase()
        flour, bag = self.item_id(purchase, self.flour), self.item_id(purchase, self.bag)
        body = self.receive(purchase, [(flour, '4')], warehouse_id=str(self.warehouse.id))
        self.assertRegex(body['reference'], r'^REC-[0-9A-F]{8}$')
        self.assertEqual((body['status'], body['user_name'], body['warehouse'], body['movements']),
                         ('confirmed', 'ana', None, None))
        self.assertEqual([(l['item_id'], l['quantity']) for l in body['lines']], [(flour, '4.000')])
        detail = self.purchase_detail(purchase)
        item = next(i for i in detail['items'] if i['id'] == flour)
        self.assertEqual((detail['reception_status'], item['received_quantity'], item['pending_quantity']),
                         ('partial', '4.000', '6.000'))
        self.receive(purchase, [(flour, '6'), (bag, '4')])
        detail = self.purchase_detail(purchase)
        self.assertEqual((detail['reception_status'], detail['payment_status']), ('received', 'unpaid'))
        self.assertNotIn('receive', detail['allowed_actions'])
        self.assertEqual(self.movements().count(), 0)

    def test_rejects_invalid_quantities_and_excess(self):  # AC-03
        purchase = self.confirmed_purchase()
        flour = self.item_id(purchase, self.flour)
        for bad in ('0', '-1', 'abc', '1.0001', '11'):
            body = self.receive(purchase, [(flour, bad)], expected=400)
            self.assertIn('quantity', body['lines'][0], bad)
        self.assertEqual(ReceiptModel.objects.count(), 0)
        self.receive(purchase, [(flour, '8')])
        body = self.receive(purchase, [(flour, '3')], expected=400)
        self.assertIn('pendiente (2.000)', body['lines'][0]['quantity'][0])

    def test_integer_units_reject_fractions(self):  # EDGE-06
        purchase = self.confirmed_purchase([(self.boxes, '5', '3.00')])
        body = self.receive(purchase, [(self.item_id(purchase, self.boxes), '1.5')], expected=400)
        self.assertIn('quantity', body['lines'][0])

    def test_lines_are_required_unique_and_belong_to_the_purchase(self):  # AC-04
        purchase = self.confirmed_purchase()
        flour = self.item_id(purchase, self.flour)
        self.assertIn('lines', self.receive(purchase, [], expected=400))
        body = self.receive(purchase, [(flour, '1'), (flour, '1'), (str(uuid4()), '1')], expected=400)
        self.assertEqual([bool(line) for line in body['lines']], [False, True, True])

    def test_date_is_required_and_not_future(self):  # AC-05
        purchase = self.confirmed_purchase()
        line = {'item_id': self.item_id(purchase, self.flour), 'quantity': '1'}
        for bad in (None, (timezone.localdate() + timedelta(days=1)).isoformat()):
            response = self.client.post(purchase_url(purchase['id'], 'receipts/'), {
                'receipt_id': str(uuid4()), 'receipt_date': bad, 'lines': [line]}, format='json')
            self.assertEqual(response.status_code, 400)
            self.assertIn('receipt_date', response.json())
        response = self.client.post(purchase_url(purchase['id'], 'receipts/'), {
            'receipt_id': str(uuid4()), 'lines': [line]}, format='json')
        self.assertIn('receipt_date', response.json())

    def test_only_confirmed_purchases_receive(self):  # AC-06
        draft = self.create()
        line = (draft['items'][0]['id'], '1')
        body = self.receive(draft, [line], expected=409)
        self.assertEqual(body['detail'], 'Solo una compra confirmada admite recepciones.')
        self.client.post(purchase_url(draft['id'], 'cancel/'), {'reason': 'x'}, format='json')
        self.receive(draft, [line], expected=409)
        self.assertEqual(self.client.get(purchase_url(draft['id'], 'reception-form/')).status_code, 409)

    def test_receiving_blocks_the_cancellation(self):  # AC-12
        purchase = self.confirmed_purchase()
        self.assertEqual(purchase['allowed_actions'], ['receive', 'pay', 'cancel'])
        self.receive(purchase, [(self.item_id(purchase, self.flour), '1')])
        self.assertEqual(self.purchase_detail(purchase)['allowed_actions'], ['receive', 'pay'])
        response = self.client.post(purchase_url(purchase['id'], 'cancel/'), {'reason': 'x'}, format='json')
        self.assertEqual(response.status_code, 409)

    def test_idempotent_by_receipt_id(self):  # AC-11, INV-10
        self.inventory_on()
        purchase = self.confirmed_purchase()
        lines = [(self.item_id(purchase, self.flour), '4')]
        rid = uuid4()
        first = self.receive(purchase, lines, receipt_id=rid, warehouse_id=str(self.warehouse.id))
        again = self.receive(purchase, lines, expected=200, receipt_id=rid, warehouse_id=str(self.warehouse.id))
        self.assertEqual(again['id'], first['id'])
        self.assertEqual((ReceiptModel.objects.count(), self.movements().count()), (1, 1))
        other = self.confirmed_purchase()
        body = self.receive(other, [(self.item_id(other, self.flour), '1')], expected=409, receipt_id=rid,
                            warehouse_id=str(self.warehouse.id))
        self.assertEqual(body['code'], 'receipt_conflict')

    def test_does_not_touch_expenses_or_amounts(self):  # AC-16, INV-12
        purchase = self.confirmed_purchase()
        expenses = ExpenseModel.objects.count()
        self.receive(purchase, [(self.item_id(purchase, self.flour), '4')])
        after = self.purchase_detail(purchase)
        self.assertEqual((ExpenseModel.objects.count(), after['total'], after['status']),
                         (expenses, purchase['total'], 'confirmed'))
        self.assertEqual(PurchaseModel.objects.get(pk=purchase['id']).payment_status, 'unpaid')


class ReceiptWithInventoryTests(ReceiptApiTestCase):
    def setUp(self):
        super().setUp()
        self.inventory_on()

    def test_controlled_lines_enter_stock(self):  # AC-08, INV-08
        purchase = self.confirmed_purchase()
        flour = self.item_id(purchase, self.flour)
        body = self.receive(purchase, [(flour, '4'), (self.item_id(purchase, self.bag), '2')],
                            warehouse_id=str(self.warehouse.id))
        entries = self.movements(kind='in')
        self.assertEqual(entries.count(), 1)  # la bolsa no controla stock (AC-09)
        entry = entries.get()
        self.assertEqual((entry.product_id, entry.warehouse_id, entry.quantity, entry.reference, entry.source_type,
                          entry.source_id), (self.flour.id, self.warehouse.id, Decimal('4'), body['reference'],
                                             'purchase_receipt', body['id']))
        self.assertEqual(inventory.get_balance(self.company.id, self.flour.id, self.warehouse.id), Decimal('4'))
        self.assertEqual(body['warehouse'], {'id': str(self.warehouse.id), 'name': 'Central'})
        self.assertEqual(len(body['movements']), 1)
        self.assertEqual(body['movements'][0]['quantity'], '4.000')
        detail = self.client.get(purchase_url(purchase['id'], f'receipts/{body["id"]}/')).json()
        self.assertEqual(detail['movements'], body['movements'])

    def test_warehouse_is_required_and_must_be_active(self):  # AC-08
        purchase = self.confirmed_purchase()
        lines = [(self.item_id(purchase, self.flour), '4')]
        self.assertIn('warehouse_id', self.receive(purchase, lines, expected=400))
        self.assertIn('warehouse_id', self.receive(purchase, lines, expected=400, warehouse_id=str(uuid4())))
        other = WarehouseModel.objects.create(company_id=make_company('Otra').id, name='Ajeno')
        self.assertIn('warehouse_id', self.receive(purchase, lines, expected=400, warehouse_id=str(other.id)))
        WarehouseModel.objects.filter(pk=self.warehouse.id).update(active=False)
        self.assertIn('warehouse_id', self.receive(purchase, lines, expected=400, warehouse_id=str(self.warehouse.id)))
        self.assertEqual((ReceiptModel.objects.count(), self.movements().count()), (0, 0))

    def test_uncontrolled_only_needs_no_warehouse(self):  # AC-09, EDGE-03
        purchase = self.confirmed_purchase()
        body = self.receive(purchase, [(self.item_id(purchase, self.bag), '2')])
        self.assertEqual((body['warehouse'], body['movements'], self.movements().count()), (None, [], 0))

    def test_inventory_rejection_leaves_nothing_behind(self):  # AC-10
        purchase = self.confirmed_purchase()
        lines = [(self.item_id(purchase, self.flour), '4')]
        from unittest import mock
        with mock.patch('modules.inventory.services.record_movement',
                        side_effect=inventory.MovementValidationError({'warehouse_id': ['El almacén está inactivo.']})):
            body = self.receive(purchase, lines, expected=400, warehouse_id=str(self.warehouse.id))
        self.assertIn('warehouse_id', body)
        self.assertEqual((ReceiptModel.objects.count(), ReceiptItemModel.objects.count()), (0, 0))
        self.assertEqual(self.purchase_detail(purchase)['reception_status'], 'not_received')

    def detail(self, purchase, body):
        return self.client.get(purchase_url(purchase['id'], f'receipts/{body["id"]}/')).json()

    def test_inventory_mode_is_saved_and_lines_flag_their_entries(self):  # AC-01, AC-06
        purchase = self.confirmed_purchase()
        body = self.receive(purchase, [(self.item_id(purchase, self.flour), '4'), (self.item_id(purchase, self.bag), '2')],
                            warehouse_id=str(self.warehouse.id))
        self.assertEqual((body['inventory_mode'], body['inventory_available']), ('inventory', True))
        self.assertEqual([line['stock_entry'] for line in body['lines']], [True, False])
        self.assertEqual(body['movements'][0]['reference'], body['reference'])

    def test_inventory_enabled_without_controlled_lines_is_inventory_mode(self):  # AC-03
        purchase = self.confirmed_purchase()
        body = self.receive(purchase, [(self.item_id(purchase, self.bag), '2')])
        self.assertEqual((body['inventory_mode'], body['movements'], body['lines'][0]['stock_entry']),
                         ('inventory', [], False))

    def test_disabling_inventory_keeps_the_saved_mode_and_movements(self):  # AC-04, EDGE-01
        purchase = self.confirmed_purchase()
        body = self.receive(purchase, [(self.item_id(purchase, self.flour), '4')], warehouse_id=str(self.warehouse.id))
        set_enabled(self.company, DEFAULT_ENABLED_KEYS + ('purchases',))
        detail = self.detail(purchase, body)
        self.assertEqual((detail['inventory_mode'], detail['inventory_available']), ('inventory', False))
        self.assertEqual(detail['movements'], body['movements'])
        self.assertEqual(detail['warehouse'], body['warehouse'])

    def test_retry_after_disabling_inventory_returns_the_original_receipt(self):  # AC-09, INV-05
        purchase = self.confirmed_purchase()
        lines = [(self.item_id(purchase, self.flour), '4')]
        rid = uuid4()
        first = self.receive(purchase, lines, receipt_id=rid, warehouse_id=str(self.warehouse.id))
        set_enabled(self.company, DEFAULT_ENABLED_KEYS + ('purchases',))
        again = self.receive(purchase, lines, expected=200, receipt_id=rid, warehouse_id=str(self.warehouse.id))
        self.assertEqual((again['id'], again['inventory_mode']), (first['id'], 'inventory'))
        self.assertEqual(self.movements().count(), 1)

    def test_documentary_receipt_never_shows_movements_after_enabling_inventory(self):  # AC-02, AC-05, EDGE-02
        set_enabled(self.company, DEFAULT_ENABLED_KEYS + ('purchases',))
        purchase = self.confirmed_purchase()
        body = self.receive(purchase, [(self.item_id(purchase, self.flour), '4')])
        self.assertEqual((body['inventory_mode'], body['movements'], body['warehouse']), ('documental', None, None))
        self.inventory_on()
        detail = self.detail(purchase, body)
        self.assertEqual((detail['inventory_mode'], detail['movements'], detail['warehouse'],
                          detail['lines'][0]['stock_entry']), ('documental', None, None, None))
        self.assertEqual(self.movements().count(), 0)


class ReceptionFormAndQueriesTests(ReceiptApiTestCase):
    def test_form_without_inventory(self):  # AC-14
        purchase = self.confirmed_purchase()
        flour = self.item_id(purchase, self.flour)
        self.receive(purchase, [(flour, '4')])
        body = self.client.get(purchase_url(purchase['id'], 'reception-form/')).json()
        self.assertEqual((body['inventory_enabled'], body['warehouses'], body['warehouse_id']), (False, [], None))
        line = next(l for l in body['lines'] if l['item_id'] == flour)
        self.assertEqual((line['ordered'], line['received'], line['pending'], line['tracks_stock'],
                          line['allows_fractions'], line['unit']), ('10.000', '4.000', '6.000', False, True,
                                                                     {'abbreviation': 'kg'}))

    def test_form_with_inventory_offers_warehouses(self):  # AC-14
        set_enabled(self.company, ENABLED)
        purchase = self.confirmed_purchase()
        body = self.client.get(purchase_url(purchase['id'], 'reception-form/')).json()
        self.assertEqual((body['inventory_enabled'], body['warehouse_id']), (True, str(self.warehouse.id)))
        self.assertEqual(body['warehouses'], [{'id': str(self.warehouse.id), 'name': 'Central', 'is_default': True}])
        self.assertEqual({l['product']['name']: l['tracks_stock'] for l in body['lines']},
                         {'Harina': True, 'Bolsa': False})

    def test_list_and_detail(self):  # AC-13
        purchase = self.confirmed_purchase()
        flour = self.item_id(purchase, self.flour)
        first = self.receive(purchase, [(flour, '1')])
        second = self.receive(purchase, [(flour, '2')])
        body = self.client.get(purchase_url(purchase['id'], 'receipts/')).json()
        self.assertEqual(body['count'], 2)
        self.assertEqual({r['id'] for r in body['results']}, {first['id'], second['id']})
        self.assertEqual(set(body['results'][0]), {'id', 'reference', 'receipt_date', 'status', 'user_name',
                                                   'lines_count'})
        detail = self.client.get(purchase_url(purchase['id'], f'receipts/{first["id"]}/')).json()
        self.assertEqual((detail['purchase']['id'], detail['purchase']['reference']),
                         (purchase['id'], purchase['reference']))

    def test_receipt_of_another_purchase_or_company_is_404(self):  # AC-13, AC-15
        purchase, other = self.confirmed_purchase(), self.confirmed_purchase()
        receipt = self.receive(purchase, [(self.item_id(purchase, self.flour), '1')])
        self.assertEqual(self.client.get(purchase_url(other['id'], f'receipts/{receipt["id"]}/')).status_code, 404)
        stranger = APIClient()
        company = make_company('Empresa B')
        authenticate(stranger, make_admin(company, username='beto'))
        set_enabled(company, ENABLED)
        for suffix in (f'receipts/{receipt["id"]}/', 'receipts/', 'reception-form/'):
            self.assertEqual(stranger.get(purchase_url(purchase['id'], suffix)).status_code, 404, suffix)
        response = stranger.post(purchase_url(purchase['id'], 'receipts/'), {
            'receipt_id': str(uuid4()), 'receipt_date': date.today().isoformat(),
            'lines': [{'item_id': str(uuid4()), 'quantity': '1'}]}, format='json')
        self.assertEqual(response.status_code, 404)


class ReceiptAccessTests(ReceiptApiTestCase):
    def test_authentication_module_and_methods(self):  # AC-15
        purchase = self.confirmed_purchase()
        urls = [purchase_url(purchase['id'], s) for s in ('receipts/', 'reception-form/')]
        anonymous = APIClient()
        for url in urls:
            self.assertEqual(anonymous.get(url).status_code, 401)
        self.assertEqual(self.client.put(urls[0], {}, format='json').status_code, 405)
        self.assertEqual(self.client.post(urls[1], {}, format='json').status_code, 405)
        set_enabled(self.company, DEFAULT_ENABLED_KEYS)  # Compras deshabilitado
        for url in urls:
            response = self.client.get(url)
            self.assertEqual((response.status_code, response.json().get('code')), (403, 'module_disabled'))
