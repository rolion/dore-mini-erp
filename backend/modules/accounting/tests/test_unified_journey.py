"""PB-ACC-005: recorrido unificado productos + servicios + regularización + reporte (AC-01, 04..07 del plan).

Solo cubre brechas: el resto de criterios (atomicidad, idempotencia, concurrencia, permisos, aislamiento) ya
tienen pruebas en `sales/tests/test_payment_ledger.py`, `receivables/tests/test_payment_ledger.py`,
`accounting/tests/test_entries_api.py` y `test_regularization*.py` (ver la matriz del TASK).
"""
import json
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.db import transaction
from django.db.models import Sum
from django.test import TransactionTestCase

from modules.accounting.application.use_cases import ConfigureMethod
from modules.accounting.domain.account import Account
from modules.accounting.infrastructure.django.models import EntryModel
from modules.accounting.infrastructure.django.repositories import DjangoAccountRepository, DjangoMethodMappingRepository
from modules.catalog.infrastructure.django.models import ProductModel
from modules.inventory.infrastructure.django.models import StockMovementModel
from modules.modularity.infrastructure.django.repositories import DjangoCompanyModuleRepository
from modules.receivables.infrastructure.django.models import ObligationModel
from modules.receivables.infrastructure.django.models import PaymentModel as ServicePayment
from modules.receivables.tests import test_api as services_api
from modules.sales.infrastructure.django.models import OrderModel
from modules.sales.infrastructure.django.models import PaymentModel as OrderPayment

ENTRIES = '/api/accounting/entries/'
PREVIEW = '/api/accounting/regularization/preview/'
APPLY = '/api/accounting/regularization/apply/'
ORDERS = '/api/orders/'
DASHBOARD = '/api/reports/dashboard/'
SECRET = 'NOTA-CLINICA-CONFIDENCIAL'


def configure(company_id, method, account):
    with transaction.atomic():
        ConfigureMethod(DjangoAccountRepository(company_id), DjangoMethodMappingRepository(company_id)).execute(
            method, account.id, True)


class UnifiedJourneyTests(TransactionTestCase):
    setUp = services_api.ReceivablesApiTests.setUp
    quote = services_api.ReceivablesApiTests.quote
    decide = services_api.ReceivablesApiTests.decide
    pay_service = services_api.ReceivablesApiTests.pay

    def prepare(self):
        company = self.admin.company_id
        modules = DjangoCompanyModuleRepository(company)
        for key in ('sales', 'customers', 'expenses', 'reporting', 'accounting'):
            modules.enable(key)
        accounts = DjangoAccountRepository(company)
        self.caja = accounts.save(Account.create('Caja', 'BOB'))
        self.banco = accounts.save(Account.create('Banco', 'BOB'))
        configure(company, 'CASH', self.caja)
        configure(company, 'QR', self.banco)

    def entries_api(self, **params):
        response = self.client.get(ENTRIES, params)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def pay_order(self, order_id, amount, method='CASH', **extra):
        response = self.client.post(f'{ORDERS}{order_id}/payments/', {'amount': amount, 'payment_method': method,
                                                                      **extra}, format='json')
        self.assertIn(response.status_code, (200, 201), response.content)
        return response.json()

    def product_order_300(self):
        product = ProductModel.objects.create(company_id=self.admin.company_id, name='Pack', description='',
                                              sale_price=Decimal('150.00'), active=True, can_sell=True)
        order = self.client.post(ORDERS, {'sales_channel': 'WHATSAPP', 'notes': SECRET}, format='json').json()
        added = self.client.post(f"{ORDERS}{order['id']}/items/", {'product_id': str(product.id), 'quantity': 2},
                                format='json')
        self.assertEqual(added.status_code, 201, added.content)
        return order['id']

    def dashboard(self):
        response = self.client.get(DASHBOARD)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    # AC-01, AC-05, AC-07
    def test_products_and_services_make_a_single_book_of_600_without_touching_stock_or_reports(self):
        self.prepare()
        order_id = self.product_order_300()
        report_before = self.dashboard()
        stock_before = StockMovementModel.objects.count()

        keys = [str(uuid4()), str(uuid4())]
        self.pay_order(order_id, '100.00', 'CASH', idempotency_key=keys[0])
        self.pay_order(order_id, '200.00', 'QR', idempotency_key=keys[1])
        p = self.quote()  # servicios aceptados: 100 + 200 (Blanqueamiento rechazado)
        a, b = p['lines'][0]['id'], p['lines'][1]['id']
        service_keys = [uuid4(), uuid4(), uuid4()]
        for key, allocations in zip(service_keys, ([(a, '100.00')], [(b, '50.00')], [(b, '150.00')])):
            self.assertEqual(self.pay_service(p['number'], allocations, key=key).status_code, 201)

        # los mismos cobros reintentados no duplican nada
        self.pay_order(order_id, '100.00', 'CASH', idempotency_key=keys[0])
        self.assertEqual(self.pay_service(p['number'], [(a, '100.00')], key=service_keys[0]).status_code, 200)

        book = self.entries_api()
        self.assertEqual(book['count'], 5)
        totals = {t['currency']: t for t in book['totals']}
        self.assertEqual((totals['BOB']['amount'], totals['BOB']['count']), ('600.00', 5))
        self.assertEqual(totals['BOB']['by_origin'], {'PRODUCT': '300.00', 'SERVICE': '300.00'})
        self.assertEqual(self.entries_api(origin='PRODUCT')['totals'][0]['amount'], '300.00')
        self.assertEqual(self.entries_api(origin='SERVICE')['totals'][0]['amount'], '300.00')
        paged = self.entries_api(page_size=2, page=3)
        self.assertEqual(paged['totals'], book['totals'])  # los totales cubren todas las páginas
        # una entrada por pago, sin pagos huérfanos
        self.assertEqual(EntryModel.objects.values('origin_id').distinct().count(), 5)
        self.assertEqual(OrderPayment.objects.count() + ServicePayment.objects.count(), 5)

        # AC-05: cobrar no mueve stock y ninguna nota llega al libro; el libro no expone saldos
        self.assertEqual(StockMovementModel.objects.count(), stock_before)
        raw = json.dumps(book)
        self.assertNotIn(SECRET, raw)
        self.assertNotIn('balance', raw)
        self.assertNotIn('saldo', raw.lower())

        # AC-07: el reporte ventas − gastos no depende de las entradas del libro
        report_after = self.dashboard()
        for key in ('sales_total', 'expenses_total', 'estimated_profit', 'sales_criteria'):
            self.assertEqual(report_after[key], report_before[key], key)
        self.assertEqual(Decimal(report_after['estimated_profit']),
                         Decimal(report_after['sales_total']) - Decimal(report_after['expenses_total']))

    # AC-04
    def test_changing_the_mapping_keeps_history_and_applies_to_the_next_payment_in_both_origins(self):
        self.prepare()
        order_id = self.product_order_300()
        p = self.quote()
        a = p['lines'][0]['id']
        self.pay_order(order_id, '100.00', 'CASH')
        self.pay_service(p['number'], [(a, '40.00')])
        configure(self.admin.company_id, 'CASH', self.banco)
        self.pay_order(order_id, '50.00', 'CASH')
        self.pay_service(p['number'], [(a, '60.00')])
        rows = EntryModel.objects.order_by('created_at')
        self.assertEqual([(r.origin_kind, r.amount, r.account_id) for r in rows], [
            ('PRODUCT', Decimal('100.00'), self.caja.id), ('SERVICE', Decimal('40.00'), self.caja.id),
            ('PRODUCT', Decimal('50.00'), self.banco.id), ('SERVICE', Decimal('60.00'), self.banco.id)])

    # AC-06
    def test_repeated_regularization_keeps_totals_and_filters_match_every_page(self):
        self.prepare()
        company = self.admin.company_id
        day = date(2026, 3, 10)
        for index in range(6):  # pagos históricos de pedidos, sin entrada (anteriores a la habilitación)
            order = OrderModel.objects.create(company_id=company, status='DELIVERED', sales_channel='STORE',
                                              order_date=day, payment_status='paid')
            OrderPayment.objects.create(order=order, amount=Decimal('10.00'), payment_method='CASH', payment_date=day)
        obligation = ObligationModel.objects.create(company_id=company, source_kind='quotation', source_number='PF-9',
                                                    customer_id=uuid4(), customer_name='C')
        from datetime import datetime, timezone
        ServicePayment.objects.create(
            company_id=company, obligation=obligation, receipt_number='CB-000900', amount=Decimal('25.00'),
            payment_method='QR', payment_date=day, recorded_by=1, recorded_by_name='Ana', idempotency_key=uuid4(),
            payload_hash='h', created_at=datetime(2026, 3, 10, tzinfo=timezone.utc))
        mapping = {'CASH': [{'account_id': str(self.caja.id)}], 'QR': [{'account_id': str(self.banco.id)}]}
        paid_before = (OrderPayment.objects.aggregate(t=Sum('amount'))['t'], ServicePayment.objects.count())

        preview = self.client.post(PREVIEW, {'mapping': mapping}, format='json')
        self.assertEqual(preview.status_code, 200, preview.content)
        self.assertEqual(EntryModel.objects.count(), 0)  # la previsualización no escribe

        first = self.client.post(APPLY, {'mapping': mapping, 'confirm': True}, format='json')
        self.assertEqual(first.status_code, 200, first.content)
        snapshot = self.entries_api(page_size=2)['totals']
        self.assertEqual(snapshot[0]['amount'], '85.00')
        self.assertEqual(snapshot[0]['by_origin'], {'PRODUCT': '60.00', 'SERVICE': '25.00'})

        second = self.client.post(APPLY, {'mapping': mapping, 'confirm': True}, format='json').json()
        self.assertEqual(sum(g['count'] for g in second['groups'] if g['status'] == 'created'), 0)
        self.assertEqual(self.entries_api(page_size=2)['totals'], snapshot)
        self.assertEqual(EntryModel.objects.count(), 7)
        # pagos y saldos no cambian
        self.assertEqual((OrderPayment.objects.aggregate(t=Sum('amount'))['t'], ServicePayment.objects.count()),
                         paid_before)
        # listado y totales coinciden con cada filtro, sobre todas las páginas
        for params, rows, amount in (({'origin': 'PRODUCT'}, 6, '60.00'), ({'origin': 'SERVICE'}, 1, '25.00'),
                                     ({'method': 'QR'}, 1, '25.00'),
                                     ({'account_id': str(self.caja.id)}, 6, '60.00'),
                                     ({'date_from': '2026-03-10', 'date_to': '2026-03-10'}, 7, '85.00')):
            collected, page = [], 1
            while True:
                data = self.entries_api(page_size=2, page=page, **params)
                collected += data['results']
                if not data['next']:
                    break
                page += 1
            self.assertEqual((data['count'], len(collected), data['totals'][0]['amount']), (rows, rows, amount), params)
