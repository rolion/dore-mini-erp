"""Guardas del aislamiento por empresa (AC-16): fallan si alguien olvida el filtro al agregar código nuevo."""
from django.apps import apps
from django.test import SimpleTestCase
from django.urls import URLPattern, URLResolver, get_resolver

BUSINESS_APPS = ('catalog', 'customers', 'sales', 'expenses', 'purchases')
# Tablas hijas: heredan la empresa de su pedido por la FK interna de Sales y se consultan siempre a través de él.
CHILD_MODELS = {'sales.OrderItemModel', 'sales.PaymentModel'}
PUBLIC_PREFIXES = ('api/auth/', 'api/health/')


def iter_patterns(patterns, prefix=''):
    for pattern in patterns:
        route = prefix + str(pattern.pattern)
        if isinstance(pattern, URLResolver):
            yield from iter_patterns(pattern.url_patterns, route)
        elif isinstance(pattern, URLPattern):
            yield route, pattern.callback


class CompanyColumnTests(SimpleTestCase):
    def test_every_root_business_table_has_company_id(self):  # AC-16 (a), INV-01
        missing = []
        for label in BUSINESS_APPS:
            for model in apps.get_app_config(label).get_models():
                if model._meta.label in CHILD_MODELS:
                    continue
                try:
                    field = model._meta.get_field('company_id')
                except Exception:
                    missing.append(model._meta.label)
                    continue
                if field.null or not field.db_index:
                    missing.append(f'{model._meta.label} (company_id debe ser obligatorio e indexado)')
        self.assertEqual(missing, [])

    def test_child_tables_are_reached_through_their_order(self):  # AC-16 (a)
        for label in CHILD_MODELS:
            model = apps.get_model(label)
            self.assertEqual([f.name for f in model._meta.get_fields() if f.name == 'company_id'], [], label)
            self.assertTrue(model._meta.get_field('order').remote_field.model._meta.label == 'sales.OrderModel')

    def test_business_models_do_not_reference_accounts_by_foreign_key(self):  # ADR aislamiento: solo UUID
        offenders = []
        for label in BUSINESS_APPS:
            for model in apps.get_app_config(label).get_models():
                for field in model._meta.get_fields():
                    related = getattr(field, 'related_model', None)
                    if related is not None and related._meta.app_label == 'accounts':
                        offenders.append(f'{model._meta.label}.{field.name}')
        self.assertEqual(offenders, [])


class DefaultPermissionTests(SimpleTestCase):
    def test_no_business_view_overrides_the_default_permission(self):  # AC-09, AC-16
        offenders = []
        for route, callback in iter_patterns(get_resolver().url_patterns):
            if not route.startswith('api/') or route.startswith(PUBLIC_PREFIXES):
                continue
            view_class = getattr(callback, 'view_class', None) or getattr(callback, 'cls', None)
            permissions = [p.__name__ for p in getattr(view_class, 'permission_classes', [])]
            if permissions != ['CompanyModulePermission']:
                offenders.append(f'{route}: {permissions}')
        self.assertEqual(offenders, [])

    def test_every_api_view_declares_known_required_modules(self):  # PB-MOD-002 AC-09, INV-02
        from modules.modularity.domain.modules import BY_KEY

        offenders = []
        for route, callback in iter_patterns(get_resolver().url_patterns):
            if not route.startswith('api/') or route.startswith(PUBLIC_PREFIXES):
                continue
            view_class = getattr(callback, 'view_class', None) or getattr(callback, 'cls', None)
            required = getattr(view_class, 'required_modules', None)
            if not isinstance(required, tuple) or any(key not in BY_KEY for key in required):
                offenders.append(f'{route}: {required!r}')
        self.assertEqual(offenders, [])
