"""Importación de ventas de punta a punta contra la base real: catálogo, clientes, pedidos y cobros reales."""
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.catalog.infrastructure.django.models import ProductModel
from modules.customers.infrastructure.django.models import CustomerModel
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
