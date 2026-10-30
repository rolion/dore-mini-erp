from uuid import uuid4

from django.apps import apps

from modules.accounts.testing import make_company
from modules.modularity.infrastructure.django.models import CompanyModuleModel
from modules.purchases.infrastructure.django.models import PurchaseModel, SupplierModel
from modules.purchases.tests.test_purchase_api import (
    DETAIL_FIELDS,
    LIST_URL,
    PurchaseApiTestCase,
    detail_url,
)


def action_url(purchase_id, action):
    return f'{LIST_URL}{purchase_id}/{action}/'


class ConfirmPurchaseApiTests(PurchaseApiTestCase):
    def confirm(self, purchase_id):
        return self.client.post(action_url(purchase_id, 'confirm'), format='json')

    def test_confirm_locks_the_purchase(self):  # AC-01, AC-03
        purchase = self.create()
        response = self.confirm(purchase['id'])
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual((body['status'], body['editable'], body['allowed_actions']), ('confirmed', False, ['receive', 'cancel']))
        self.assertEqual((body['reception_status'], body['payment_status']), ('not_received', 'unpaid'))
        self.assertIsNotNone(body['confirmed_at'])
        self.assertRegex(body['reference'], r'^COM-[0-9A-F]{8}$')
        patch = self.client.patch(detail_url(purchase['id']), {'items': []}, format='json')
        self.assertEqual(patch.status_code, 409)
        self.assertEqual(self.client.get(detail_url(purchase['id'])).json()['items'][0]['unit_price'], '10.00')

    def test_confirm_requires_items_and_active_supplier(self):  # AC-02
        purchase = self.create(items=[])
        SupplierModel.objects.filter(pk=self.supplier.id).update(active=False)
        response = self.confirm(purchase['id'])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {'items', 'supplier_id'})
        self.assertEqual(self.client.get(detail_url(purchase['id'])).json()['status'], 'draft')

    def test_confirm_moves_no_stock_and_is_idempotent(self):  # AC-04, INV-09
        movements = apps.get_model('inventory', 'StockMovementModel')
        expenses = apps.get_model('expenses', 'ExpenseModel')
        purchase = self.create()
        first = self.confirm(purchase['id']).json()
        second = self.confirm(purchase['id'])
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()['confirmed_at'], first['confirmed_at'])
        self.assertEqual((movements.objects.count(), expenses.objects.count()), (0, 0))

    def test_confirm_a_cancelled_purchase_is_409(self):  # AC-09
        purchase = self.create()
        self.client.post(action_url(purchase['id'], 'cancel'), {'reason': 'x'}, format='json')
        response = self.confirm(purchase['id'])
        self.assertEqual((response.status_code, response.json()['detail']),
                         (409, 'Una compra cancelada no puede confirmarse.'))


class CancelPurchaseApiTests(PurchaseApiTestCase):
    def cancel(self, purchase_id, **body):
        return self.client.post(action_url(purchase_id, 'cancel'), body, format='json')

    def test_cancel_a_draft_with_a_reason(self):  # AC-05
        purchase = self.create()
        response = self.cancel(purchase['id'], reason='  Pedido duplicado ')
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual((body['status'], body['cancellation_reason'], body['allowed_actions'], body['editable']),
                         ('cancelled', 'Pedido duplicado', [], False))
        self.assertIsNotNone(body['cancelled_at'])
        self.assertEqual(self.client.patch(detail_url(purchase['id']), {'notes': 'x'}, format='json').status_code, 409)

    def test_cancel_a_confirmed_purchase_without_activity(self):  # AC-06
        purchase = self.create()
        self.client.post(action_url(purchase['id'], 'confirm'))
        self.assertEqual(self.cancel(purchase['id'], reason='Ya no se necesita').json()['status'], 'cancelled')

    def test_reason_is_required_and_limited(self):  # AC-07
        purchase = self.create()
        for body in ({}, {'reason': ''}, {'reason': '   '}, {'reason': None}, {'reason': 'x' * 501}):
            response = self.cancel(purchase['id'], **body)
            self.assertEqual(response.status_code, 400, body)
            self.assertIn('reason', response.json())
        self.assertEqual(self.client.get(detail_url(purchase['id'])).json()['status'], 'draft')

    def test_activity_blocks_the_cancellation(self):  # AC-08
        purchase = self.create()
        self.client.post(action_url(purchase['id'], 'confirm'))
        PurchaseModel.objects.filter(pk=purchase['id']).update(reception_status='partial')
        response = self.cancel(purchase['id'], reason='x')
        self.assertEqual(response.status_code, 409)
        self.assertIn('recepciones o pagos', response.json()['detail'])
        body = self.client.get(detail_url(purchase['id'])).json()
        self.assertEqual((body['status'], body['allowed_actions']), ('confirmed', ['receive']))

    def test_repeating_keeps_the_original_reason(self):  # AC-09
        purchase = self.create()
        first = self.cancel(purchase['id'], reason='Primera').json()
        second = self.cancel(purchase['id'], reason='Otra')
        self.assertEqual(second.status_code, 200)
        self.assertEqual((second.json()['cancellation_reason'], second.json()['cancelled_at']),
                         ('Primera', first['cancelled_at']))


class LifecycleContractTests(PurchaseApiTestCase):
    def test_detail_exposes_the_lifecycle_fields(self):  # AC-10
        purchase = self.create()
        self.assertEqual(set(purchase), DETAIL_FIELDS)
        self.assertEqual(purchase['allowed_actions'], ['edit', 'confirm', 'cancel'])
        self.assertEqual(purchase['cancellation_reason'], '')

    def test_list_reflects_the_status(self):  # AC-10
        purchase = self.create()
        self.client.post(action_url(purchase['id'], 'confirm'))
        self.assertEqual(self.client.get(LIST_URL).json()['results'][0]['status'], 'confirmed')

    def test_unknown_and_foreign_purchases_are_404(self):  # AC-11
        other = make_company('Empresa B')
        foreign = PurchaseModel.objects.create(company_id=other.id, supplier_id=uuid4(), purchase_date='2026-10-29')
        for purchase_id in (uuid4(), foreign.id):
            for action in ('confirm', 'cancel'):
                response = self.client.post(action_url(purchase_id, action), {'reason': 'x'}, format='json')
                self.assertEqual((response.status_code, response.json()), (404, {'detail': 'Compra no encontrada.'}))

    def test_access_and_methods(self):  # AC-11
        purchase = self.create()
        for action in ('confirm', 'cancel'):
            url = action_url(purchase['id'], action)
            for method in ('get', 'put', 'delete'):
                self.assertEqual(getattr(self.client, method)(url).status_code, 405)
            self.assertEqual(self.client.__class__().post(url).status_code, 401)
        CompanyModuleModel.objects.filter(company_id=self.company.id, module_key='purchases').delete()
        self.assertEqual(self.client.post(action_url(purchase['id'], 'confirm')).status_code, 403)
