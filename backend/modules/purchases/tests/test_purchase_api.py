from decimal import Decimal
from uuid import uuid4

from django.apps import apps
from rest_framework.test import APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.catalog.infrastructure.django.models import ProductModel, UnitModel
from modules.modularity.infrastructure.django.models import CompanyModuleModel
from modules.purchases.infrastructure.django.models import PurchaseItemModel, PurchaseModel, SupplierModel
from modules.purchases.tests.test_api import enable_purchases

LIST_URL = '/api/purchases/'
DETAIL_FIELDS = {'id', 'supplier', 'purchase_date', 'external_reference', 'notes', 'status', 'currency', 'editable',
                 'items', 'total', 'created_at', 'updated_at'}
ITEM_FIELDS = {'id', 'product_id', 'product_name', 'unit_abbreviation', 'quantity', 'unit_price', 'subtotal'}


def detail_url(purchase_id):
    return f'{LIST_URL}{purchase_id}/'


class PurchaseApiTestCase(APITestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        authenticate(self.client, make_admin(self.company, username='ana'))
        enable_purchases(self.company)
        self.supplier = SupplierModel.objects.create(company_id=self.company.id, name='Distribuidora Sur')
        self.kg = UnitModel.objects.create(company_id=self.company.id, name='Kilogramo', abbreviation='kg',
                                           allows_fractions=True)
        self.unit = UnitModel.objects.create(company_id=self.company.id, name='Unidad', abbreviation='u')
        self.flour = self.product('Harina', unit=self.kg)
        self.boxes = self.product('Cajas', unit=self.unit)
        self.bag = self.product('Bolsa')

    def product(self, name, unit=None, company_id=None, active=True):
        return ProductModel.objects.create(
            company_id=company_id or self.company.id, name=name, sale_price=Decimal('1.00'), base_unit=unit,
            tracks_stock=unit is not None, active=active)

    def payload(self, **extra):
        return {'supplier_id': str(self.supplier.id), 'purchase_date': '2026-10-29',
                'items': [{'product_id': str(self.flour.id), 'quantity': '2.5', 'unit_price': '10.00'}], **extra}

    def create(self, **extra):
        response = self.client.post(LIST_URL, self.payload(**extra), format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()


class CreatePurchaseTests(PurchaseApiTestCase):
    def test_create_returns_the_draft_with_derived_amounts(self):  # AC-01
        body = self.create(external_reference='F-1', notes='n')
        self.assertEqual(set(body), DETAIL_FIELDS)
        self.assertEqual((body['status'], body['currency'], body['editable']), ('draft', 'BOB', True))
        self.assertEqual(body['supplier'], {'id': str(self.supplier.id), 'name': 'Distribuidora Sur', 'active': True})
        item = body['items'][0]
        self.assertEqual(set(item), ITEM_FIELDS)
        self.assertEqual((item['product_name'], item['unit_abbreviation'], item['quantity'], item['unit_price'],
                          item['subtotal']), ('Harina', 'kg', '2.500', '10.00', '25.00'))
        self.assertEqual(body['total'], '25.00')
        self.assertEqual(PurchaseModel.objects.get(pk=body['id']).total, Decimal('25.00'))

    def test_optional_fields_and_empty_items(self):  # AC-02
        response = self.client.post(LIST_URL, {'supplier_id': str(self.supplier.id), 'purchase_date': '2026-10-29',
                                               'notes': None}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual((body['external_reference'], body['notes'], body['items'], body['total']),
                         ('', '', [], '0.00'))

    def test_header_validation_reports_every_field(self):  # AC-03
        response = self.client.post(LIST_URL, {'external_reference': 'x' * 101, 'notes': 'n' * 2001}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {'supplier_id', 'purchase_date', 'external_reference', 'notes'})
        self.assertEqual(PurchaseModel.objects.count(), 0)

    def test_unknown_inactive_or_foreign_supplier(self):  # AC-03, INV-11
        inactive = SupplierModel.objects.create(company_id=self.company.id, name='Norte', active=False)
        foreign = SupplierModel.objects.create(company_id=uuid4(), name='Ajeno')
        for supplier_id in (uuid4(), inactive.id, foreign.id):
            response = self.client.post(LIST_URL, self.payload(supplier_id=str(supplier_id)), format='json')
            self.assertEqual(response.status_code, 400)
            self.assertIn('supplier_id', response.json())
        response = self.client.post(LIST_URL, self.payload(supplier_id='no-es-uuid'), format='json')
        self.assertEqual(response.status_code, 400)  # EDGE-06

    def test_line_errors_are_indexed_and_nothing_is_saved(self):  # AC-03
        inactive = self.product('Viejo', active=False)
        foreign = self.product('Ajeno', company_id=uuid4())
        items = [
            {'product_id': str(self.flour.id), 'quantity': '1', 'unit_price': '1.00'},
            {'product_id': str(self.flour.id), 'quantity': '0', 'unit_price': '-1'},
            {'product_id': str(inactive.id), 'quantity': '1', 'unit_price': '1.00'},
            {'product_id': str(foreign.id), 'quantity': '1', 'unit_price': '1.00'},
            {'product_id': str(self.boxes.id), 'quantity': '1.5', 'unit_price': '1.00'},
        ]
        response = self.client.post(LIST_URL, self.payload(items=items, supplier_id=None), format='json')
        self.assertEqual(response.status_code, 400)
        errors = response.json()
        self.assertIn('supplier_id', errors)
        lines = errors['items']
        self.assertEqual(len(lines), 5)
        self.assertEqual(lines[0], {})
        self.assertEqual(set(lines[1]), {'product_id', 'quantity', 'unit_price'})
        self.assertIn('product_id', lines[2])
        self.assertIn('product_id', lines[3])
        self.assertIn('quantity', lines[4])
        self.assertEqual((PurchaseModel.objects.count(), PurchaseItemModel.objects.count()), (0, 0))

    def test_numbers_must_be_text_or_integers_never_float(self):  # AC-04
        for field, value in (('quantity', 1.5), ('unit_price', 10.5), ('quantity', 'NaN'), ('quantity', '1e3'),
                             ('unit_price', 'abc'), ('unit_price', True)):
            item = {'product_id': str(self.flour.id), 'quantity': '1', 'unit_price': '1', field: value}
            response = self.client.post(LIST_URL, self.payload(items=[item]), format='json')
            self.assertEqual(response.status_code, 400, (field, value))
        item = {'product_id': str(self.flour.id), 'quantity': 3, 'unit_price': 7}
        response = self.client.post(LIST_URL, self.payload(items=[item]), format='json')
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()['total'], '21.00')

    def test_total_status_discount_and_tax_are_ignored(self):  # AC-05, INV-07
        item = {'product_id': str(self.flour.id), 'quantity': '2', 'unit_price': '10', 'subtotal': '1.00',
                'product_name': 'Falso', 'discount': '5'}
        body = self.create(items=[item], total='1.00', status='confirmed', discount='9.00', tax='3.00')
        self.assertEqual((body['total'], body['status']), ('20.00', 'draft'))
        self.assertEqual(body['items'][0]['product_name'], 'Harina')

    def test_saving_creates_no_stock_movements_or_expenses(self):  # AC-10, INV-10
        movements, expenses = apps.get_model('inventory', 'StockMovementModel'), apps.get_model('expenses', 'ExpenseModel')
        purchase = self.create()
        self.client.patch(detail_url(purchase['id']), {'notes': 'x', 'items': []}, format='json')
        self.assertEqual((movements.objects.count(), expenses.objects.count()), (0, 0))


class GetPurchaseTests(PurchaseApiTestCase):
    def test_detail_shows_an_inactive_supplier(self):  # AC-06
        purchase = self.create()
        SupplierModel.objects.filter(pk=self.supplier.id).update(active=False)
        body = self.client.get(detail_url(purchase['id'])).json()
        self.assertEqual(body['supplier'], {'id': str(self.supplier.id), 'name': 'Distribuidora Sur', 'active': False})
        self.assertEqual(body['id'], purchase['id'])

    def test_unknown_and_foreign_purchase_are_404(self):  # AC-06, INV-11
        other = make_company('Empresa B')
        foreign = PurchaseModel.objects.create(company_id=other.id, supplier_id=uuid4(), purchase_date='2026-10-29')
        for purchase_id in (uuid4(), foreign.id):
            response = self.client.get(detail_url(purchase_id))
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json(), {'detail': 'Compra no encontrada.'})
            self.assertEqual(self.client.patch(detail_url(purchase_id), {'notes': 'x'}, format='json').status_code, 404)


class UpdatePurchaseTests(PurchaseApiTestCase):
    def test_patch_changes_only_sent_fields(self):  # AC-07
        purchase = self.create(notes='a', external_reference='R')
        body = self.client.patch(detail_url(purchase['id']), {'notes': 'b'}, format='json').json()
        self.assertEqual((body['notes'], body['external_reference'], body['total']), ('b', 'R', '25.00'))
        self.assertEqual((body['id'], body['status'], body['created_at']),
                         (purchase['id'], 'draft', purchase['created_at']))
        self.assertEqual(self.client.patch(detail_url(purchase['id']), {}, format='json').status_code, 200)

    def test_patch_items_replaces_the_lines_and_keeps_the_snapshot(self):  # AC-07, INV-08
        purchase = self.create()
        ProductModel.objects.filter(pk=self.flour.id).update(name='Harina RENOMBRADA', active=False)
        items = [{'product_id': str(self.flour.id), 'quantity': '4', 'unit_price': '3.00'},
                 {'product_id': str(self.bag.id), 'quantity': '1.25', 'unit_price': '2.00'}]
        response = self.client.patch(detail_url(purchase['id']), {'items': items}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual([(i['product_name'], i['unit_abbreviation'], i['subtotal']) for i in body['items']],
                         [('Harina', 'kg', '12.00'), ('Bolsa', '', '2.50')])
        self.assertEqual(body['total'], '14.50')
        self.assertEqual(PurchaseItemModel.objects.filter(purchase_id=purchase['id']).count(), 2)
        removed = self.client.patch(detail_url(purchase['id']), {'items': []}, format='json').json()
        self.assertEqual((removed['items'], removed['total']), ([], '0.00'))

    def test_failed_patch_leaves_the_draft_untouched(self):  # AC-07
        purchase = self.create()
        response = self.client.patch(detail_url(purchase['id']), {
            'notes': 'cambiada', 'items': [{'product_id': str(self.flour.id), 'quantity': '0', 'unit_price': '1'}]},
            format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get(detail_url(purchase['id'])).json()['notes'], '')
        self.assertEqual(self.client.get(detail_url(purchase['id'])).json()['total'], '25.00')

    def test_patch_requires_an_active_supplier(self):  # AC-08, EDGE-05
        purchase = self.create()
        SupplierModel.objects.filter(pk=self.supplier.id).update(active=False)
        response = self.client.patch(detail_url(purchase['id']), {'notes': 'x'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('supplier_id', response.json())
        other = SupplierModel.objects.create(company_id=self.company.id, name='Otro')
        response = self.client.patch(detail_url(purchase['id']), {'supplier_id': str(other.id)}, format='json')
        self.assertEqual(response.json()['supplier']['id'], str(other.id))

    def test_put_and_delete_are_not_allowed(self):  # AC-11
        purchase = self.create()
        self.assertEqual(self.client.put(detail_url(purchase['id']), {}, format='json').status_code, 405)
        self.assertEqual(self.client.delete(detail_url(purchase['id'])).status_code, 405)


class ListPurchaseTests(PurchaseApiTestCase):
    def test_list_is_ordered_filtered_and_scoped_to_the_company(self):  # AC-09
        other_supplier = SupplierModel.objects.create(company_id=self.company.id, name='Otro')
        old = self.create(purchase_date='2026-10-01')
        new = self.create(purchase_date='2026-10-20')
        mine = self.create(supplier_id=str(other_supplier.id), purchase_date='2026-10-10', items=[])
        other = make_company('Empresa B')
        PurchaseModel.objects.create(company_id=other.id, supplier_id=uuid4(), purchase_date='2026-12-01')
        body = self.client.get(LIST_URL).json()
        self.assertEqual(body['count'], 3)
        self.assertEqual([r['id'] for r in body['results']], [new['id'], mine['id'], old['id']])
        first = body['results'][0]
        self.assertEqual(set(first), {'id', 'purchase_date', 'supplier', 'external_reference', 'total', 'currency',
                                      'status', 'items_count'})
        self.assertEqual((first['supplier']['name'], first['total'], first['items_count']),
                         ('Distribuidora Sur', '25.00', 1))
        filtered = self.client.get(LIST_URL, {'supplier_id': str(other_supplier.id)}).json()
        self.assertEqual([r['id'] for r in filtered['results']], [mine['id']])
        self.assertEqual(self.client.get(LIST_URL, {'supplier_id': 'x'}).status_code, 400)

    def test_pagination(self):  # AC-09
        for day in range(1, 4):
            self.create(purchase_date=f'2026-10-0{day}')
        body = self.client.get(LIST_URL, {'page_size': 2}).json()
        self.assertEqual((body['count'], len(body['results']), bool(body['next'])), (3, 2, True))


class AccessTests(PurchaseApiTestCase):
    def test_requires_authentication(self):  # AC-11
        self.assertEqual(self.client.__class__().get(LIST_URL).status_code, 401)

    def test_module_disabled_is_403(self):  # AC-11
        CompanyModuleModel.objects.filter(company_id=self.company.id, module_key='purchases').delete()
        self.assertEqual(self.client.get(LIST_URL).status_code, 403)
        self.assertEqual(self.client.post(LIST_URL, self.payload(), format='json').status_code, 403)
