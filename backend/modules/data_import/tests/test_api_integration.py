"""Importación de ventas de punta a punta contra la base real: catálogo, clientes, pedidos y cobros reales."""
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from uuid import uuid4

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.catalog.infrastructure.django.models import ProductModel
from modules.customers.infrastructure.django.models import CustomerModel
from modules.accounting.infrastructure.django.models import JournalEntryModel
from modules.purchases.infrastructure.django.models import PurchaseModel, ReceiptModel
from modules.sales.infrastructure.django.models import OrderModel

CSV = (
    'fecha,n_venta,producto,cantidad,precio_unitario,cliente,metodo_pago,canal,descuento\n'
    '3 ago.,1,pack queso,5,25,Eulogio,QR,Whatsapp,\n'
    '4 ago.,2,pack queso,1,25,Carla,QR,Whatsapp,10\n'
    '4 ago.,2,pack guayaba,1,32,Carla,QR,Whatsapp,\n'
)
OPTIONS = {'infer_products': True, 'infer_customers': True, 'infer_inventory': False, 'infer_accounting': False}


class SalesImportEndToEndTests(APITestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        authenticate(self.client, make_admin(self.company, username='ana'))

    def _upload(self):
        response = self.client.post('/api/imports/sales/', {'file': SimpleUploadedFile('v.csv', CSV.encode('utf-8'))},
                                    format='multipart')
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def test_preview_then_execute_creates_products_customers_and_paid_orders(self):
        upload = self._upload()
        body = {'mapping': upload['suggested_mapping'], 'options': OPTIONS}
        run_url = f"/api/imports/sales/{upload['id']}"
        preview = self.client.post(f'{run_url}/preview/', body, format='json')
        self.assertEqual(preview.status_code, 200, preview.content)
        self.assertEqual(OrderModel.objects.filter(company_id=self.company.id).count(), 0)  # no escribe

        executed = self.client.post(f'{run_url}/execute/', body, format='json')
        self.assertEqual(executed.status_code, 200, executed.content)
        rows = self.client.get(f'{run_url}/rows/').json()
        failed = [r for r in rows['results'] if r['status'] == 'FAILED']
        self.assertEqual(failed, [], failed)

        self.assertEqual(ProductModel.objects.filter(company_id=self.company.id).count(), 2)
        self.assertEqual(CustomerModel.objects.filter(company_id=self.company.id).count(), 2)
        totals = sorted(o.total for o in OrderModel.objects.filter(company_id=self.company.id))
        self.assertEqual(totals, [Decimal('47.00'), Decimal('125.00')])  # 25 + 32 - 10 de descuento
        self.assertTrue(all(o.status == 'DELIVERED' and o.paid_total == o.total
                            for o in OrderModel.objects.filter(company_id=self.company.id)))

        again = self.client.post(f'{run_url}/execute/', body, format='json')  # reintento: no duplica
        self.assertEqual(again.status_code, 200)
        self.assertEqual(OrderModel.objects.filter(company_id=self.company.id).count(), 2)


FULL_CSV = '\n'.join([
    'fecha,n_venta,producto,cantidad,precio_unitario,cliente,metodo_pago,canal,descuento,proveedor,costo_unitario',
    '3 ago.,1,pack queso,5,25,Eulogio,QR,Whatsapp,,DORE,12',
    '3 ago.,2,pack queso,2,25,Carla,QR,Whatsapp,5,DORE,12',
    '3 ago.,2,pack guayaba,1,32,Carla,QR,Whatsapp,,DORE,15',
    '4 ago.,3,pack queso,1,25,Naty,QR,Whatsapp,,DORE,12',
]) + '\n'


class FullSequenceTests(APITestCase):
    """Valoración inicial → corte contable → importación con compras pagadas, inventario y asientos reales."""

    def test_valuation_then_import_with_purchases_inventory_and_accounting(self):
        registered = self.client.post('/api/auth/register/', {
            'company_name': 'Dore', 'username': 'demo', 'first_name': 'd', 'last_name': 'd', 'email': 'd@e.com',
            'password': 'Sup3r-secreta-123'}, format='json')
        self.assertEqual(registered.status_code, 201, registered.content)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + registered.json()['token'])
        company_id = registered.json()['user']['company']['id']

        adopted = self.client.post('/api/valuation/adopt/', {'adoption_id': str(uuid4()), 'lines': []}, format='json')
        self.assertIn(adopted.status_code, (200, 201), adopted.content)
        moved = self.client.patch('/api/accounting/settings/', {'cutoff_date': '2026-08-01'}, format='json')
        self.assertEqual(moved.status_code, 200, moved.content)

        upload = self.client.post('/api/imports/sales/', {'file': SimpleUploadedFile('v.csv', FULL_CSV.encode())},
                                  format='multipart').json()
        options = {'infer_products': True, 'infer_customers': True, 'infer_inventory': True,
                   'infer_accounting': True, 'default_payment_method': 'CASH'}
        body = {'mapping': upload['suggested_mapping'], 'options': options}
        base = f"/api/imports/sales/{upload['id']}"
        preview = self.client.post(f'{base}/preview/', body, format='json').json()
        self.assertEqual((preview['with_errors'], preview['to_create'], preview['without_posting']), (0, 3, 0), preview)
        self.assertEqual((preview['purchases_to_create'], preview['units_to_buy']), (2, 9))  # una por día y proveedor

        executed = self.client.post(f'{base}/execute/', body, format='json')
        self.assertEqual(executed.status_code, 200, executed.content)
        rows = self.client.get(f'{base}/rows/').json()['results']
        self.assertEqual([r for r in rows if r['status'] != 'CREATED'], [])

        purchases = PurchaseModel.objects.filter(company_id=company_id)
        self.assertEqual(purchases.count(), 2)
        self.assertTrue(all(p.payment_status == 'paid' and p.status == 'confirmed' for p in purchases),
                        [(p.status, p.payment_status) for p in purchases])
        self.assertEqual(ReceiptModel.objects.filter(company_id=company_id).count(), 2)  # recibidas por completo
        self.assertEqual(sorted(o.total for o in OrderModel.objects.filter(company_id=company_id)),
                         [Decimal('25.00'), Decimal('77.00'), Decimal('125.00')])
        journal = JournalEntryModel.objects.filter(company_id=company_id)
        self.assertGreater(journal.count(), 6)  # compras, pagos de compra, ventas, cobros y costo de ventas
        self.assertTrue(journal.filter(description__startswith='Costo de ventas').exists())
        stock = self.client.get('/api/stock/').json()
        quantities = [Decimal(str(r.get('quantity', r.get('balance', 0)))) for r in stock.get('results', stock)]
        self.assertTrue(all(q == 0 for q in quantities), quantities)  # compró exactamente lo que vendió


class ReuploadTests(APITestCase):
    """Volver a subir ventas ya importadas no las duplica, aunque sea otro archivo."""

    def setUp(self):
        self.company = make_company('Empresa A')
        authenticate(self.client, make_admin(self.company, username='ana'))

    def _run(self, text, name):
        upload = self.client.post('/api/imports/sales/', {'file': SimpleUploadedFile(name, text.encode())},
                                  format='multipart').json()
        body = {'mapping': upload['suggested_mapping'], 'options': OPTIONS}
        base = f"/api/imports/sales/{upload['id']}"
        preview = self.client.post(f'{base}/preview/', body, format='json').json()
        self.client.post(f'{base}/execute/', body, format='json')
        rows = self.client.get(f'{base}/rows/').json()['results']
        return preview, [r['status'] for r in rows]

    def test_same_sales_in_another_file_are_skipped_and_new_ones_are_loaded(self):
        header = 'fecha,n_venta,producto,cantidad,precio_unitario,cliente,metodo_pago,canal'
        september = chr(10).join([header, '3 sep.,10,pack queso,4,25,Eva,QR,Whatsapp',
                                  '4 sep.,11,pack queso,1,25,Eva,QR,Whatsapp'])
        _, statuses = self._run(september, 'sep.csv')
        self.assertEqual(statuses, ['CREATED', 'CREATED'])
        extended = september + chr(10) + '5 sep.,12,pack queso,2,25,Eva,QR,Whatsapp'
        preview, statuses = self._run(extended, 'sep_ampliado.csv')
        self.assertEqual((preview['already_imported'], preview['to_create']), (2, 1))
        self.assertEqual(sorted(statuses), ['CREATED', 'SKIPPED_DUPLICATE', 'SKIPPED_DUPLICATE'])
        self.assertEqual(OrderModel.objects.filter(company_id=self.company.id).count(), 3)

    def test_sales_without_number_are_recognized_by_their_content(self):
        header = 'fecha,producto,cantidad,precio_unitario,cliente,metodo_pago,canal'
        text = header + chr(10) + '3 sep.,pack queso,4,25,Eva,QR,Whatsapp'
        self._run(text, 'a.csv')
        _, statuses = self._run(text, 'b.csv')
        self.assertEqual(statuses, ['SKIPPED_DUPLICATE'])
        self.assertEqual(OrderModel.objects.filter(company_id=self.company.id).count(), 1)
