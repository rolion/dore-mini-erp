from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle

from modules.accounts import registration
from modules.accounts.models import Company
from modules.accounts.testing import authenticate, make_admin, make_company


class UserModelTests(TestCase):
    def test_auth_user_model_is_accounts_user(self):
        self.assertEqual(get_user_model()._meta.label, 'accounts.User')

    def test_create_user(self):
        user = get_user_model().objects.create_user(username='ana', password='x-Pass-123')
        self.assertTrue(user.check_password('x-Pass-123'))

    def test_user_defaults_to_admin_role_and_no_company(self):
        user = get_user_model().objects.create_user(username='op', password='x-Pass-123')
        self.assertEqual(user.role, 'admin')
        self.assertIsNone(user.company)


class CompanyModelTests(TestCase):
    def test_company_name_is_normalized_and_unique_ignoring_case(self):  # INV-03
        Company.objects.create(name='  Cuñapés   SRL ')
        self.assertEqual(Company.objects.get(name__iexact='cuñapés srl').name, 'Cuñapés SRL')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Company.objects.create(name='CUÑAPÉS SRL')


class AuthApiTests(APITestCase):
    login_url = '/api/auth/login/'
    logout_url = '/api/auth/logout/'

    def setUp(self):
        cache.clear()  # el throttle de login usa cache; aislar entre tests
        self.user = get_user_model().objects.create_user(
            username='ana', password='x-Pass-123', first_name='Ana', last_name='Pérez',
        )

    def login(self, username='ana', password='x-Pass-123', **extra):
        return self.client.post(self.login_url, {'username': username, 'password': password}, format='json', **extra)

    def test_login_ok_returns_token_and_user(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['token'], Token.objects.get(user=self.user).key)
        self.assertEqual(
            body['user'],
            {'id': self.user.id, 'username': 'ana', 'first_name': 'Ana', 'last_name': 'Pérez',
             'role': 'admin', 'company': None},
        )

    def test_login_returns_role_and_company_of_the_user(self):  # AC-10
        company = Company.objects.create(name='Cuñapés SRL')
        self.user.company = company
        self.user.save()
        user = self.login().json()['user']
        self.assertEqual(user['role'], 'admin')
        self.assertEqual(user['company'], {'id': str(company.id), 'name': 'Cuñapés SRL'})

    def test_login_of_inactive_company_is_indistinguishable_from_invalid_credentials(self):  # AC-10
        self.user.company = Company.objects.create(name='Cerrada SRL', is_active=False)
        self.user.save()
        response = self.login()
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {'detail': 'Credenciales inválidas.'})
        self.assertFalse(Token.objects.exists())

    def test_login_response_never_exposes_password(self):
        content = self.login().content.decode()
        self.assertNotIn('password', content)
        self.assertNotIn(self.user.password, content)

    def test_login_invalid_credentials_are_indistinguishable(self):
        get_user_model().objects.create_user(username='off', password='x-Pass-123', is_active=False)
        responses = [
            self.login(password='mala'),
            self.login(username='nadie'),
            self.login(username='off'),
        ]
        for response in responses:
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json(), {'detail': 'Credenciales inválidas.'})
        self.assertFalse(Token.objects.exists())

    def test_login_missing_fields_returns_400(self):
        response = self.client.post(self.login_url, {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {'username', 'password'})

    def test_login_ignores_invalid_authorization_header(self):
        response = self.login(HTTP_AUTHORIZATION='Token vencido')
        self.assertEqual(response.status_code, 200)

    def test_login_reuses_existing_token(self):
        first = self.login().json()['token']
        second = self.login().json()['token']
        self.assertEqual(first, second)
        self.assertEqual(Token.objects.count(), 1)

    def test_logout_deletes_token_and_it_stops_authenticating(self):
        token = self.login().json()['token']
        header = {'HTTP_AUTHORIZATION': f'Token {token}'}
        self.assertEqual(self.client.post(self.logout_url, **header).status_code, 204)
        self.assertFalse(Token.objects.filter(key=token).exists())
        self.assertEqual(self.client.post(self.logout_url, **header).status_code, 401)

    def test_logout_without_authentication_returns_401(self):
        self.assertEqual(self.client.post(self.logout_url).status_code, 401)

    def test_login_is_throttled(self):
        with mock.patch.object(ScopedRateThrottle, 'THROTTLE_RATES', {'login': '3/min'}):
            statuses = [self.login(password='mala').status_code for _ in range(4)]
        self.assertEqual(statuses, [401, 401, 401, 429])


class RegisterApiTests(APITestCase):
    url = '/api/auth/register/'
    payload = {
        'company_name': 'Cuñapés SRL', 'username': 'maria', 'first_name': 'María', 'last_name': 'Quispe',
        'email': 'maria@example.com', 'password': 'Cl4ve-segura-2026',
    }

    def setUp(self):
        cache.clear()  # el throttle de registro usa cache; aislar entre tests

    def register(self, **overrides):
        return self.client.post(self.url, {**self.payload, **overrides}, format='json')

    def test_register_creates_company_and_admin_and_returns_session(self):  # AC-01
        response = self.register()
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        user = get_user_model().objects.get(username='maria')
        self.assertEqual(user.company.name, 'Cuñapés SRL')
        self.assertEqual(user.role, 'admin')
        self.assertTrue(user.check_password('Cl4ve-segura-2026'))
        self.assertEqual(body['token'], Token.objects.get(user=user).key)
        self.assertEqual(body['user'], {
            'id': user.id, 'username': 'maria', 'first_name': 'María', 'last_name': 'Quispe',
            'role': 'admin', 'company': {'id': str(user.company.id), 'name': 'Cuñapés SRL'},
        })

    def test_registered_token_authenticates_business_api(self):  # AC-01
        token = self.register().json()['token']
        response = self.client.get('/api/products/', HTTP_AUTHORIZATION=f'Token {token}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['results'], [])

    def test_register_never_exposes_password(self):  # AC-03
        content = self.register().content.decode()
        self.assertNotIn('password', content)
        self.assertNotIn(get_user_model().objects.get(username='maria').password, content)

    def test_register_collapses_spaces_in_company_name(self):  # EDGE-06
        self.register(company_name='  Cuñapés    SRL ')
        self.assertEqual(get_user_model().objects.get(username='maria').company.name, 'Cuñapés SRL')

    def test_existing_company_name_is_rejected_ignoring_case_and_spaces(self):  # AC-02
        make_company('Cuñapés SRL')
        before = (Company.objects.count(), get_user_model().objects.count())
        response = self.register(company_name='  cuñapés   srl ')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {'company_name'})
        self.assertEqual((Company.objects.count(), get_user_model().objects.count()), before)
        self.assertFalse(Token.objects.exists())

    def test_existing_username_is_rejected_without_creating_company(self):  # AC-03
        make_admin(make_company('Otra SRL'), username='maria')
        before = Company.objects.count()
        response = self.register()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {'username'})
        self.assertEqual(Company.objects.count(), before)

    def test_weak_password_is_rejected(self):  # AC-03
        response = self.register(password='12345678')
        self.assertEqual(response.status_code, 400)
        self.assertIn('password', response.json())
        self.assertFalse(get_user_model().objects.filter(username='maria').exists())

    def test_missing_fields_return_400_per_field(self):  # AC-03
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()),
                         {'company_name', 'username', 'first_name', 'last_name', 'email', 'password'})

    def test_blank_or_too_long_company_name_is_rejected(self):  # EDGE-06
        for name in ('   ', 'x' * 151):
            response = self.register(company_name=name)
            self.assertEqual(response.status_code, 400, name)
            self.assertEqual(set(response.json()), {'company_name'})

    def test_invalid_email_is_rejected(self):  # AC-03
        self.assertEqual(set(self.register(email='no-es-correo').json()), {'email'})

    def test_register_ignores_invalid_authorization_header(self):
        response = self.client.post(self.url, self.payload, format='json', HTTP_AUTHORIZATION='Token vencido')
        self.assertEqual(response.status_code, 201)

    def test_race_on_company_name_ends_in_400_not_500(self):  # EDGE-01
        # El chequeo previo "no ve" la empresa que otra petición acaba de crear: gana la restricción de la BD.
        make_company('Cuñapés SRL')
        with mock.patch.object(registration, '_conflicts', side_effect=[{}, {}]):
            response = self.register(company_name='cuñapés srl')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {'company_name'})
        self.assertFalse(get_user_model().objects.filter(username='maria').exists())

    def test_register_is_throttled(self):  # AC-11
        with mock.patch.object(ScopedRateThrottle, 'THROTTLE_RATES', {'register': '2/hour'}):
            statuses = [self.register(company_name=f'E{i}', username=f'u{i}').status_code for i in range(3)]
        self.assertEqual(statuses, [201, 201, 429])

    @override_settings(REGISTRATION_ENABLED=False)
    def test_register_can_be_disabled(self):  # AC-11
        before = Company.objects.count()
        response = self.register()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Company.objects.count(), before)
        self.assertFalse(get_user_model().objects.exists())


class BusinessApiPermissionTests(APITestCase):
    """AC-09: la API de negocio exige empresa activa y rol admin; lo público sigue público."""

    url = '/api/products/'

    def call_as(self, user):
        authenticate(self.client, user)
        return self.client.get(self.url)

    def test_admin_of_active_company_has_access(self):
        self.assertEqual(self.call_as(make_admin()).status_code, 200)

    def test_user_without_company_is_forbidden(self):  # EDGE-02
        user = get_user_model().objects.create_user(username='op', password='x-Pass-123')
        response = self.call_as(user)
        self.assertEqual(response.status_code, 403)
        self.assertIn('detail', response.json())

    def test_user_of_inactive_company_is_forbidden(self):
        company = make_company('Cerrada SRL', is_active=False)
        self.assertEqual(self.call_as(make_admin(company)).status_code, 403)

    def test_user_with_other_role_is_forbidden(self):
        user = make_admin()
        get_user_model().objects.filter(pk=user.pk).update(role='lector')
        user.refresh_from_db()
        self.assertEqual(self.call_as(user).status_code, 403)

    def test_anonymous_is_unauthorized(self):
        self.assertEqual(self.client.get(self.url).status_code, 401)

    def test_public_endpoints_stay_public(self):
        self.assertEqual(self.client.get('/api/health/').status_code, 200)

    def test_logout_only_requires_authentication(self):
        user = get_user_model().objects.create_user(username='op', password='x-Pass-123')
        authenticate(self.client, user)
        self.assertEqual(self.client.post('/api/auth/logout/').status_code, 204)
