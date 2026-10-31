"""Isolated deployment checks: no .env, PostgreSQL or app startup required.

Run: .venv/Scripts/python.exe -m unittest config.test_production_deployment -v
"""
import importlib.util
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

import environ
from django.conf import settings
from django.http import HttpResponse
from django.middleware.csrf import CsrfViewMiddleware
from django.middleware.security import SecurityMiddleware
from django.test import RequestFactory, override_settings

if not settings.configured:
    settings.configure()


def production_settings(**overrides):
    """Load the real production module with a synthetic base and environment."""
    package = types.ModuleType('deployment_settings')
    package.__path__ = []
    base = types.ModuleType('deployment_settings.base')
    base.BASE_DIR = Path('/app')
    base.env = environ.Env()
    spec = importlib.util.spec_from_file_location(
        'deployment_settings.production',
        Path(__file__).parent / 'settings' / 'production.py',
    )
    module = importlib.util.module_from_spec(spec)
    variables = {
        'SECRET_KEY': 'synthetic-test-value',
        'ALLOWED_HOSTS': 'www.pocketbiz.website,app.pocketbiz.website',
        'DATABASE_URL': 'postgresql://test:test@db_v2:5432/test',
        **overrides,
    }
    with patch.dict(os.environ, variables, clear=True), patch.dict(
        sys.modules,
        {'deployment_settings': package, 'deployment_settings.base': base},
    ):
        spec.loader.exec_module(module)
    return module


class ProductionDeploymentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not settings.configured:
            settings.configure()
        cls.production = production_settings()

    def deployment_settings(self):
        return override_settings(**{
            name: getattr(self.production, name)
            for name in (
                'SECURE_PROXY_SSL_HEADER', 'SECURE_SSL_REDIRECT',
                'ALLOWED_HOSTS', 'SESSION_COOKIE_SECURE', 'CSRF_COOKIE_SECURE',
            )
        })

    def test_forwarded_https_has_no_redirect_loop(self):
        with self.deployment_settings():
            request = RequestFactory().get(
                '/api/health/', HTTP_HOST='app.pocketbiz.website',
                HTTP_X_FORWARDED_PROTO='https',
            )
            response = SecurityMiddleware(lambda _: HttpResponse('ok'))(request)
            self.assertTrue(request.is_secure())
            self.assertEqual(response.status_code, 200)

    def test_http_redirects_to_original_host_and_path(self):
        with self.deployment_settings():
            request = RequestFactory().get(
                '/admin/login/?next=/admin/', HTTP_HOST='www.pocketbiz.website',
                HTTP_X_FORWARDED_PROTO='http',
            )
            response = SecurityMiddleware(lambda _: HttpResponse('ok'))(request)
            self.assertEqual(response.status_code, 301)
            self.assertEqual(
                response['Location'],
                'https://www.pocketbiz.website/admin/login/?next=/admin/',
            )

    def test_same_origin_admin_csrf_and_cross_origin_rejection(self):
        with self.deployment_settings():
            middleware = CsrfViewMiddleware(lambda _: HttpResponse('ok'))
            request = RequestFactory().post(
                '/admin/login/', HTTP_HOST='app.pocketbiz.website',
                HTTP_X_FORWARDED_PROTO='https',
                HTTP_ORIGIN='https://app.pocketbiz.website',
            )
            self.assertTrue(middleware._origin_verified(request))
            request.META['HTTP_ORIGIN'] = 'https://untrusted.example'
            self.assertFalse(middleware._origin_verified(request))

    def test_static_collection_and_secure_defaults(self):
        self.assertEqual(self.production.STATIC_ROOT, Path('/app/staticfiles'))
        self.assertEqual(self.production.STATIC_URL, '/static/')
        self.assertFalse(self.production.DEBUG)
        self.assertTrue(self.production.SESSION_COOKIE_SECURE)
        self.assertTrue(self.production.CSRF_COOKIE_SECURE)

    def test_required_variables_fail_without_reading_dotenv(self):
        from django.core.exceptions import ImproperlyConfigured
        for name in ('SECRET_KEY', 'DATABASE_URL', 'ALLOWED_HOSTS'):
            with self.subTest(name=name), self.assertRaises(ImproperlyConfigured):
                self.missing(name)

    def missing(self, name):
        # The real environ.Env must reject absent mandatory values.
        with patch.object(environ.Env, 'ENVIRON', {
            'SECRET_KEY': 'synthetic', 'DATABASE_URL': 'postgresql://test:test@db_v2/test',
            'ALLOWED_HOSTS': 'app.pocketbiz.website',
        }):
            del environ.Env.ENVIRON[name]
            production_settings()


if __name__ == '__main__':
    unittest.main()