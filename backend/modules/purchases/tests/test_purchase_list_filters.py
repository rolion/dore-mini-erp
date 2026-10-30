"""PB-COM-006: seguimiento y filtros de la lista de compras (BD real)."""
from uuid import uuid4

from modules.accounts.testing import make_company
from modules.purchases.infrastructure.django.models import PurchaseModel, SupplierModel
from modules.purchases.tests.test_payment_api import PaymentApiTestCase
from modules.purchases.tests.test_purchase_api import LIST_URL

SUMMARY_FIELDS = {'id', 'purchase_date', 'supplier', 'external_reference', 'total', 'currency', 'status',
                  'items_count', 'reference', 'reception_status', 'payment_status', 'paid_total', 'balance'}


class PurchaseListFilterTests(PaymentApiTestCase):
    def setUp(self):
        super().setUp()
        self.other_supplier = SupplierModel.objects.create(company_id=self.company.id, name='Otro proveedor')

    def received(self, purchase, status='received'):
        PurchaseModel.objects.filter(pk=purchase['id']).update(reception_status=status)

    def ids(self, **params):
        response = self.client.get(LIST_URL, params)
        self.assertEqual(response.status_code, 200, response.content)
        return {row['id'] for row in response.json()['results']}

    def scenario(self):
        """Borrador, cancelada y cuatro confirmadas con distinta recepción y pago."""
        draft = self.create(purchase_date='2026-10-01')
        cancelled = self.create(purchase_date='2026-10-02')
        self.client.post(f'{LIST_URL}{cancelled["id"]}/cancel/', {'reason': 'error'}, format='json')
        unpaid = self.confirmed_purchase()
        partial = self.confirmed_purchase()
        self.pay(partial, '20.00')
        paid = self.confirmed_purchase()
        self.pay(paid, '50.00')
        received_unpaid = self.confirmed_purchase()
        self.received(received_unpaid)
        self.received(paid, 'partial')
        return {'draft': draft['id'], 'cancelled': cancelled['id'], 'unpaid': unpaid['id'],
                'partial': partial['id'], 'paid': paid['id'], 'received_unpaid': received_unpaid['id']}

    def test_rows_carry_tracking_for_confirmed_purchases_only(self):  # AC-01, AC-06, INV-01
        ids = self.scenario()
        rows = {r['id']: r for r in self.client.get(LIST_URL).json()['results']}
        self.assertEqual(set(rows[ids['unpaid']]), SUMMARY_FIELDS)
        partial = rows[ids['partial']]
        self.assertEqual((partial['reception_status'], partial['payment_status'], partial['paid_total'],
                          partial['balance'], partial['total']), ('not_received', 'partial', '20.00', '30.00', '50.00'))
        self.assertRegex(partial['reference'], r'^COM-[0-9A-F]{8}$')
        self.assertEqual((rows[ids['unpaid']]['paid_total'], rows[ids['unpaid']]['balance']), ('0.00', '50.00'))
        # Recibida e impaga, y pagada pendiente de recepción: estados separados.
        self.assertEqual((rows[ids['received_unpaid']]['reception_status'], rows[ids['received_unpaid']]['payment_status']),
                         ('received', 'unpaid'))
        self.assertEqual((rows[ids['paid']]['reception_status'], rows[ids['paid']]['payment_status'],
                          rows[ids['paid']]['balance']), ('partial', 'paid', '0.00'))
        for key in ('draft', 'cancelled'):
            row = rows[ids[key]]
            self.assertEqual([row[f] for f in ('reception_status', 'payment_status', 'paid_total', 'balance')],
                             [None] * 4)

    def test_filters_by_document_reception_and_payment_status(self):  # AC-02, INV-02
        ids = self.scenario()
        self.assertEqual(self.ids(status='draft'), {ids['draft']})
        self.assertEqual(self.ids(status='cancelled'), {ids['cancelled']})
        self.assertEqual(self.ids(status='confirmed'), {ids[k] for k in ('unpaid', 'partial', 'paid', 'received_unpaid')})
        self.assertEqual(self.ids(reception_status='received'), {ids['received_unpaid']})
        # Sin recibir solo devuelve confirmadas (los borradores no tienen recepción).
        self.assertEqual(self.ids(reception_status='not_received'), {ids['unpaid'], ids['partial']})
        self.assertEqual(self.ids(payment_status='paid'), {ids['paid']})
        self.assertEqual(self.ids(payment_status='unpaid'), {ids['unpaid'], ids['received_unpaid']})

    def test_pending_payment_combined_with_received_returns_received_but_unpaid(self):  # AC-03
        ids = self.scenario()
        self.assertEqual(self.ids(payment_status='pending'),
                         {ids['unpaid'], ids['partial'], ids['received_unpaid']})
        self.assertEqual(self.ids(payment_status='pending', reception_status='received'), {ids['received_unpaid']})

    def test_filters_by_supplier_and_inclusive_date_range(self):  # AC-02
        a = self.create(purchase_date='2026-10-05')
        b = self.create(supplier_id=str(self.other_supplier.id), purchase_date='2026-10-10', items=[])
        c = self.create(purchase_date='2026-10-15')
        self.assertEqual(self.ids(supplier_id=str(self.other_supplier.id)), {b['id']})
        self.assertEqual(self.ids(date_from='2026-10-10'), {b['id'], c['id']})
        self.assertEqual(self.ids(date_to='2026-10-10'), {a['id'], b['id']})
        self.assertEqual(self.ids(date_from='2026-10-10', date_to='2026-10-10'), {b['id']})
        self.assertEqual(self.ids(date_from='2026-10-10', supplier_id=str(self.supplier.id)), {c['id']})

    def test_search_by_external_and_internal_reference(self):  # AC-04
        a = self.create(external_reference='FAC-0042')
        b = self.create(external_reference='remito 7')
        self.assertEqual(self.ids(q='fac-00'), {a['id']})
        self.assertEqual(self.ids(q='  REMITO '), {b['id']})
        internal = a['reference']
        self.assertEqual(self.ids(q=internal), {a['id']})
        self.assertEqual(self.ids(q=internal.lower().removeprefix('com-')[:4]) >= {a['id']}, True)
        self.assertEqual(self.ids(q='   '), {a['id'], b['id']})
        self.assertEqual(self.ids(q='zzz-no'), set())

    def test_invalid_params_are_400_per_field(self):  # AC-05
        for params, field in (({'supplier_id': 'x'}, 'supplier_id'), ({'date_from': '2026-13-01'}, 'date_from'),
                              ({'status': 'zzz'}, 'status'), ({'reception_status': 'pending'}, 'reception_status'),
                              ({'payment_status': 'zzz'}, 'payment_status'), ({'q': 'x' * 101}, 'q'),
                              ({'date_from': '2026-10-10', 'date_to': '2026-10-01'}, 'date_to')):
            response = self.client.get(LIST_URL, params)
            self.assertEqual(response.status_code, 400, params)
            self.assertIn(field, response.json())

    def test_other_company_never_appears_and_count_follows_filters(self):  # AC-02, EDGE-04, INV-03
        mine = self.confirmed_purchase()
        other = make_company('Empresa B')
        PurchaseModel.objects.create(company_id=other.id, supplier_id=uuid4(), purchase_date='2026-10-20',
                                     status='confirmed', total=50)
        body = self.client.get(LIST_URL, {'status': 'confirmed', 'payment_status': 'pending', 'page_size': 1}).json()
        self.assertEqual((body['count'], [r['id'] for r in body['results']]), (1, [mine['id']]))
