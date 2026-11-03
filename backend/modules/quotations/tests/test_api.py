from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from unittest import mock

from django.db import connections
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from modules.accounts.testing import make_admin
from modules.customers.infrastructure.django.models import CustomerModel
from modules.modularity.infrastructure.django.repositories import DjangoCompanyModuleRepository
from modules.quotations.infrastructure.django.models import ProformaLineModel, ProformaModel
from modules.sales.infrastructure.django.models import OrderModel
from modules.service_catalog.infrastructure.django.models import ServiceModel

URL = '/api/quotations/proformas/'


class ProformaApiTests(TransactionTestCase):
    def setUp(self):
        self.admin = make_admin(username='quote-admin')
        self.other = make_admin(username='quote-other')
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        modules = DjangoCompanyModuleRepository(self.admin.company_id)
        modules.enabled_keys()
        for key in ('catalog', 'services', 'quotations'):
            modules.enable(key)
        company = self.admin.company_id
        self.customer = CustomerModel.objects.create(company_id=company, name='Rosa Pérez')
        self.limpieza = ServiceModel.objects.create(
            company_id=company, name='Limpieza', base_price=Decimal('100.00'), duration_minutes=30)
        self.corona = ServiceModel.objects.create(
            company_id=company, name='Corona', base_price=Decimal('150.00'), duration_minutes=60)

    def payload(self, lines=None, **extra):
        lines = lines if lines is not None else [
            {'service_id': str(self.limpieza.pk), 'quantity': '1'},
            {'service_id': str(self.corona.pk), 'quantity': '1'}]
        return {'customer_id': str(self.customer.pk), 'date': '2026-11-03', 'lines': lines, **extra}

    def create(self, **kwargs):
        return self.client.post(URL, self.payload(**kwargs), format='json')

    # AC-01
    def test_total_is_server_calculated_and_frozen_after_catalog_changes(self):
        response = self.create(total='1', lines=[
            {'service_id': str(self.limpieza.pk), 'quantity': '1', 'subtotal': '9'},
            {'service_id': str(self.corona.pk), 'quantity': '1'}])
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual((body['total'], body['number'], body['version'], body['status'], body['currency']),
                         ('250.00', 'PRO-000001', 1, 'draft', 'BOB'))
        self.assertEqual([l['description'] for l in body['lines']], ['Limpieza', 'Corona'])
        ServiceModel.objects.filter(pk=self.limpieza.pk).update(name='Otro', base_price=Decimal('999'), active=False)
        again = self.client.get(f"{URL}{body['id']}/").json()
        self.assertEqual((again['total'], again['lines'][0]['description'], again['lines'][0]['unit_price']),
                         ('250.00', 'Limpieza', '100.00'))
        updated = self.client.put(f"{URL}{body['id']}/", self.payload(lines=again['lines']), format='json')
        self.assertEqual(updated.status_code, 200, updated.content)
        self.assertEqual(updated.json()['total'], '250.00')

    # AC-02
    def test_invalid_quantity_and_price_are_rejected_per_line(self):
        for quantity, price in (('0', None), ('-1', None), ('1', '-5')):
            line = {'service_id': str(self.limpieza.pk), 'quantity': quantity}
            if price is not None:
                line['unit_price'] = price
            response = self.create(lines=[{'service_id': str(self.corona.pk), 'quantity': '1'}, line])
            self.assertEqual(response.status_code, 400, (quantity, price))
            self.assertTrue(response.json()['lines'][1])
        self.assertEqual(ProformaModel.objects.count(), 0)

    # AC-03
    def test_price_override_requires_permission(self):
        line = {'service_id': str(self.limpieza.pk), 'quantity': '2', 'unit_price': '80.00'}
        ok = self.create(lines=[line])
        self.assertEqual(ok.status_code, 201, ok.content)
        self.assertEqual(ok.json()['total'], '160.00')
        with mock.patch('modules.quotations.api.views.can_edit_price', return_value=False):
            denied = self.create(lines=[line])
            self.assertEqual(denied.status_code, 403)
            same_price = self.create(lines=[{**line, 'unit_price': '100.00'}])
            self.assertEqual(same_price.status_code, 201)
            self.assertFalse(same_price.json()['can_edit_price'])
        self.assertEqual(ProformaModel.objects.count(), 2)

    # AC-04
    def test_inactive_or_foreign_service_and_customer_are_rejected(self):
        ServiceModel.objects.filter(pk=self.corona.pk).update(active=False)
        foreign = ServiceModel.objects.create(company_id=self.other.company_id, name='Ajeno',
                                              base_price=Decimal('1'), duration_minutes=10)
        for service in (self.corona, foreign):
            response = self.create(lines=[{'service_id': str(service.pk), 'quantity': '1'}])
            self.assertEqual(response.status_code, 400)
        CustomerModel.objects.filter(pk=self.customer.pk).update(active=False)
        self.assertEqual(self.create().status_code, 400)
        stranger = CustomerModel.objects.create(company_id=self.other.company_id, name='Ajeno')
        self.assertEqual(self.client.post(URL, self.payload(customer_id=str(stranger.pk)), format='json')
                         .status_code, 400)

    # AC-05
    def test_present_needs_lines_then_freezes(self):
        empty = self.create(lines=[]).json()
        self.assertEqual(self.client.post(f"{URL}{empty['id']}/present/").status_code, 400)
        body = self.create().json()
        presented = self.client.post(f"{URL}{body['id']}/present/")
        self.assertEqual((presented.status_code, presented.json()['status']), (200, 'presented'))
        self.assertEqual(self.client.put(f"{URL}{body['id']}/", self.payload(), format='json').status_code, 409)
        self.assertEqual(self.client.post(f"{URL}{body['id']}/present/").status_code, 409)

    # AC-06
    def test_saving_repeatedly_creates_no_sale_or_stock(self):
        body = self.create().json()
        for _ in range(3):
            self.client.put(f"{URL}{body['id']}/", self.payload(lines=body['lines']), format='json')
        self.client.post(f"{URL}{body['id']}/present/")
        self.assertEqual(OrderModel.objects.count(), 0)
        self.assertEqual(ProformaModel.objects.count(), 1)
        self.assertEqual(ProformaLineModel.objects.count(), 2)

    # AC-07
    def test_numbering_is_per_company_and_unique_under_concurrency(self):
        workers = 4
        barrier = Barrier(workers)

        def create_one(_):
            client = APIClient()
            client.force_authenticate(self.admin)
            barrier.wait()
            try:
                return client.post(URL, self.payload(), format='json').json()['number']
            finally:
                connections.close_all()

        with ThreadPoolExecutor(workers) as pool:
            numbers = list(pool.map(create_one, range(workers)))
        self.assertEqual(sorted(numbers), [f'PRO-{n:06d}' for n in range(1, workers + 1)])
        other_client = APIClient()
        other_client.force_authenticate(self.other)
        modules = DjangoCompanyModuleRepository(self.other.company_id)
        modules.enabled_keys()
        for key in ('catalog', 'services', 'quotations'):
            modules.enable(key)
        mine = CustomerModel.objects.create(company_id=self.other.company_id, name='B')
        svc = ServiceModel.objects.create(company_id=self.other.company_id, name='S',
                                          base_price=Decimal('1'), duration_minutes=5)
        response = other_client.post(URL, {'customer_id': str(mine.pk), 'date': '2026-11-03', 'lines': [
            {'service_id': str(svc.pk), 'quantity': '1'}]}, format='json')
        self.assertEqual(response.json()['number'], 'PRO-000001')

    # AC-08
    def test_new_version_flow(self):
        body = self.create().json()
        self.assertEqual(self.client.post(f"{URL}{body['id']}/new-version/").status_code, 409)
        self.client.post(f"{URL}{body['id']}/present/")
        ServiceModel.objects.filter(pk=self.limpieza.pk).update(base_price=Decimal('500'))
        nxt = self.client.post(f"{URL}{body['id']}/new-version/")
        self.assertEqual(nxt.status_code, 201, nxt.content)
        draft = nxt.json()
        self.assertEqual((draft['number'], draft['version'], draft['status'], draft['total']),
                         (body['number'], 2, 'draft', '250.00'))
        self.assertEqual(self.client.post(f"{URL}{body['id']}/new-version/").status_code, 409)
        self.assertEqual(self.client.post(f"{URL}{draft['id']}/present/").status_code, 200)
        first = self.client.get(f"{URL}{body['id']}/").json()
        self.assertEqual(first['status'], 'superseded')
        self.assertEqual([(v['version'], v['status']) for v in first['versions']],
                         [(1, 'superseded'), (2, 'presented')])
        self.assertEqual(first['allowed_actions'], [])

    # AC-09
    def test_list_filters_pagination_and_company_isolation(self):
        first = self.create().json()
        self.client.post(f"{URL}{first['id']}/present/")
        self.create()
        make_other = CustomerModel.objects.create(company_id=self.other.company_id, name='Rosa Pérez')
        ProformaModel.objects.create(company_id=self.other.company_id, number='PRO-000001', customer_id=make_other.pk,
                                     customer_name='Rosa Pérez', date='2026-11-03')
        self.assertEqual(self.client.get(URL).json()['count'], 2)
        self.assertEqual(self.client.get(URL, {'status': 'presented'}).json()['count'], 1)
        self.assertEqual(self.client.get(URL, {'customer': 'rosa'}).json()['count'], 2)
        self.assertEqual(self.client.get(URL, {'customer': 'zzz'}).json()['count'], 0)
        self.assertEqual(self.client.get(URL, {'from': '2026-11-04'}).json()['count'], 0)
        self.assertEqual(self.client.get(URL, {'to': '2026-11-03'}).json()['count'], 2)
        self.assertEqual(self.client.get(URL, {'status': 'x'}).status_code, 400)
        self.assertEqual(self.client.get(URL, {'from': 'nope'}).status_code, 400)
        self.assertEqual(self.client.get(URL, {'page_size': '0'}).status_code, 400)
        self.assertEqual(self.client.get(URL, {'page_size': '1'}).json()['results'][0]['total'], '250.00')
        detail = self.client.get(f"{URL}{first['id']}/").json()
        self.assertEqual(detail['allowed_actions'], ['new-version'])
        foreign = ProformaModel.objects.get(company_id=self.other.company_id)
        self.assertEqual(self.client.get(f'{URL}{foreign.pk}/').status_code, 404)
        self.assertEqual(self.client.post(f'{URL}{foreign.pk}/present/').status_code, 404)

    # AC-10
    def test_module_disabled_returns_403(self):
        DjangoCompanyModuleRepository(self.admin.company_id).disable('quotations')
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['code'], 'module_disabled')
