"""PB-INV-003 (API-05): filtro `tracks_stock` y `allows_fractions` en la unidad base del producto."""
from rest_framework.test import APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
from modules.modularity.tests.test_enforcement import set_enabled


class ProductStockFilterTests(APITestCase):
    def setUp(self):
        company = make_company('Empresa A')
        authenticate(self.client, make_admin(company, username='ana'))
        set_enabled(company, [*DEFAULT_ENABLED_KEYS, 'inventory'])
        unit = self.client.post(
            '/api/units/', {'name': 'Kilogramo', 'abbreviation': 'kg', 'allows_fractions': True}, format='json').json()
        self.client.post('/api/products/', {
            'name': 'Harina', 'sale_price': '1.00', 'category': 'raw_material', 'tracks_stock': True, 'base_unit_id': unit['id']}, format='json')
        self.client.post('/api/products/', {'name': 'Servicio', 'sale_price': '5.00', 'category': 'finished'}, format='json')

    def names(self, **params):
        return [p['name'] for p in self.client.get('/api/products/', params).json()['results']]

    def test_filter_by_tracks_stock(self):
        self.assertEqual(self.names(tracks_stock='true'), ['Harina'])
        self.assertEqual(self.names(tracks_stock='false'), ['Servicio'])
        self.assertEqual(self.names(), ['Harina', 'Servicio'])
        self.assertEqual(self.client.get('/api/products/', {'tracks_stock': 'x'}).status_code, 400)

    def test_base_unit_exposes_allows_fractions(self):
        harina = self.client.get('/api/products/', {'tracks_stock': 'true'}).json()['results'][0]
        self.assertTrue(harina['base_unit']['allows_fractions'])
