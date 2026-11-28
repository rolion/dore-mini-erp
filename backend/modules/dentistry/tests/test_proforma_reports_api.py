from decimal import Decimal
from io import BytesIO
from uuid import uuid4

from django.test import TransactionTestCase
from openpyxl import load_workbook
from rest_framework.test import APIClient

from modules.accounts.testing import make_admin
from modules.customers.infrastructure.django.models import CustomerModel
from modules.dentistry.infrastructure.models import PatientModel
from modules.modularity.infrastructure.django.repositories import DjangoCompanyModuleRepository
from modules.personnel.infrastructure.django.models import ProfessionalModel
from modules.service_catalog.infrastructure.django.models import ServiceModel

ROOT = '/api/dentistry/'
RECEIVABLES = '/api/receivables/'
RECEIVABLE, PAID = f'{ROOT}reports/proformas/receivable/', f'{ROOT}reports/proformas/paid/'


class ProformaReportsApiTests(TransactionTestCase):
    def setUp(self):
        self.admin = make_admin(username='rep-admin')
        self.other = make_admin(username='rep-other')
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.modules = DjangoCompanyModuleRepository(self.admin.company_id)
        self.modules.enabled_keys()
        for key in ('catalog', 'services', 'dentistry', 'receivables'):
            self.modules.enable(key)
        company = self.admin.company_id
        self.doctor = ProfessionalModel.objects.create(company_id=company, name='Dra. Paz', created_by=1, updated_by=1)
        self.service = ServiceModel.objects.create(company_id=company, name='Corona', base_price=Decimal('100.00'),
                                                   duration_minutes=60)

    def patient(self, name, client=None, admin=None):
        admin = admin or self.admin
        customer = CustomerModel.objects.create(company_id=admin.company_id, name=name)
        PatientModel.objects.create(company_id=admin.company_id, customer_id=customer.pk, created_by=admin.pk,
                                    updated_by=admin.pk)
        return customer

    def proforma(self, customer, day='2026-11-04', accept=True, present=True, doctor=None, client=None, service=None):
        client = client or self.client
        service = service or self.service
        body = {'date': day, 'lines': [{'service_id': str(service.pk), 'quantity': '1'}]}
        if doctor:
            body['professional_id'] = str(doctor.pk)
        created = client.post(f'{ROOT}patients/{customer.pk}/proformas/', body, format='json')
        self.assertEqual(created.status_code, 201, created.content)
        p = created.json()
        if present:
            p = client.post(f"{ROOT}proformas/{p['id']}/present/").json()
        if accept:
            r = client.post(f"{ROOT}proformas/{p['id']}/decisions/", {
                'idempotency_key': str(uuid4()), 'decision': 'accepted', 'line_ids': [p['lines'][0]['id']],
                'accepted_by_name': 'X', 'medium': 'in_person'}, format='json')
            self.assertEqual(r.status_code, 201, r.content)
            p = r.json()
        return p

    def pay(self, p, amount, client=None):
        r = (client or self.client).post(f"{RECEIVABLES}commitments/dental/{p['number']}/payments/", {
            'idempotency_key': str(uuid4()), 'amount': amount, 'payment_method': 'CASH',
            'allocations': [{'line_id': p['lines'][0]['id'], 'amount': amount}]}, format='json')
        self.assertEqual(r.status_code, 201, r.content)

    # AC-03, AC-04, AC-06
    def test_receivable_and_paid_lists_split_by_collection(self):
        rosa, luis, ana = self.patient('Rosa'), self.patient('Luis'), self.patient('Ana')
        unpaid = self.proforma(rosa, doctor=self.doctor)
        partial = self.proforma(luis)
        self.pay(partial, '30.00')
        paid = self.proforma(ana, day='2026-11-05')
        self.pay(paid, '100.00')
        self.proforma(rosa, accept=False)                     # presentada sin aceptar: fuera
        self.proforma(rosa, present=False, accept=False)      # borrador: fuera

        receivable = self.client.get(RECEIVABLE).json()
        self.assertEqual({(r['code'], r['amount']) for r in receivable['results']},
                         {(partial['number'], '70.00'), (unpaid['number'], '100.00')})
        self.assertEqual(receivable['totals'], {'count': 2, 'amount': '170.00'})
        row = next(r for r in receivable['results'] if r['code'] == unpaid['number'])
        self.assertEqual(row['doctor'], {'id': str(self.doctor.pk), 'name': 'Dra. Paz'})
        self.assertEqual(row['customer']['name'], 'Rosa')
        self.assertIsNone(next(r for r in receivable['results'] if r['code'] == partial['number'])['doctor'])

        done = self.client.get(PAID).json()
        self.assertEqual([(r['code'], r['amount']) for r in done['results']], [(paid['number'], '100.00')])
        self.assertEqual(done['totals'], {'count': 1, 'amount': '100.00'})

    # AC-05
    def test_date_filter_is_inclusive_and_validated(self):
        customer = self.patient('Rosa')
        early, late = self.proforma(customer, day='2026-10-01'), self.proforma(customer, day='2026-11-20')
        codes = lambda q: [r['code'] for r in self.client.get(RECEIVABLE + q).json()['results']]  # noqa: E731
        self.assertEqual(sorted(codes('')), sorted([early['number'], late['number']]))
        self.assertEqual(codes('?date_from=2026-10-01&date_to=2026-10-01'), [early['number']])
        self.assertEqual(codes('?date_from=2026-11-20'), [late['number']])
        self.assertEqual(codes('?date_to=2026-09-30'), [])
        self.assertEqual(self.client.get(RECEIVABLE + '?date_from=nope').status_code, 400)
        self.assertEqual(self.client.get(RECEIVABLE + '?date_from=2026-11-02&date_to=2026-11-01').status_code, 400)

    # AC-06: los totales son de todo el conjunto, no de la página
    def test_totals_cover_every_page(self):
        customer = self.patient('Rosa')
        for _ in range(3):
            self.proforma(customer)
        page = self.client.get(RECEIVABLE + '?page_size=2').json()
        self.assertEqual((len(page['results']), page['count'], page['totals']),
                         (2, 3, {'count': 3, 'amount': '300.00'}))

    # AC-07
    def test_exports_have_same_rows_and_neutralize_formulas(self):
        customer = self.patient('=SUM(A1)')
        p = self.proforma(customer, doctor=self.doctor)
        xlsx = self.client.get(RECEIVABLE + 'export/xlsx/')
        self.assertEqual(xlsx.status_code, 200)
        self.assertIn('proformas-por-cobrar-', xlsx['Content-Disposition'])
        sheet = load_workbook(BytesIO(xlsx.content)).active
        self.assertEqual([c.value for c in sheet[1]], ['Proforma', 'Paciente', 'Doctor', 'Saldo por cobrar'])
        self.assertEqual([c.value for c in sheet[2]][:3], [p['number'], '=SUM(A1)', 'Dra. Paz'])
        self.assertEqual(sheet['B2'].data_type, 's')
        self.assertEqual((sheet['A3'].value, sheet['B3'].value, sheet['D3'].value),
                         ('Totales', '1 proformas', Decimal('100.00')))
        pdf = self.client.get(PAID + 'export/pdf/')
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        self.assertEqual(self.client.get(PAID + 'export/csv/').status_code, 404)
        self.assertEqual(self.client.get(PAID + 'export/pdf/?date_from=x').status_code, 400)

    def test_export_limit(self):
        from unittest import mock
        self.proforma(self.patient('Rosa'))
        with mock.patch('modules.dentistry.api.proforma_report_views.MAX_EXPORT_ROWS', 0):
            self.assertEqual(self.client.get(RECEIVABLE + 'export/xlsx/').status_code, 400)

    # AC-08
    def test_company_isolation(self):
        other_client = APIClient()
        other_client.force_authenticate(self.other)
        modules = DjangoCompanyModuleRepository(self.other.company_id)
        modules.enabled_keys()
        for key in ('catalog', 'services', 'dentistry', 'receivables'):
            modules.enable(key)
        service = ServiceModel.objects.create(company_id=self.other.company_id, name='X', base_price=Decimal('50.00'),
                                              duration_minutes=30)
        theirs = self.proforma(self.patient('Ajena', admin=self.other), client=other_client, service=service)
        mine = self.proforma(self.patient('Rosa'))
        self.pay(mine, '10.00')
        self.assertEqual([r['code'] for r in self.client.get(RECEIVABLE).json()['results']], [mine['number']])
        self.assertEqual(self.client.get(RECEIVABLE).json()['results'][0]['amount'], '90.00')
        self.assertEqual([r['code'] for r in other_client.get(RECEIVABLE).json()['results']], [theirs['number']])

    # AC-09
    def test_requires_both_modules(self):
        self.modules.disable('receivables')
        self.assertEqual(self.client.get(RECEIVABLE).status_code, 403)
        self.assertEqual(self.client.get(PAID + 'export/pdf/').status_code, 403)
        self.modules.enable('receivables')
        self.modules.disable('dentistry')
        self.assertEqual(self.client.get(PAID).status_code, 403)

    def test_superseded_versions_are_not_listed_twice(self):
        customer = self.patient('Rosa')
        p = self.proforma(customer)
        draft = self.client.post(f"{ROOT}proformas/{p['id']}/new-version/").json()
        self.assertEqual(draft['version'], 2)
        self.assertEqual([r['code'] for r in self.client.get(RECEIVABLE).json()['results']], [p['number']])
