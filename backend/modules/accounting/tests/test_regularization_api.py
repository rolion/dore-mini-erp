"""PB-ACC-004: API de regularización (AC-11..AC-14; API-01..03)."""
from datetime import date
from decimal import Decimal
from unittest import mock
from uuid import uuid4

from rest_framework.test import APIClient, APITestCase

from modules.accounting.domain.account import Account
from modules.accounting.infrastructure.django.models import EntryModel
from modules.accounting.infrastructure.django.repositories import DjangoAccountRepository
from modules.accounting.tests.test_entries_api import enable
from modules.accounts.testing import authenticate, make_admin, make_company
from modules.receivables.infrastructure.django.models import ObligationModel
from modules.receivables.infrastructure.django.models import PaymentModel as ServicePayment
from modules.sales.infrastructure.django.models import OrderModel
from modules.sales.infrastructure.django.models import PaymentModel as OrderPayment

PREVIEW = '/api/accounting/regularization/preview/'
APPLY = '/api/accounting/regularization/apply/'
D = date(2026, 3, 10)


class RegularizationApiTests(APITestCase):
    def setUp(self):
        self.company, self.other = make_company('A'), make_company('B')
        enable(self.company, 'accounting')
        enable(self.other, 'accounting')
        self.admin = make_admin(self.company, 'ana', first_name='Ana', last_name='Pérez')
        self.client_a = self.login(self.admin)
        self.client_b = self.login(make_admin(self.other, 'beto'))
        self.caja = DjangoAccountRepository(self.company.id).save(Account.create('Caja', 'BOB'))
        self.mapping = {m: [{'account_id': str(self.caja.id)}] for m in ('CASH', 'QR')}

    @staticmethod
    def login(user):
        client = APIClient()
        authenticate(client, user)
        return client

    def order_payment(self, company=None, status='DELIVERED', amount='100.00'):
        order = OrderModel.objects.create(company_id=(company or self.company).id, status=status,
                                          sales_channel='STORE', order_date=D, payment_status='paid')
        return OrderPayment.objects.create(order=order, amount=Decimal(amount), payment_method='CASH', payment_date=D)

    def service_payment(self):
        obligation = ObligationModel.objects.create(company_id=self.company.id, source_kind='quotation',
                                                    source_number='PF-1', customer_id=uuid4(), customer_name='C')
        from datetime import datetime, timezone
        return ServicePayment.objects.create(
            company_id=self.company.id, obligation=obligation, receipt_number='CB-000001', amount=Decimal('50.00'),
            payment_method='QR', payment_date=D, recorded_by=9, recorded_by_name='Beto', idempotency_key=uuid4(),
            payload_hash='h', created_at=datetime(2026, 3, 10, tzinfo=timezone.utc))

    def body(self, **extra):
        data = {'mapping': self.mapping}
        data.update(extra)
        return data

    def count(self, company=None):
        return EntryModel.objects.filter(company_id=(company or self.company).id).count()

    def test_preview_does_not_write_and_ignores_a_company_in_the_body(self):  # AC-11
        self.order_payment()
        self.order_payment(status='CANCELLED', amount='25.00')
        self.service_payment()
        foreign = self.order_payment(company=self.other)
        response = self.client_a.post(PREVIEW, self.body(company_id=str(self.other.id)), format='json')
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual((data['mode'], data['total_payments']), ('preview', 3))
        missing = [g for g in data['groups'] if g['status'] == 'missing']
        self.assertEqual(sum(g['count'] for g in missing), 3)
        self.assertEqual({g['origin'] for g in missing}, {'PRODUCT', 'SERVICE'})
        self.assertEqual(self.count(), 0)
        self.assertFalse(EntryModel.objects.filter(origin_id=foreign.id).exists())
        company_b = self.client_b.post(PREVIEW, {'mapping': {'CASH': [{'account_id': str(self.caja.id)}]}}, format='json')
        self.assertEqual(company_b.status_code, 400)  # la cuenta de A no existe en B

    def test_apply_requires_confirm_and_records_the_authenticated_user(self):  # AC-12
        payment = self.order_payment()
        self.assertEqual(self.client_a.post(APPLY, self.body(), format='json').status_code, 400)
        self.assertEqual(self.client_a.post(APPLY, self.body(confirm=False), format='json').status_code, 400)
        self.assertEqual(self.count(), 0)
        response = self.client_a.post(APPLY, self.body(confirm=True), format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['mode'], 'apply')
        entry = EntryModel.objects.get(origin_id=payment.id)
        self.assertEqual(entry.regularized_by_name, 'Ana Pérez')
        self.assertIsNotNone(entry.regularized_at)
        again = self.client_a.post(APPLY, self.body(confirm=True), format='json').json()
        self.assertEqual(sum(g['count'] for g in again['groups'] if g['status'] == 'created'), 0)
        self.assertEqual(self.count(), 1)

    def test_permissions_and_module_gate(self):  # AC-13
        self.assertIn(APIClient().post(PREVIEW, self.body(), format='json').status_code, (401, 403))
        member = self.login(make_admin(self.company, 'mario', role='member'))
        self.assertEqual(member.post(PREVIEW, self.body(), format='json').status_code, 403)
        self.assertEqual(member.post(APPLY, self.body(confirm=True), format='json').status_code, 403)
        from modules.modularity.infrastructure.django.models import CompanyModuleModel
        CompanyModuleModel.objects.filter(company_id=self.company.id, module_key='accounting').delete()
        response = self.client_a.post(PREVIEW, self.body(), format='json')
        self.assertEqual((response.status_code, response.json()['code']), (403, 'module_disabled'))

    def test_empty_mapping_previews_everything_as_pending_but_cannot_apply(self):  # AC-14, REV-04
        self.order_payment()
        preview = self.client_a.post(PREVIEW, {'mapping': {}}, format='json')
        self.assertEqual(preview.status_code, 200, preview.content)
        data = preview.json()
        self.assertEqual({g['status'] for g in data['groups']}, {'pending'})
        self.assertEqual(data['details'][0]['currency'], 'BOB')
        apply = self.client_a.post(APPLY, {'mapping': {}, 'confirm': True}, format='json')
        self.assertEqual(apply.status_code, 400)
        self.assertEqual(self.count(), 0)

    def test_validation_errors_and_conflict(self):  # AC-14
        self.order_payment()
        cases = [
            {'mapping': {'XXX': [{'account_id': str(self.caja.id)}]}},
            {'mapping': {'CASH': [{'account_id': str(uuid4())}]}},
            {'mapping': {'CASH': [{'account_id': str(self.caja.id)}, {'account_id': str(self.caja.id), 'from': '2026-01-01'}]}},
            {'mapping': self.mapping, 'date_from': '2026-05-01', 'date_to': '2026-01-01'},
            {'mapping': self.mapping, 'date_from': 'ayer'},
            {},
            {'mapping': {'CASH': []}},
        ]
        for body in cases:
            response = self.client_a.post(PREVIEW, body, format='json')
            self.assertEqual(response.status_code, 400, body)
        with mock.patch('modules.accounting.infrastructure.adapters.DjangoRegularizationLedger.try_lock',
                        return_value=False):
            response = self.client_a.post(APPLY, self.body(confirm=True), format='json')
        self.assertEqual((response.status_code, response.json()['code']), (409, 'regularization_in_progress'))
        self.assertEqual(self.count(), 0)
