"""PB-MOD-002: puerto `shared.module_gate` y reglas del permiso por módulo (INV-02, EDGE-05)."""
from unittest import mock
from uuid import uuid4

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from config.permissions import CompanyModulePermission, ModuleDisabled
from shared import module_gate


class ModuleGateTests(SimpleTestCase):
    def test_without_a_provider_it_never_grants_access(self):  # EDGE-05
        with mock.patch.object(module_gate, '_provider', None):
            with self.assertRaises(module_gate.GateNotConfigured):
                module_gate.is_enabled(uuid4(), 'sales')

    def test_delegates_to_the_registered_provider(self):
        with mock.patch.object(module_gate, '_provider', lambda company_id: {'catalog', 'sales'}):
            self.assertTrue(module_gate.is_enabled(uuid4(), 'sales'))
            self.assertFalse(module_gate.is_enabled(uuid4(), 'customers'))


class _View:
    pass


class CompanyModulePermissionTests(SimpleTestCase):
    def check(self, required):
        view = _View()
        if required is not None:
            view.required_modules = required
        request = APIRequestFactory().get('/')
        request.user = mock.Mock(is_authenticated=True, company_id=uuid4(), role='admin')
        request.user.company.is_active = True
        with mock.patch.object(module_gate, '_provider', lambda company_id: {'catalog', 'sales'}):
            return CompanyModulePermission().has_permission(request, view)

    def test_view_without_required_modules_is_denied(self):  # INV-02
        self.assertFalse(self.check(None))

    def test_empty_tuple_needs_no_module(self):
        self.assertTrue(self.check(()))

    def test_enabled_module_is_allowed(self):
        self.assertTrue(self.check(('sales',)))

    def test_first_missing_module_is_reported(self):  # EDGE-02
        with self.assertRaises(ModuleDisabled) as raised:
            self.check(('sales', 'customers', 'expenses'))
        self.assertEqual(raised.exception.detail['module'], 'customers')
