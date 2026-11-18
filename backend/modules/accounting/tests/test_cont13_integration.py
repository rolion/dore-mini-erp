"""CONT-13: validación integrada de Contabilidad antes de integrarla a `main` (AC-01, 03, 04, 05, 06, 07 del plan).

Una sola empresa recorre venta con anticipo y entrega, servicio cobrado, compra con recepción y pago, gasto y su
anulación sobre el libro de partida doble real (sin dobles). Cada importe esperado está calculado a mano.
Complementa, sin repetirlas, las pruebas por módulo (`sales/…/test_sales_posting`, `purchases/…/test_purchase_posting`,
`expenses/…/test_voiding_api`, `receivables/…/test_service_posting`).
"""
from collections import Counter
from datetime import timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from django.db import transaction
from django.db.models import Sum
from django.test import TransactionTestCase
from django.utils import timezone

from modules.accounting import services as accounting
from modules.accounting.infrastructure.django.models import (
    EntryModel,
    FiscalPeriodModel,
    JournalEntryModel,
    JournalLineModel,
    SettingsModel,
)
from modules.accounting.infrastructure.django.repositories import DjangoAccountRepository
from modules.accounting.tests.journal_support import make_account, make_period, money_account
from modules.accounts.testing import authenticate, make_admin
from modules.catalog.infrastructure.django.models import ProductModel, UnitModel
from modules.expenses.infrastructure.django.models import ExpenseModel
from modules.inventory.infrastructure.django.models import StockMovementModel, WarehouseModel
from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
from modules.modularity.infrastructure.django.models import CompanyModuleModel
from modules.modularity.tests.test_enforcement import set_enabled
from modules.purchases.infrastructure.django.models import ReceiptModel, SupplierModel
from modules.receivables.tests import test_api as services_api
from modules.receivables.tests.test_payment_ledger import configure
from modules.sales.infrastructure.django.models import PaymentModel as OrderPayment
from rest_framework.test import APIClient

TODAY = timezone.localdate()
D = Decimal
ZERO = D('0')
ORDERS = '/api/orders/'
PURCHASES = '/api/purchases/'
EXPENSES = '/api/expenses/'
CATEGORIES = '/api/expense-categories/'
MODULES = tuple(dict.fromkeys(DEFAULT_ENABLED_KEYS + (
    'sales', 'customers', 'expenses', 'purchases', 'inventory', 'accounting',
    'catalog', 'services', 'quotations', 'dentistry', 'receivables')))


class Cont13Base(TransactionTestCase):
    quote = services_api.ReceivablesApiTests.quote
    decide = services_api.ReceivablesApiTests.decide
    detail = services_api.ReceivablesApiTests.detail
    pay_service = services_api.ReceivablesApiTests.pay

    def setUp(self):
        services_api.ReceivablesApiTests.setUp(self)
        self.company_id = self.admin.company_id
        set_enabled(self.admin.company, MODULES)
        self.company = self.admin.company
        accounts = DjangoAccountRepository(self.company_id)
        self.caja = money_account(accounts, 'Caja', '110101', 'CASH')
        self.banco = money_account(accounts, 'Banco', '110102')
        self.cxc = make_account(self.company_id, 'Cuentas por cobrar', 'ASSET', '112001')
        self.inventario = make_account(self.company_id, 'Inventario', 'ASSET', '113001')
        self.anticipos_prov = make_account(self.company_id, 'Anticipos a proveedores', 'ASSET', '113101')
        self.proveedores = make_account(self.company_id, 'Proveedores', 'LIABILITY', '210101')
        self.anticipos = make_account(self.company_id, 'Anticipos de clientes', 'LIABILITY', '210001')
        self.capital = make_account(self.company_id, 'Capital', 'EQUITY', '310001')
        self.ingresos = make_account(self.company_id, 'Ingresos por ventas', 'INCOME', '410001')
        self.ingresos_serv = make_account(self.company_id, 'Ingresos por servicios', 'INCOME', '420001')
        self.alquiler = make_account(self.company_id, 'Alquiler', 'EXPENSE', '510001')
        self.period = make_period(self.company_id, 'Año', TODAY - timedelta(days=200), TODAY + timedelta(days=100))
        for method, account in (('CASH', self.caja), ('QR', self.banco), ('BANK_TRANSFER', self.banco)):
            configure(self.company_id, method, account)
        for role, account in (('RECEIVABLE', self.cxc), ('SALES_INCOME', self.ingresos),
                              ('SERVICE_INCOME', self.ingresos_serv), ('CUSTOMER_ADVANCES', self.anticipos),
                              ('INVENTORY', self.inventario), ('PAYABLE', self.proveedores),
                              ('SUPPLIER_ADVANCES', self.anticipos_prov)):
            accounting.set_role_account(self.company_id, role, account.id)
        category = self.client.post(CATEGORIES, {'name': 'Alquiler'}, format='json').json()
        self.category_id = category['id']
        accounting.set_category_account(self.company_id, UUID(self.category_id), self.alquiler.id)
        self.supplier = SupplierModel.objects.create(company_id=self.company_id, name='Distribuidora Sur')
        unit = UnitModel.objects.create(company_id=self.company_id, name='Unidad', abbreviation='u')
        self.boxes = ProductModel.objects.create(company_id=self.company_id, name='Cajas', sale_price=D('1.00'),
                                                 base_unit=unit, tracks_stock=True, active=True, can_buy=True)
        self.warehouse = WarehouseModel.objects.create(company_id=self.company_id, name='Central', is_default=True)

    # --- flujos de negocio por HTTP -------------------------------------------------------------------------
    def post(self, url, body=None, expected=(200, 201)):
        response = self.client.post(url, body or {}, format='json')
        self.assertIn(response.status_code, expected if isinstance(expected, tuple) else (expected,),
                      response.content)
        return response.json() if response.content else {}

    def prepared_order(self, price='150.00', quantity=2):
        product = ProductModel.objects.create(company_id=self.company_id, name=f'Pack {uuid4().hex[:6]}',
                                              description='', sale_price=D(price), active=True, can_sell=True)
        order = self.post(ORDERS, {'sales_channel': 'WHATSAPP'}, 201)
        self.post(f"{ORDERS}{order['id']}/items/", {'product_id': str(product.id), 'quantity': quantity}, 201)
        self.post(f"{ORDERS}{order['id']}/prepare/")
        return order['id']

    def pay_order(self, order_id, amount, method='CASH', **extra):
        return self.post(f'{ORDERS}{order_id}/payments/', {'amount': amount, 'payment_method': method, **extra})

    def purchase(self, quantity='100', price='10.00'):
        created = self.post(PURCHASES, {'supplier_id': str(self.supplier.id), 'purchase_date': TODAY.isoformat(),
                                        'items': [{'product_id': str(self.boxes.id), 'quantity': quantity,
                                                   'unit_price': price}]}, 201)
        return self.post(f"{PURCHASES}{created['id']}/confirm/")

    def receive(self, purchase, quantity, receipt_id=None, expected=(200, 201)):
        body = {'receipt_id': str(receipt_id or uuid4()), 'receipt_date': TODAY.isoformat(),
                'warehouse_id': str(self.warehouse.id),
                'lines': [{'item_id': purchase['items'][0]['id'], 'quantity': quantity}]}
        return self.post(f"{PURCHASES}{purchase['id']}/receipts/", body, expected)

    def pay_purchase(self, purchase, amount, method='CASH'):
        return self.post(f"{PURCHASES}{purchase['id']}/payments/", {
            'payment_id': str(uuid4()), 'amount': amount, 'payment_method': method,
            'payment_date': TODAY.isoformat()}, 201)

    def expense(self, amount='500.00', method='BANK_TRANSFER', day=None, expected=201):
        response = self.client.post(EXPENSES, {
            'description': 'Alquiler del local', 'amount': amount, 'category_id': self.category_id,
            'expense_date': (day or TODAY).isoformat(), 'payment_method': method}, format='json')
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()

    # --- conciliación --------------------------------------------------------------------------------------
    def net(self, account):
        balance = accounting.journal_balances(self.company_id, [account.id]).get(account.id)
        return (balance.debit - balance.credit) if balance else ZERO

    def entries(self, company_id=None):
        return JournalEntryModel.objects.filter(company_id=company_id or self.company_id)

    def assert_books_reconcile(self, company_id=None):
        """INV-01/02/05: asientos que cuadran, sin duplicados de origen, líneas de la empresa y saldos que suman 0."""
        company_id = company_id or self.company_id
        for entry in self.entries(company_id):
            lines = list(entry.lines.all())
            debit, credit = sum(line.debit for line in lines), sum(line.credit for line in lines)
            self.assertEqual(debit, credit, f'asiento descuadrado {entry.id}')
            self.assertEqual(debit, entry.total)
            self.assertGreaterEqual(len(lines), 2)
            self.assertTrue(all(line.company_id == company_id for line in lines))
            self.assertTrue(all(line.account.company_id == company_id for line in lines))
        origins = Counter(self.entries(company_id).filter(origin_id__isnull=False, reverses__isnull=True)
                          .values_list('origin_kind', 'origin_id'))
        self.assertEqual([key for key, count in origins.items() if count > 1], [])
        totals = JournalLineModel.objects.filter(company_id=company_id).aggregate(d=Sum('debit'), c=Sum('credit'))
        self.assertEqual(totals['d'] or ZERO, totals['c'] or ZERO)
        balances = accounting.journal_balances(company_id)
        self.assertEqual(sum(b.debit - b.credit for b in balances.values()), ZERO)


class IntegratedJourneyTests(Cont13Base):
    def test_sale_service_purchase_expense_and_voiding_reconcile_in_one_book(self):  # AC-01, AC-04
        # Apertura: asiento manual balanceado (Caja contra Capital).
        with transaction.atomic():
            accounting.post_journal_entry(self.company_id, accounting.JournalEntryInput(
                accounting_date=TODAY - timedelta(days=1), description='Apertura',
                lines=[accounting.JournalLineInput(self.caja.id, debit=D('1000.00')),
                       accounting.JournalLineInput(self.capital.id, credit=D('1000.00'))],
                created_by=self.admin.pk, created_by_name='ana'))
        # Venta a crédito de 300: anticipo de 100 en preparación y entrega con saldo de 200 por cobrar.
        order = self.prepared_order()
        self.pay_order(order, '100.00')
        self.post(f'{ORDERS}{order}/ready/')
        before = self.client.get(f'{ORDERS}{order}/').json()
        self.assertEqual((before['total'], before['paid_total'], before['balance']), ('300.00', '100.00', '200.00'))
        self.post(f'{ORDERS}{order}/deliver/')
        # Servicio: Corona (200) prestado y cobrado 80 en efectivo.
        proforma = self.quote(accept=(0, 1, 2), reject=())
        corona = proforma['lines'][1]['id']
        rendered = self.client.post(f"/api/receivables/commitments/quotation/{proforma['number']}/services/",
                                    {'line_id': corona}, format='json')
        self.assertEqual(rendered.status_code, 201, rendered.content)
        self.assertEqual(self.pay_service(proforma['number'], [(corona, '80.00')]).status_code, 201)
        # Compra de 100 u a 10.00 (1.000): recepción de 60 y pago de 400.
        purchase = self.purchase()
        self.receive(purchase, '60')
        self.pay_purchase(purchase, '400.00')
        detail = self.client.get(f"{PURCHASES}{purchase['id']}/").json()
        self.assertEqual((detail['total'], detail['paid_total'], detail['balance']), ('1000.00', '400.00', '600.00'))
        # Gasto de 500 por banco y gasto de 120 en efectivo que se anula.
        self.expense('500.00')
        voided = self.expense('120.00', 'CASH')
        self.post(f"{EXPENSES}{voided['id']}/void/")

        expected = [(self.caja, D('780.00')), (self.banco, D('-500.00')), (self.cxc, D('320.00')),
                    (self.anticipos, ZERO), (self.ingresos, D('-300.00')), (self.ingresos_serv, D('-200.00')),
                    (self.inventario, D('600.00')), (self.proveedores, D('-200.00')), (self.alquiler, D('500.00')),
                    (self.capital, D('-1000.00')), (self.anticipos_prov, ZERO)]
        for account, value in expected:
            self.assertEqual(self.net(account), value, account.name)
        self.assert_books_reconcile()
        kinds = Counter(self.entries().values_list('origin_kind', flat=True))
        self.assertEqual(kinds['SALE_ADVANCE'], 1)
        self.assertEqual(kinds['SALE_DELIVERY'], 1)
        self.assertEqual(kinds['PURCHASE_RECOGNITION'], 1)
        self.assertEqual(kinds['PURCHASE_PAYMENT'], 1)
        self.assertEqual(kinds['EXPENSE_RECORD'], 2)
        self.assertEqual(self.entries().filter(reverses__isnull=False).count(), 1)  # la anulación del gasto
        # Nada de lo anterior cayó en el libro de una sola cuenta.
        self.assertEqual(EntryModel.objects.filter(company_id=self.company_id).count(), 0)


class PeriodAndCoverageTests(Cont13Base):
    def close_period_and_open_next(self):
        accounting.coverage_status(self.company_id, TODAY)
        SettingsModel.objects.filter(company_id=self.company_id).update(cutoff_date=TODAY - timedelta(days=200))
        FiscalPeriodModel.objects.filter(pk=self.period.id).update(end_date=TODAY - timedelta(days=10))
        make_period(self.company_id, 'Nuevo', TODAY - timedelta(days=9), TODAY + timedelta(days=100))

    def test_a_closed_period_blocks_records_and_the_reversal_goes_to_an_open_one(self):  # AC-03
        self.close_period_and_open_next()
        old_day = TODAY - timedelta(days=20)
        created = self.expense('200.00', day=old_day)
        original = accounting.find_automatic_entry(self.company_id, 'EXPENSE_RECORD', created['id'])
        FiscalPeriodModel.objects.filter(pk=self.period.id).update(status='CLOSED')
        entries, expenses = self.entries().count(), ExpenseModel.objects.count()
        self.expense('50.00', day=old_day, expected=409)  # el período cerrado rechaza y no deja nada a medias
        self.assertEqual((self.entries().count(), ExpenseModel.objects.count()), (entries, expenses))
        self.post(f"{EXPENSES}{created['id']}/void/")
        reversal = self.entries().get(reverses_id=original.id)
        self.assertEqual(reversal.accounting_date, TODAY)
        self.assertNotEqual(reversal.period_id, self.period.id)
        self.assertEqual(self.entries().filter(period_id=self.period.id).count(), 1)  # el original se conserva
        self.assertEqual(self.net(self.alquiler), ZERO)
        self.assert_books_reconcile()

    def test_a_failed_receipt_in_a_closed_period_leaves_no_receipt_stock_or_entry(self):  # AC-07
        purchase = self.purchase()
        FiscalPeriodModel.objects.filter(pk=self.period.id).update(status='CLOSED')
        response = self.client.post(f"{PURCHASES}{purchase['id']}/receipts/", {
            'receipt_id': str(uuid4()), 'receipt_date': TODAY.isoformat(), 'warehouse_id': str(self.warehouse.id),
            'lines': [{'item_id': purchase['items'][0]['id'], 'quantity': '10'}]}, format='json')
        self.assertGreaterEqual(response.status_code, 400, response.content)
        self.assertEqual((ReceiptModel.objects.count(), StockMovementModel.objects.count(),
                          self.entries().count()), (0, 0, 0))

    def test_disabled_accounting_and_pre_cutoff_operations_are_never_posted_retroactively(self):  # AC-05
        CompanyModuleModel.objects.filter(company_id=self.company_id, module_key='accounting').delete()
        order = self.prepared_order()
        self.pay_order(order, '100.00')
        recorded = self.expense('300.00', day=TODAY - timedelta(days=3))
        self.assertFalse(recorded['posted'])
        self.assertEqual(self.entries().count(), 0)  # el negocio siguió, sin asientos
        self.assertEqual((OrderPayment.objects.count(), ExpenseModel.objects.count()), (1, 1))
        CompanyModuleModel.objects.create(company_id=self.company_id, module_key='accounting')
        self.assertEqual(self.entries().count(), 0)  # habilitar no contabiliza lo anterior
        self.post(f"{EXPENSES}{recorded['id']}/void/")  # anular lo anterior al corte tampoco crea reversión
        self.assertEqual(self.entries().count(), 0)
        again = self.expense('40.00')  # desde hoy sí hay cobertura
        self.assertTrue(again['posted'])
        self.assertEqual(self.entries().count(), 1)


class IsolationAndRetryTests(Cont13Base):
    def test_a_second_company_sees_and_changes_nothing_of_the_first(self):  # AC-06
        created = self.expense('500.00')
        entry = accounting.find_automatic_entry(self.company_id, 'EXPENSE_RECORD', created['id'])
        other_admin = make_admin(username='otra-admin')
        other = APIClient()
        authenticate(other, other_admin)
        set_enabled(other_admin.company, MODULES)
        for url in ('/api/accounting/accounts/', '/api/accounting/journal-entries/', '/api/accounting/balances/',
                    '/api/accounting/fiscal-periods/', '/api/accounting/payment-methods/'):
            response = other.get(url)
            self.assertEqual(response.status_code, 200, (url, response.content))
            for leaked in (str(entry.id), str(self.caja.id), str(self.alquiler.id), str(self.period.id)):
                self.assertNotIn(leaked, response.text, url)
        self.assertEqual(other.get(f'/api/accounting/journal-entries/{entry.id}/').status_code, 404)
        reverse = other.post(f'/api/accounting/journal-entries/{entry.id}/reverse/',
                             {'reason': 'x', 'date': TODAY.isoformat()}, format='json')
        self.assertIn(reverse.status_code, (400, 404))
        self.assertEqual(self.entries().filter(reverses__isnull=False).count(), 0)
        self.assertEqual(self.entries(other_admin.company_id).count(), 0)
        self.assertEqual(APIClient().get('/api/accounting/journal-entries/').status_code, 401)
        self.assert_books_reconcile()

    def test_replaying_payments_and_receipts_does_not_duplicate_entries(self):  # AC-07
        order = self.prepared_order('300.00', 1)
        key = str(uuid4())
        self.pay_order(order, '100.00', idempotency_key=key)
        self.pay_order(order, '100.00', idempotency_key=key)
        purchase = self.purchase()
        receipt_id = uuid4()
        self.receive(purchase, '10', receipt_id=receipt_id)
        self.receive(purchase, '10', receipt_id=receipt_id, expected=(200, 201, 409))
        self.assertEqual(OrderPayment.objects.count(), 1)
        self.assertEqual(self.entries().filter(origin_kind='SALE_ADVANCE').count(), 1)
        self.assertEqual(self.entries().filter(origin_kind='PURCHASE_RECOGNITION').count(), 1)
        self.assertEqual(self.net(self.inventario), D('100.00'))
        self.assert_books_reconcile()
