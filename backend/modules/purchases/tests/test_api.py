from uuid import uuid4

from rest_framework.test import APIClient, APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
from modules.modularity.infrastructure.django.models import CompanyModuleModel, CompanySettingsModel
from modules.purchases.infrastructure.django.models import SupplierModel

LIST_URL = '/api/suppliers/'
FIELDS = {'id', 'name', 'tax_id', 'phone', 'email', 'notes', 'active', 'created_at', 'updated_at'}


def detail_url(supplier_id, suffix=''):
    return f'/api/suppliers/{supplier_id}/{suffix}'


def enable_purchases(company):
    """Habilita Compras (deshabilitado por defecto) además de los módulos por defecto."""
    CompanySettingsModel.objects.get_or_create(company_id=company.id)
    CompanyModuleModel.objects.filter(company_id=company.id).delete()
    CompanyModuleModel.objects.bulk_create([
        CompanyModuleModel(company_id=company.id, module_key=key) for key in (*DEFAULT_ENABLED_KEYS, 'purchases')
    ])


class SupplierApiTestCase(APITestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        authenticate(self.client, make_admin(self.company, username='ana'))
        enable_purchases(self.company)

    def create(self, name='Distribuidora Sur', **extra):
        response = self.client.post(LIST_URL, {'name': name, **extra}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()


class CreateSupplierTests(SupplierApiTestCase):
    def test_create_with_name_only(self):  # AC-01
        body = self.create(name='  Sur  ')
        self.assertEqual(body['name'], 'Sur')
        self.assertEqual((body['tax_id'], body['phone'], body['email'], body['notes']), ('', '', '', ''))
        self.assertTrue(body['active'])
        self.assertEqual(set(body), FIELDS)
        listed = self.client.get(LIST_URL).json()['results']
        self.assertEqual([s['id'] for s in listed], [body['id']])

    def test_create_with_all_fields_and_ignores_active(self):  # AC-01, INV-03
        body = self.create(tax_id='NIT-1', phone='7654 3210', email='v@sur.com', notes='ok', active=False)
        self.assertEqual((body['tax_id'], body['phone'], body['email'], body['notes']),
                         ('NIT-1', '7654 3210', 'v@sur.com', 'ok'))
        self.assertTrue(body['active'])

    def test_invalid_name(self):  # AC-02
        for name in ('', '   ', 'a' * 151):
            response = self.client.post(LIST_URL, {'name': name}, format='json')
            self.assertEqual(response.status_code, 400, name)
            self.assertIn('name', response.json())
        response = self.client.post(LIST_URL, {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['name'], ['El nombre es obligatorio.'])
        self.assertEqual(SupplierModel.objects.count(), 0)

    def test_field_errors_are_reported_together(self):  # AC-02
        response = self.client.post(
            LIST_URL, {'name': '', 'email': 'mal', 'tax_id': 'x' * 51, 'phone': 'x' * 31, 'notes': 'x' * 2001},
            format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {'name', 'email', 'tax_id', 'phone', 'notes'})
        self.assertEqual(SupplierModel.objects.count(), 0)

    def test_duplicated_name_and_tax_id_are_allowed(self):  # EDGE-03, INV-05
        self.create(tax_id='1')
        self.create(tax_id='1')
        self.assertEqual(SupplierModel.objects.count(), 2)


class UpdateSupplierTests(SupplierApiTestCase):
    def test_patch_updates_only_sent_fields(self):  # AC-03
        body = self.create(tax_id='1', phone='2', email='a@b.com', notes='n')
        response = self.client.patch(detail_url(body['id']), {'name': 'Norte', 'phone': '', 'active': False},
                                     format='json')
        self.assertEqual(response.status_code, 200, response.content)
        updated = response.json()
        self.assertEqual((updated['name'], updated['tax_id'], updated['phone'], updated['email']),
                         ('Norte', '1', '', 'a@b.com'))
        self.assertTrue(updated['active'])
        self.assertEqual(updated['created_at'], body['created_at'])
        self.assertGreaterEqual(updated['updated_at'], body['updated_at'])
        self.assertEqual(self.client.get(detail_url(body['id'])).json(), updated)

    def test_empty_patch_changes_nothing(self):  # AC-03
        body = self.create()
        response = self.client.patch(detail_url(body['id']), {}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), body)

    def test_invalid_patch_is_rejected_without_changes(self):  # AC-02
        body = self.create()
        response = self.client.patch(detail_url(body['id']), {'name': '', 'email': 'mal'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {'name', 'email'})
        self.assertEqual(self.client.get(detail_url(body['id'])).json()['name'], body['name'])


class ListSuppliersTests(SupplierApiTestCase):
    def setUp(self):
        super().setUp()
        self.sur = self.create(name='Sur', tax_id='NIT-100')
        self.norte = self.create(name='Norte', tax_id='CI-200')
        self.client.post(detail_url(self.norte['id'], 'deactivate/'))

    def ids(self, query=''):
        response = self.client.get(f'{LIST_URL}{query}')
        self.assertEqual(response.status_code, 200, response.content)
        return [s['id'] for s in response.json()['results']]

    def test_search_by_name_or_tax_id_case_insensitive(self):  # AC-04
        self.assertEqual(self.ids('?search=SUR'), [self.sur['id']])
        self.assertEqual(self.ids('?search=ci-2'), [self.norte['id']])
        self.assertEqual(self.ids('?search=zzz'), [])

    def test_active_filter(self):  # AC-04
        self.assertEqual(self.ids('?active=true'), [self.sur['id']])
        self.assertEqual(self.ids('?active=false'), [self.norte['id']])
        self.assertEqual(self.ids(), [self.norte['id'], self.sur['id']])
        self.assertEqual(self.ids('?active=true&search=nor'), [])

    def test_invalid_active_value(self):  # AC-04
        response = self.client.get(f'{LIST_URL}?active=maybe')
        self.assertEqual(response.status_code, 400)
        self.assertIn('active', response.json())

    def test_pagination(self):  # AC-04
        for index in range(3):
            self.create(name=f'Extra {index}')
        body = self.client.get(f'{LIST_URL}?page_size=2&page=2').json()
        self.assertEqual((body['count'], len(body['results'])), (5, 2))
        self.assertEqual(self.client.get(f'{LIST_URL}?page_size=500').json()['count'], 5)


class StateTests(SupplierApiTestCase):
    def test_deactivate_and_activate_are_idempotent_and_keep_the_record(self):  # AC-05
        body = self.create()
        for _ in range(2):
            response = self.client.post(detail_url(body['id'], 'deactivate/'))
            self.assertEqual((response.status_code, response.json()['active']), (200, False))
        self.assertFalse(self.client.get(detail_url(body['id'])).json()['active'])
        self.assertEqual(self.client.get(f'{LIST_URL}?active=true').json()['count'], 0)
        for _ in range(2):
            response = self.client.post(detail_url(body['id'], 'activate/'))
            self.assertEqual((response.status_code, response.json()['active']), (200, True))

    def test_no_delete_or_put(self):  # AC-05, AC-07
        body = self.create()
        self.assertEqual(self.client.delete(detail_url(body['id'])).status_code, 405)
        self.assertEqual(self.client.put(detail_url(body['id']), {'name': 'X'}, format='json').status_code, 405)
        self.assertEqual(SupplierModel.objects.count(), 1)


class DetailAndAccessTests(SupplierApiTestCase):
    def test_detail_shape(self):  # AC-07
        body = self.create()
        response = self.client.get(detail_url(body['id']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), FIELDS)

    def test_unknown_supplier_is_404(self):  # AC-07
        for response in (
            self.client.get(detail_url(uuid4())),
            self.client.patch(detail_url(uuid4()), {'name': 'X'}, format='json'),
            self.client.post(detail_url(uuid4(), 'activate/')),
            self.client.post(detail_url(uuid4(), 'deactivate/')),
        ):
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json(), {'detail': 'Proveedor no encontrado.'})

    def test_requires_authentication(self):  # AC-07
        self.assertEqual(APIClient().get(LIST_URL).status_code, 401)

    def test_disabled_module_is_rejected(self):  # AC-07
        CompanyModuleModel.objects.filter(company_id=self.company.id, module_key='purchases').delete()
        for method, path in (('get', LIST_URL), ('post', LIST_URL), ('get', detail_url(uuid4())),
                             ('patch', detail_url(uuid4())), ('post', detail_url(uuid4(), 'activate/')),
                             ('post', detail_url(uuid4(), 'deactivate/'))):
            with self.subTest(f'{method} {path}'):
                response = getattr(self.client, method)(path, {}, format='json')
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json()['code'], 'module_disabled')
        self.assertEqual(SupplierModel.objects.count(), 0)


class CompanyIsolationTests(SupplierApiTestCase):
    def setUp(self):
        super().setUp()
        other = make_company('Empresa B')
        enable_purchases(other)
        self.other_client = APIClient()
        authenticate(self.other_client, make_admin(other, username='beto'))
        self.foreign = self.other_client.post(LIST_URL, {'name': 'Ajeno'}, format='json').json()

    def test_other_company_supplier_is_invisible_and_untouchable(self):  # AC-06
        self.create(name='Propio')
        self.assertEqual([s['name'] for s in self.client.get(LIST_URL).json()['results']], ['Propio'])
        self.assertEqual(self.client.get(detail_url(self.foreign['id'])).status_code, 404)
        self.assertEqual(self.client.patch(detail_url(self.foreign['id']), {'name': 'X'}, format='json').status_code, 404)
        self.assertEqual(self.client.post(detail_url(self.foreign['id'], 'deactivate/')).status_code, 404)
        self.assertTrue(SupplierModel.objects.get(pk=self.foreign['id']).active)
        self.assertEqual(SupplierModel.objects.get(pk=self.foreign['id']).name, 'Ajeno')

    def test_company_sent_by_the_client_is_ignored(self):  # AC-06
        response = self.client.post(
            LIST_URL, {'name': 'Mío', 'company_id': str(self.foreign['id'])}, format='json',
            HTTP_X_COMPANY_ID=str(uuid4()))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(SupplierModel.objects.get(pk=response.json()['id']).company_id, self.company.id)
