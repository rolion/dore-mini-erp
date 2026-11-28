"""El tipo de empresa elegido al registrarse define los módulos iniciales, sin limitar los posteriores."""
from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APITestCase

from modules.accounts.models import Company
from modules.accounts.testing import make_admin
from modules.modularity.domain.company_types import TEMPLATES
from modules.modularity.domain.modules import BASE_KEYS
from modules.modularity.infrastructure.django.models import CompanyModuleModel
from shared import company_defaults

SNAPSHOT = company_defaults.load_snapshot()


def enabled_keys(company) -> set[str]:
    return set(CompanyModuleModel.objects.filter(company_id=company.id).values_list('module_key', flat=True))


class RegisterByTypeTests(APITestCase):
    payload = {
        'company_name': 'Nueva SRL', 'username': 'nuevo', 'first_name': 'Ana', 'last_name': 'Paz',
        'email': 'ana@example.com', 'password': 'Cl4ve-segura-2026',
    }

    def setUp(self):
        cache.clear()

    def register(self, company_type, **extra):
        response = self.client.post('/api/auth/register/', {**self.payload, 'company_type': company_type, **extra},
                                    format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return response, Company.objects.get(name=extra.get('company_name', self.payload['company_name']))

    def test_each_type_enables_exactly_its_template(self):  # AC-02
        for index, (company_type, modules) in enumerate(TEMPLATES.items()):
            _, company = self.register(company_type, company_name=f'Empresa {index}', username=f'u{index}',
                                       email=f'u{index}@example.com')
            self.assertEqual(company.company_type, company_type)
            self.assertEqual(enabled_keys(company), set(modules), company_type)

    def test_modules_endpoint_reflects_the_template(self):  # AC-02
        response, _ = self.register('servicios')
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {response.json()['token']}")
        listed = {m['key'] for m in self.client.get('/api/modules/').json() if m['enabled']}
        self.assertEqual(listed, set(TEMPLATES['servicios']) | BASE_KEYS)
        self.assertEqual(response.json()['user']['company']['type'], 'servicios')  # AC-04

    def test_rest_of_default_configuration_is_applied_for_every_type(self):  # AC-03
        from modules.accounting.infrastructure.django.models import AccountModel
        for index, company_type in enumerate(TEMPLATES):
            _, company = self.register(company_type, company_name=f'Config {index}', username=f'c{index}',
                                       email=f'c{index}@example.com')
            self.assertEqual(AccountModel.objects.filter(company_id=company.id).count(),
                             len(SNAPSHOT['accounting']['accounts']), company_type)

    def test_admin_can_enable_and_disable_modules_after_registration(self):  # AC-05
        response, company = self.register('servicios')
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {response.json()['token']}")
        self.assertEqual(self.client.post('/api/modules/inventory/enable/').status_code, 200)
        self.assertIn('inventory', enabled_keys(company))
        self.assertEqual(self.client.post('/api/modules/reporting/disable/').status_code, 200)
        self.assertNotIn('reporting', enabled_keys(company))
        self.assertEqual(Company.objects.get(pk=company.pk).company_type, 'servicios')  # INV-01


class ExistingCompaniesTests(APITestCase):
    def test_company_without_explicit_type_is_general(self):  # AC-06
        self.assertEqual(Company.objects.create(name='Antigua SRL').company_type, 'general')

    def test_login_of_a_general_company_returns_its_type(self):  # AC-04, AC-06
        make_admin(username='vieja')
        login = self.client.post('/api/auth/login/', {'username': 'vieja', 'password': 'x-Pass-123'}, format='json')
        self.assertEqual(login.json()['user']['company']['type'], 'general')

    def test_copy_command_keeps_copying_the_snapshot_modules(self):  # AC-07
        company = Company.objects.create(name='Vacía SRL')
        call_command('copy_company_defaults', '--company', 'Vacía SRL')
        self.assertEqual(enabled_keys(company), set(SNAPSHOT['modularity']['modules']))

    def test_apply_all_without_profile_uses_the_snapshot(self):  # AC-07
        company = Company.objects.create(name='Sin perfil SRL')
        company_defaults.apply_all(company.id)
        self.assertEqual(enabled_keys(company), set(SNAPSHOT['modularity']['modules']))
