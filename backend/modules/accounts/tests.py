from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle


class UserModelTests(TestCase):
    def test_auth_user_model_is_accounts_user(self):
        self.assertEqual(get_user_model()._meta.label, 'accounts.User')

    def test_create_user(self):
        user = get_user_model().objects.create_user(username='ana', password='x-Pass-123')
        self.assertTrue(user.check_password('x-Pass-123'))


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
            {'id': self.user.id, 'username': 'ana', 'first_name': 'Ana', 'last_name': 'Pérez'},
        )

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
