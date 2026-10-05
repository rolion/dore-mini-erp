import importlib
import os
import sys
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings
from django.urls import path
from rest_framework.response import Response
from rest_framework.test import APITestCase
from rest_framework.views import APIView


class ProtectedView(APIView):
    def get(self, request):
        return Response({'secret': True})


urlpatterns = [path('api/protected/', ProtectedView.as_view())]


class HealthTests(APITestCase):
    def test_health_is_public(self):
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})


@override_settings(ROOT_URLCONF='config.tests')
class DefaultPermissionTests(APITestCase):
    def test_api_denies_anonymous_by_default(self):
        response = self.client.get('/api/protected/')
        self.assertIn(response.status_code, (401, 403))


class ProductionSettingsTests(SimpleTestCase):
    def test_production_requires_secret_key_and_database(self):
        sys.modules.pop('config.settings.production', None)
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ImproperlyConfigured):
                importlib.import_module('config.settings.production')
