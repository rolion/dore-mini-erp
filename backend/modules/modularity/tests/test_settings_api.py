from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.modularity import services
from modules.modularity.infrastructure.django.models import CompanySettingModel, SettingChangeModel

CHANNEL = 'sales.default_sales_channel'
METHOD = 'sales.default_payment_method'
PERCENT = 'sales.max_discount_percent'


def settings_url(module):
    return f'/api/settings/{module}/'


def history_url(scope):
    return f'/api/settings/{scope}/history/'


class SettingsApiTestCase(APITestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        self.user = make_admin(self.company, username='ana', first_name='Ana', last_name='Pérez')
        authenticate(self.client, self.user)

    def save(self, module='sales', values=None, expected=200):
        response = self.client.patch(settings_url(module), {'settings': values}, format='json')
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()

    def values(self, module='sales'):
        body = self.client.get(settings_url(module)).json()
        return {item['key']: item['value'] for item in body['settings']}


class GetSettingsTests(SettingsApiTestCase):
    def test_initial_values_are_documented_defaults(self):  # AC-02
        body = self.client.get(settings_url('sales')).json()
        self.assertEqual(body['module'], 'sales')
        self.assertEqual([i['key'] for i in body['settings']], [CHANNEL, METHOD, PERCENT])
        percent = body['settings'][2]
        self.assertEqual((percent['value'], percent['default'], percent['kind']), ('100.00', '100.00', 'percent'))
        self.assertEqual((percent['minimum'], percent['maximum']), ('0', '100'))
        self.assertTrue(percent['label'] and percent['description'])
        self.assertEqual(body['settings'][0]['choices'][0], {'value': 'WHATSAPP', 'label': 'WhatsApp'})
        self.assertEqual(self.values(), {CHANNEL: '', METHOD: '', PERCENT: '100.00'})

    def test_modules_without_settings_return_empty_list(self):  # AC-09
        for module in ('purchases', 'inventory', 'customers'):
            self.assertEqual(self.client.get(settings_url(module)).json()['settings'], [])

    def test_unknown_or_base_module_is_404(self):  # EDGE-01
        for module in ('nope', 'catalog', 'access', 'modules'):
            self.assertEqual(self.client.get(settings_url(module)).status_code, 404, module)

    def test_requires_company_admin(self):  # AC-01
        self.client.credentials()
        self.assertIn(self.client.get(settings_url('sales')).status_code, (401, 403))
        no_company = make_admin(None, username='root')
        no_company.company = None
        no_company.save()
        authenticate(self.client, no_company)
        self.assertEqual(self.client.get(settings_url('sales')).status_code, 403)
        self.assertEqual(self.client.get(history_url('sales')).status_code, 403)
        self.assertEqual(self.client.patch(settings_url('sales'), {'settings': {PERCENT: '10'}},
                                           format='json').status_code, 403)

    def test_inactive_company_is_rejected(self):  # AC-01
        self.company.is_active = False
        self.company.save()
        self.assertEqual(self.client.get(settings_url('sales')).status_code, 403)


class SaveSettingsTests(SettingsApiTestCase):
    def test_save_returns_new_values_and_persists(self):  # AC-04
        body = self.save(values={CHANNEL: 'FAIR', PERCENT: '15.5'})
        self.assertEqual({i['key']: i['value'] for i in body['settings']},
                         {CHANNEL: 'FAIR', METHOD: '', PERCENT: '15.50'})
        self.assertEqual(self.values(), {CHANNEL: 'FAIR', METHOD: '', PERCENT: '15.50'})

    def test_partial_update_keeps_other_values(self):
        self.save(values={CHANNEL: 'FAIR'})
        self.save(values={METHOD: 'QR'})
        self.assertEqual(self.values()[CHANNEL], 'FAIR')
        self.assertEqual(self.values()[METHOD], 'QR')

    def test_invalid_values_are_rejected_without_saving_anything(self):  # AC-03, INV-02
        body = self.save(values={CHANNEL: 'FAIR', PERCENT: '101', 'sales.nope': 1}, expected=400)
        self.assertEqual(set(body['settings']), {PERCENT, 'sales.nope'})
        self.assertEqual(self.values(), {CHANNEL: '', METHOD: '', PERCENT: '100.00'})
        self.assertEqual(SettingChangeModel.objects.count(), 0)

    def test_each_invalid_value_gets_a_field_error(self):  # AC-03
        for key, value in ((PERCENT, 'abc'), (PERCENT, '1.005'), (PERCENT, -1), (CHANNEL, 'TELEGRAM'),
                           (METHOD, 'BITCOIN'), (PERCENT, None)):
            body = self.save(values={key: value}, expected=400)
            self.assertTrue(body['settings'][key], (key, value))

    def test_bad_payload_shape(self):  # EDGE-02
        for payload in ({}, {'settings': {}}, {'settings': 'x'}, {'settings': [1]}):
            response = self.client.patch(settings_url('sales'), payload, format='json')
            self.assertEqual(response.status_code, 400, payload)

    def test_float_percent_is_parsed_from_text(self):  # EDGE-08
        self.save(values={PERCENT: 0.1})
        self.assertEqual(self.values()[PERCENT], '0.10')

    def test_module_without_settings_rejects_any_key(self):
        self.save('customers', {'x': 1}, expected=400)

    def test_unknown_module_is_404(self):  # EDGE-01
        self.save('nope', {PERCENT: '1'}, expected=404)
        self.save('catalog', {PERCENT: '1'}, expected=404)

    def test_disabled_module_cannot_be_configured(self):  # AC-11
        self.client.post('/api/modules/reporting/disable/')
        self.client.post('/api/modules/sales/disable/')
        body = self.save(values={PERCENT: '10'}, expected=409)
        self.assertTrue(body['detail'])
        self.assertEqual(CompanySettingModel.objects.count(), 0)

    def test_settings_are_isolated_between_companies(self):  # AC-01, INV-04
        self.save(values={CHANNEL: 'FAIR', PERCENT: '10'})
        other = make_company('Empresa B')
        authenticate(self.client, make_admin(other, username='beto'))
        self.assertEqual(self.values(), {CHANNEL: '', METHOD: '', PERCENT: '100.00'})
        self.assertEqual(self.client.get(history_url('sales')).json()['count'], 0)
        self.save(values={PERCENT: '50'})
        authenticate(self.client, self.user)
        self.assertEqual(self.values()[PERCENT], '10.00')

    def test_company_comes_from_the_user_not_the_client(self):  # INV-04
        other = make_company('Empresa B')
        self.client.patch(settings_url('sales') + f'?company_id={other.id}',
                          {'settings': {PERCENT: '5'}, 'company_id': str(other.id)}, format='json')
        self.assertEqual(CompanySettingModel.objects.filter(company_id=other.id).count(), 0)
        self.assertEqual(CompanySettingModel.objects.filter(company_id=self.company.id).count(), 1)


class SalesFacadeTests(SettingsApiTestCase):
    def test_facade_returns_defaults_then_saved_values(self):
        initial = services.get_sales_settings(self.company.id)
        self.assertEqual((initial.default_sales_channel, initial.default_payment_method, initial.max_discount_percent),
                         ('', '', Decimal('100.00')))
        self.save(values={CHANNEL: 'FAIR', PERCENT: '12'})
        saved = services.get_sales_settings(self.company.id)
        self.assertEqual((saved.default_sales_channel, saved.max_discount_percent), ('FAIR', Decimal('12.00')))
        other = services.get_sales_settings(make_company('Empresa B').id)
        self.assertEqual(other.max_discount_percent, Decimal('100.00'))


class HistoryTests(SettingsApiTestCase):
    def test_changes_are_recorded_with_user_and_values(self):  # AC-04
        self.save(values={CHANNEL: 'FAIR', PERCENT: '15'})
        self.save(values={PERCENT: '20'})
        body = self.client.get(history_url('sales')).json()
        self.assertEqual(body['count'], 3)
        newest = body['results'][0]
        self.assertEqual((newest['setting_key'], newest['setting_label'], newest['old_value'], newest['new_value'],
                          newest['changed_by']),
                         (PERCENT, 'Descuento máximo (% del subtotal)', '15.00 %', '20.00 %', 'Ana Pérez'))
        self.assertTrue(newest['changed_at'])
        channel = next(r for r in body['results'] if r['setting_key'] == CHANNEL)
        self.assertEqual((channel['old_value'], channel['new_value']), ('Sin predeterminado', 'Feria'))
        self.assertEqual([o['key'] for o in body['settings']], [CHANNEL, METHOD, PERCENT])

    def test_no_change_creates_no_record(self):  # AC-04, EDGE-02
        self.save(values={PERCENT: '100'})
        self.save(values={CHANNEL: ''})
        self.assertEqual(self.client.get(history_url('sales')).json()['count'], 0)
        self.save(values={CHANNEL: 'FAIR'})
        self.save(values={CHANNEL: 'FAIR'})
        self.assertEqual(self.client.get(history_url('sales')).json()['count'], 1)

    def test_user_name_is_a_snapshot(self):  # EDGE-04
        self.save(values={CHANNEL: 'FAIR'})
        self.user.first_name = 'Otra'
        self.user.save()
        self.assertEqual(self.client.get(history_url('sales')).json()['results'][0]['changed_by'], 'Ana Pérez')

    def test_username_used_when_no_full_name(self):
        authenticate(self.client, make_admin(self.company, username='sinnombre'))
        self.save(values={CHANNEL: 'STORE'})
        self.assertEqual(self.client.get(history_url('sales')).json()['results'][0]['changed_by'], 'sinnombre')

    def test_filter_by_setting_and_date(self):  # AC-06
        self.save(values={CHANNEL: 'FAIR', PERCENT: '15'})
        row = SettingChangeModel.objects.get(setting_key=CHANNEL)
        row.changed_at = timezone.now() - timedelta(days=10)
        row.save()
        today = timezone.localdate()
        only_channel = self.client.get(history_url('sales'), {'setting': CHANNEL}).json()
        self.assertEqual([r['setting_key'] for r in only_channel['results']], [CHANNEL])
        recent = self.client.get(history_url('sales'), {'date_from': today.isoformat()}).json()
        self.assertEqual([r['setting_key'] for r in recent['results']], [PERCENT])
        old = self.client.get(history_url('sales'), {'date_to': (today - timedelta(days=5)).isoformat()}).json()
        self.assertEqual([r['setting_key'] for r in old['results']], [CHANNEL])
        inclusive = self.client.get(history_url('sales'), {'date_from': today.isoformat(),
                                                           'date_to': today.isoformat()}).json()
        self.assertEqual(inclusive['count'], 1)

    def test_pagination_and_order(self):  # AC-06
        for i in range(25):
            self.save(values={PERCENT: str(i)})
        first = self.client.get(history_url('sales')).json()
        self.assertEqual((first['count'], len(first['results'])), (25, 20))
        self.assertEqual(first['results'][0]['new_value'], '24.00 %')
        second = self.client.get(history_url('sales'), {'page': 2}).json()
        self.assertEqual(len(second['results']), 5)

    def test_invalid_filters(self):  # EDGE-05
        self.assertEqual(self.client.get(history_url('sales'), {'date_from': 'ayer'}).status_code, 400)
        self.assertEqual(self.client.get(history_url('sales'), {'date_from': '2026-02-01',
                                                                'date_to': '2026-01-01'}).status_code, 400)
        self.assertEqual(self.client.get(history_url('nope')).status_code, 404)
        self.assertEqual(self.client.get(history_url('catalog')).status_code, 404)

    def test_empty_history(self):  # EDGE-05
        for scope in ('purchases', 'inventory', 'modules', 'sales'):
            body = self.client.get(history_url(scope)).json()
            self.assertEqual((body['count'], body['results']), (0, []))

    def test_history_does_not_leak_between_companies(self):  # AC-01
        self.save(values={CHANNEL: 'FAIR'})
        authenticate(self.client, make_admin(make_company('Empresa B'), username='beto'))
        self.assertEqual(self.client.get(history_url('sales')).json()['count'], 0)

    def test_module_activation_is_recorded(self):  # AC-05
        self.client.post('/api/modules/inventory/enable/')
        self.client.post('/api/modules/inventory/enable/')  # idempotente: sin registro
        self.client.post('/api/modules/inventory/disable/')
        self.client.post('/api/modules/inventory/disable/')
        body = self.client.get(history_url('modules')).json()
        self.assertEqual(body['count'], 2)
        newest = body['results'][0]
        self.assertEqual((newest['setting_key'], newest['setting_label'], newest['old_value'], newest['new_value']),
                         ('module.inventory', 'Inventario', 'Habilitado', 'Deshabilitado'))
        self.assertEqual((body['results'][1]['old_value'], body['results'][1]['new_value']),
                         ('Deshabilitado', 'Habilitado'))
        self.assertIn({'key': 'module.inventory', 'label': 'Inventario'}, body['settings'])
        self.assertEqual(self.client.get(history_url('modules'), {'setting': 'module.sales'}).json()['count'], 0)

    def test_rejected_module_change_leaves_no_record(self):  # AC-05
        self.client.post('/api/modules/sales/disable/')  # lo requiere Reportes: 409
        self.assertEqual(self.client.get(history_url('modules')).json()['count'], 0)
