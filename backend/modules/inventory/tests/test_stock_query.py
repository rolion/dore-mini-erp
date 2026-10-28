"""Consulta de existencias: lista con filtros y detalle por producto y almacén (PB-INV-005)."""
from decimal import Decimal
from uuid import UUID, uuid4

from django.test import SimpleTestCase
from rest_framework.test import APIClient

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.inventory.domain.stock import BalanceState, balance_state
from modules.inventory.services import get_balance, record_movement, reverse_movement
from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
from modules.modularity.tests.test_enforcement import set_enabled

from .test_stock import STOCK, StockApiTestCase, line


class BalanceStateTests(SimpleTestCase):
    def test_state_is_derived_from_quantity(self):  # INV-04
        self.assertIs(balance_state(Decimal('0')), BalanceState.ZERO)
        self.assertIs(balance_state(Decimal('0.0001')), BalanceState.POSITIVE)
        self.assertIs(balance_state(Decimal('-1')), BalanceState.NEGATIVE)


class StockQueryTests(StockApiTestCase):
    def move(self, product, kind, quantity, allow_negative=False):
        return record_movement(
            self.company.id, product_id=UUID(product), warehouse_id=UUID(self.warehouse), kind=kind,
            quantity=Decimal(quantity), user_id=None, user_name='ana', allow_negative=allow_negative)[0]

    def rows(self, **params):
        response = self.client.get(STOCK, params)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()['results']

    def test_product_without_movements_is_listed_with_zero_balance(self):  # AC-01
        product = self.make_product('Harina')
        self.make_product('Servicio', tracks=False)  # EDGE-01
        rows = self.rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['product_id'], product)
        self.assertEqual((rows[0]['quantity'], rows[0]['balance_state']), ('0.0000', 'zero'))
        self.assertEqual(rows[0]['unit'], {'abbreviation': 'u', 'allows_fractions': False})
        self.assertNotIn('available', rows[0])
        self.assertNotIn('reserved', rows[0])

    def test_rows_are_ordered_by_product_name_then_warehouse(self):
        self.make_product('Sal')
        self.make_product('Azúcar')
        self.client.post('/api/warehouses/', {'name': 'Tienda'}, format='json')
        order = [(r['product_name'], r['warehouse_name']) for r in self.rows()]
        self.assertEqual(order, [('Azúcar', 'Almacén principal'), ('Azúcar', 'Tienda'),
                                 ('Sal', 'Almacén principal'), ('Sal', 'Tienda')])

    def test_search_is_case_insensitive(self):  # AC-02
        self.make_product('Harina de trigo')
        self.make_product('Sal')
        self.assertEqual([r['product_name'] for r in self.rows(search='HARINA')], ['Harina de trigo'])

    def test_active_filter_defaults_to_active_and_keeps_inactive_history(self):  # AC-02, INV-02
        active = self.make_product('Activo')
        old = self.make_product('Viejo')
        self.open([line(old, '3')])
        self.assertEqual(self.client.post(f'/api/products/{old}/deactivate/').status_code, 200)
        self.assertEqual([r['product_id'] for r in self.rows()], [active])
        inactive = self.rows(active='false')
        self.assertEqual([(r['product_id'], r['quantity'], r['product_active']) for r in inactive],
                         [(old, '3.0000', False)])
        self.assertEqual(len(self.rows(active='all')), 2)

    def test_balance_filters_zero_nonzero_and_negative(self):  # AC-02, EDGE-06
        positive, zero, negative = (self.make_product(n) for n in ('Positivo', 'Cero', 'Negativo'))
        self.open([line(positive, '5')])
        self.move(negative, 'out', '2', allow_negative=True)
        names = lambda **kw: [r['product_name'] for r in self.rows(**kw)]  # noqa: E731
        self.assertEqual(names(balance='zero'), ['Cero'])
        self.assertEqual(names(balance='nonzero'), ['Negativo', 'Positivo'])
        self.assertEqual(names(balance='negative'), ['Negativo'])
        negative_row = self.rows(balance='negative')[0]
        self.assertEqual((negative_row['quantity'], negative_row['balance_state']), ('-2.0000', 'negative'))
        self.assertEqual([r['product_id'] for r in self.rows(balance='zero')], [zero])

    def test_warehouse_filter_and_inactive_warehouse(self):  # EDGE-02
        self.make_product('Harina')
        other = self.client.post('/api/warehouses/', {'name': 'Tienda'}, format='json').json()['id']
        self.assertEqual(self.client.post(f'/api/warehouses/{other}/deactivate/').status_code, 200)
        self.assertEqual({r['warehouse_name'] for r in self.rows()}, {'Almacén principal'})
        chosen = self.rows(warehouse_id=other)
        self.assertEqual([(r['warehouse_name'], r['warehouse_active']) for r in chosen], [('Tienda', False)])
        self.assertEqual(self.client.get(STOCK, {'warehouse_id': str(uuid4())}).status_code, 404)

    def test_invalid_parameters_return_400_per_parameter(self):  # EDGE-03
        response = self.client.get(STOCK, {'active': 'x', 'balance': 'y', 'warehouse_id': 'z'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {'active', 'balance', 'warehouse_id'})

    def test_empty_company_returns_empty_list(self):  # EDGE-05
        self.assertEqual(self.client.get(STOCK).json()['count'], 0)

    def test_list_and_detail_balance_equal_ledger_sum_including_reversal(self):  # AC-08, EDGE-04
        product = self.make_product('Harina')
        self.open([line(product, '10')])
        out = self.move(product, 'out', '4')
        reverse_movement(self.company.id, out.id, user_id=None, user_name='ana')
        self.move(product, 'out', '3')
        expected = '7.0000'
        self.assertEqual(self.rows()[0]['quantity'], expected)
        detail = self.client.get(f'{STOCK}{product}/{self.warehouse}/').json()
        self.assertEqual(detail['quantity'], expected)
        self.assertEqual(get_balance(self.company.id, UUID(product), UUID(self.warehouse)), Decimal('7'))
        history = self.client.get('/api/stock-movements/', {'product_id': product, 'warehouse_id': self.warehouse})
        signed = sum(Decimal(m['quantity_in'] or 0) - Decimal(m['quantity_out'] or 0)
                     for m in history.json()['results'])
        # El contramovimiento anula la salida revertida: el historial completo suma lo mismo que el saldo.
        self.assertEqual(signed, Decimal(expected))


class StockDetailTests(StockApiTestCase):
    def test_detail_without_movements_is_zero_and_allows_opening(self):  # AC-04, AC-05
        product = self.make_product('Harina')
        response = self.client.get(f'{STOCK}{product}/{self.warehouse}/')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual((body['quantity'], body['balance_state'], body['has_history']), ('0.0000', 'zero', False))
        self.assertTrue(body['can_register_opening'])

    def test_opening_is_not_offered_with_history_or_inactive_product(self):  # INV-05
        used, retired = self.make_product('Usado'), self.make_product('Retirado')
        self.open([line(used, '2')])
        self.assertEqual(self.client.post(f'/api/products/{retired}/deactivate/').status_code, 200)
        with_history = self.client.get(f'{STOCK}{used}/{self.warehouse}/').json()
        self.assertEqual((with_history['has_history'], with_history['can_register_opening']), (True, False))
        inactive = self.client.get(f'{STOCK}{retired}/{self.warehouse}/')
        self.assertEqual(inactive.status_code, 200)
        self.assertFalse(inactive.json()['can_register_opening'])

    def test_unknown_or_untracked_product_and_unknown_warehouse_are_404(self):  # EDGE-01
        untracked = self.make_product('Servicio', tracks=False)
        self.assertEqual(self.client.get(f'{STOCK}{untracked}/{self.warehouse}/').status_code, 404)
        self.assertEqual(self.client.get(f'{STOCK}{uuid4()}/{self.warehouse}/').status_code, 404)
        tracked = self.make_product('Harina')
        self.assertEqual(self.client.get(f'{STOCK}{tracked}/{uuid4()}/').status_code, 404)

    def test_other_company_cannot_read_list_or_detail(self):  # AC-07, INV-03
        product = self.make_product('Harina')
        self.open([line(product, '5')])
        other = make_company('Empresa B')
        client = APIClient()
        authenticate(client, make_admin(other, username='beto'))
        set_enabled(other, [*DEFAULT_ENABLED_KEYS, 'inventory'])
        self.assertEqual(client.get(STOCK).json()['count'], 0)
        self.assertEqual(client.get(f'{STOCK}{product}/{self.warehouse}/').status_code, 404)
