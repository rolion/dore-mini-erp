from django.contrib.auth import get_user_model
from django.test import TestCase


class UserModelTests(TestCase):
    def test_auth_user_model_is_accounts_user(self):
        self.assertEqual(get_user_model()._meta.label, 'accounts.User')

    def test_create_user(self):
        user = get_user_model().objects.create_user(username='ana', password='x-Pass-123')
        self.assertTrue(user.check_password('x-Pass-123'))
