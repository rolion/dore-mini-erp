"""Numeración correlativa por período fiscal con BD real (TASK-numeracion-correlativa-pedidos-venta)."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APITestCase

from modules.accounting.infrastructure.django.models import FiscalPeriodModel
from modules.accounts.testing import authenticate, make_admin, make_company
from modules.catalog.infrastructure.django.models import ProductModel
from modules.sales.application.commands import StartOrderPreparation
from modules.sales.domain.exceptions import OrderRuleViolation
from modules.sales.domain.order import Order
from modules.sales.infrastructure.adapters import OrderNumberingAdapter, _period_suffix
from modules.sales.infrastructure.django.models import OrderModel, OrderNumberCounterModel
from modules.sales.infrastructure.django.repositories import DjangoOrderRepository

LIST_URL = '/api/orders/'


def make_period(company, name, start, end, status='OPEN'):
    return FiscalPeriodModel.objects.create(
        company_id=company.id, name=name, start_date=start, end_date=end, status=status)


def make_order(company, order_date, confirm=True):
    repository = DjangoOrderRepository(company.id)
    order = Order.create('WHATSAPP', order_date)
    order.add_item(uuid4(), 'Pack', Decimal('35.00'), 2)
    order = repository.save(order)
    if confirm:
        with transaction.atomic():
            order = StartOrderPreparation(repository, OrderNumberingAdapter(company.id)).execute(order.id)
    return order


class SeriesTests(TestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        self.p2026 = make_period(self.company, 'Gestión 2026', date(2026, 1, 1), date(2026, 12, 31))
        self.p2027 = make_period(self.company, 'Gestión 2027', date(2027, 1, 1), date(2027, 12, 31))

    def test_numbers_are_consecutive_and_restart_in_each_period(self):  # AC-01
        a = make_order(self.company, date(2026, 3, 1))
        b = make_order(self.company, date(2026, 9, 1))
        c = make_order(self.company, date(2027, 1, 5))
        d = make_order(self.company, date(2026, 12, 31))
        self.assertEqual([o.code for o in (a, b, c, d)], ['NV-000001', 'NV-000002', 'NV-000001', 'NV-000003'])
        self.assertEqual((a.number.period_id, c.number.period_id), (self.p2026.id, self.p2027.id))

    def test_the_period_is_the_one_of_the_order_date_not_of_the_confirmation(self):  # AC-04, INV-04
        order = make_order(self.company, date(2026, 12, 30))  # se confirma «hoy», que puede ser de otro período
        self.assertEqual((order.number.period_name, order.code), ('Gestión 2026', 'NV-000001'))

    def test_each_company_has_its_own_series(self):  # AC-01, INV-05
        other = make_company('Empresa B')
        make_period(other, 'Gestión 2026', date(2026, 1, 1), date(2026, 12, 31))
        make_order(self.company, date(2026, 3, 1))
        make_order(self.company, date(2026, 3, 2))
        self.assertEqual(make_order(other, date(2026, 3, 1)).code, 'NV-000001')

    def test_creating_an_order_does_not_consume_a_number(self):  # AC-02
        make_order(self.company, date(2026, 3, 1), confirm=False)
        make_order(self.company, date(2026, 3, 2), confirm=False)
        self.assertEqual(make_order(self.company, date(2026, 3, 3)).code, 'NV-000001')

    def test_a_cancelled_order_keeps_its_number_and_it_is_not_reused(self):  # AC-03
        repository = DjangoOrderRepository(self.company.id)
        first = make_order(self.company, date(2026, 3, 1))
        order = repository.get(first.id)
        order.cancel('Cliente desistió', first.created_at)
        repository.save(order)
        self.assertEqual(repository.get(first.id).code, 'NV-000001')
        self.assertEqual(make_order(self.company, date(2026, 3, 2)).code, 'NV-000002')

    def test_the_period_name_is_a_snapshot(self):  # EDGE-03
        order = make_order(self.company, date(2026, 3, 1))
        FiscalPeriodModel.objects.filter(pk=self.p2026.id).update(name='Renombrado')
        self.assertEqual(DjangoOrderRepository(self.company.id).get(order.id).number.period_name, 'Gestión 2026')

    def test_no_period_for_the_date_blocks_and_leaves_the_counter_untouched(self):  # AC-05
        order = make_order(self.company, date(2028, 1, 1), confirm=False)
        repository = DjangoOrderRepository(self.company.id)
        with self.assertRaises(OrderRuleViolation) as caught, transaction.atomic():
            StartOrderPreparation(repository, OrderNumberingAdapter(self.company.id)).execute(order.id)
        self.assertEqual(caught.exception.code, 'fiscal_period_missing')
        self.assertEqual(repository.get(order.id).status.value, 'NEW')
        self.assertFalse(OrderNumberCounterModel.objects.filter(company_id=self.company.id).exists())

    def test_a_closed_period_blocks_and_a_reopened_one_continues_the_series(self):  # AC-06, EDGE-05
        make_order(self.company, date(2026, 3, 1))
        FiscalPeriodModel.objects.filter(pk=self.p2026.id).update(status='CLOSED')
        order = make_order(self.company, date(2026, 3, 2), confirm=False)
        repository = DjangoOrderRepository(self.company.id)
        with self.assertRaises(OrderRuleViolation) as caught, transaction.atomic():
            StartOrderPreparation(repository, OrderNumberingAdapter(self.company.id)).execute(order.id)
        self.assertEqual(caught.exception.code, 'fiscal_period_closed')
        FiscalPeriodModel.objects.filter(pk=self.p2026.id).update(status='OPEN')
        with transaction.atomic():
            confirmed = StartOrderPreparation(repository, OrderNumberingAdapter(self.company.id)).execute(order.id)
        self.assertEqual(confirmed.code, 'NV-000002')

    def test_a_failure_after_numbering_rolls_the_counter_back(self):  # AC-09, INV-02
        order = make_order(self.company, date(2026, 3, 1), confirm=False)
        repository = DjangoOrderRepository(self.company.id)
        with self.assertRaises(RuntimeError), transaction.atomic():
            StartOrderPreparation(repository, OrderNumberingAdapter(self.company.id)).execute(order.id)
            raise RuntimeError('falla posterior a numerar')
        self.assertEqual(repository.get(order.id).status.value, 'NEW')
        self.assertEqual(make_order(self.company, date(2026, 3, 2)).code, 'NV-000001')

    def test_the_database_rejects_a_duplicate_number(self):  # INV-01
        order = make_order(self.company, date(2026, 3, 1))
        twin = make_order(self.company, date(2026, 3, 2), confirm=False)
        with self.assertRaises(IntegrityError), transaction.atomic():
            OrderModel.objects.filter(pk=twin.id).update(
                fiscal_period_id=order.number.period_id, fiscal_period_name='Gestión 2026', number=order.number.number)

    def test_number_and_period_go_together(self):  # INV-01
        twin = make_order(self.company, date(2026, 3, 2), confirm=False)
        with self.assertRaises(IntegrityError), transaction.atomic():
            OrderModel.objects.filter(pk=twin.id).update(number=5)


class ApiTests(APITestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        authenticate(self.client, make_admin(self.company, username='ana'))
        self.product = ProductModel.objects.create(
            company_id=self.company.id, name='Pack', description='', sale_price=Decimal('35.00'), active=True,
            can_sell=True)

    def start(self, order_date):
        body = {'sales_channel': 'WHATSAPP', 'order_date': order_date,
                'items': [{'product_id': str(self.product.id), 'quantity': 2}]}
        return self.client.post(LIST_URL + 'start/', body, format='json')

    def test_a_new_order_shows_the_provisional_code_and_no_period(self):  # AC-02, AC-11
        make_period(self.company, 'Gestión 2026', date(2026, 1, 1), date(2026, 12, 31))
        created = self.client.post(LIST_URL, {'sales_channel': 'WHATSAPP', 'order_date': '2026-03-01'},
                                   format='json').json()
        self.assertTrue(created['code'].startswith('P-'))
        self.assertEqual((created['number'], created['fiscal_period']), (None, None))

    def test_prepare_assigns_the_number_and_detail_and_list_expose_it(self):  # AC-01, AC-11, API-01
        period = make_period(self.company, 'Gestión 2026', date(2026, 1, 1), date(2026, 12, 31))
        created = self.client.post(LIST_URL, {'sales_channel': 'WHATSAPP', 'order_date': '2026-03-01'},
                                   format='json').json()
        self.client.post(f"{LIST_URL}{created['id']}/items/", {'product_id': str(self.product.id), 'quantity': 1},
                         format='json')
        prepared = self.client.post(f"{LIST_URL}{created['id']}/prepare/", {}, format='json')
        self.assertEqual(prepared.status_code, 200, prepared.content)
        body = prepared.json()
        self.assertEqual((body['code'], body['number'], body['fiscal_period']),
                         ('NV-000001', 1, {'id': str(period.id), 'name': 'Gestión 2026'}))
        row = self.client.get(LIST_URL).json()['results'][0]
        self.assertEqual((row['code'], row['number'], row['fiscal_period']['name']), ('NV-000001', 1, 'Gestión 2026'))

    def test_start_creates_a_numbered_order(self):  # AC-10
        make_period(self.company, 'Gestión 2026', date(2026, 1, 1), date(2026, 12, 31))
        response = self.start('2026-03-01')
        self.assertEqual((response.status_code, response.json()['code']), (201, 'NV-000001'))
        self.assertEqual(self.start('2026-03-02').json()['code'], 'NV-000002')

    def test_start_without_period_is_a_409_and_creates_nothing(self):  # AC-05, AC-10, API-02
        response = self.start('2026-03-01')
        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual(response.json()['code'], 'fiscal_period_missing')
        self.assertEqual(OrderModel.objects.filter(company_id=self.company.id).count(), 0)

    def test_start_in_a_closed_period_is_a_409(self):  # AC-06, API-02
        make_period(self.company, 'Gestión 2026', date(2026, 1, 1), date(2026, 12, 31), status='CLOSED')
        response = self.start('2026-03-01')
        self.assertEqual((response.status_code, response.json()['code']), (409, 'fiscal_period_closed'))
        self.assertEqual(response.json()['period'], 'Gestión 2026')  # la UI nombra el período cerrado
        self.assertEqual(OrderModel.objects.filter(company_id=self.company.id).count(), 0)

    def test_prepare_without_period_is_a_409_and_the_order_stays_new(self):  # AC-05, API-02
        created = self.client.post(LIST_URL, {'sales_channel': 'WHATSAPP', 'order_date': '2026-03-01'},
                                   format='json').json()
        self.client.post(f"{LIST_URL}{created['id']}/items/", {'product_id': str(self.product.id), 'quantity': 1},
                         format='json')
        response = self.client.post(f"{LIST_URL}{created['id']}/prepare/", {}, format='json')
        self.assertEqual((response.status_code, response.json()['code']), (409, 'fiscal_period_missing'))
        self.assertEqual(self.client.get(f"{LIST_URL}{created['id']}/").json()['status'], 'NEW')

    def test_the_return_preview_uses_the_numbered_code(self):  # API-03, AC-11
        make_period(self.company, 'Gestión 2026', date(2026, 1, 1), date(2026, 12, 31))
        order = self.start('2026-03-01').json()
        for action in ('ready', 'deliver'):
            response = self.client.post(f"{LIST_URL}{order['id']}/{action}/", {}, format='json')
            self.assertEqual(response.status_code, 200, response.content)
        preview = self.client.get(f"{LIST_URL}{order['id']}/return-preview/")
        self.assertEqual((preview.status_code, preview.json()['order_code']), (200, 'NV-000001'))

    def test_the_delivery_entry_description_carries_the_period(self):  # AC-11
        make_period(self.company, 'Gestión 2026', date(2026, 1, 1), date(2026, 12, 31))
        order = make_order(self.company, date(2026, 3, 1))
        self.assertEqual(_period_suffix(order), ' (Gestión 2026)')
        self.assertEqual(_period_suffix(Order.create('WHATSAPP', date(2026, 3, 1))), '')
