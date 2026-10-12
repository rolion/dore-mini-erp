"""AC-12: las migraciones de aislamiento asignan los datos existentes a la empresa por defecto y son reversibles."""
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

DEFAULT_COMPANY_ID = '00000000-0000-4000-8000-000000000001'

BEFORE = [
    ('accounts', '0001_initial'),
    ('catalog', '0001_initial'),
    ('customers', '0001_initial'),
    ('expenses', '0001_initial'),
    ('sales', '0001_initial'),
]
AFTER = [
    ('accounts', '0002_company_and_role'),
    ('catalog', '0002_company_id'),
    ('customers', '0002_company_id'),
    ('expenses', '0002_company_id'),
    ('sales', '0002_company_id'),
]


def _columns(table: str) -> set[str]:
    with connection.cursor() as cursor:
        return {c.name for c in connection.introspection.get_table_description(cursor, table)}


class IsolationMigrationTests(TransactionTestCase):
    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.migrate(targets)
        return MigrationExecutor(connection).loader.project_state(targets).apps

    def tearDown(self):
        # Deja la base de pruebas en el último estado para el resto de la suite.
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_existing_data_moves_to_the_default_company_and_is_reversible(self):
        old = self.migrate(BEFORE)
        User = old.get_model('accounts', 'User')
        user = User.objects.create(username='previo', password='x')
        old.get_model('catalog', 'ProductModel').objects.create(name='Pack', sale_price='10.00')
        old.get_model('customers', 'CustomerModel').objects.create(name='Ana')
        category = old.get_model('expenses', 'ExpenseCategoryModel').objects.create(name='Empaque')
        old.get_model('expenses', 'ExpenseModel').objects.create(
            category=category, description='Harina', amount='5.00', expense_date='2026-10-01',
            payment_method='CASH', status='ACTIVE')
        old.get_model('sales', 'OrderModel').objects.create(
            status='NEW', sales_channel='STORE', order_date='2026-10-01', payment_status='UNPAID')

        new = self.migrate(AFTER)

        company = new.get_model('accounts', 'Company').objects.get(pk=DEFAULT_COMPANY_ID)
        self.assertEqual(company.name, 'Empresa por defecto')
        self.assertEqual(new.get_model('accounts', 'User').objects.get(pk=user.pk).company_id, company.id)
        self.assertEqual(new.get_model('accounts', 'User').objects.get(pk=user.pk).role, 'admin')
        for app, model in (('catalog', 'ProductModel'), ('customers', 'CustomerModel'),
                           ('expenses', 'ExpenseCategoryModel'), ('expenses', 'ExpenseModel'),
                           ('sales', 'OrderModel')):
            rows = list(new.get_model(app, model).objects.values_list('company_id', flat=True))
            self.assertEqual([str(r) for r in rows], [DEFAULT_COMPANY_ID], f'{app}.{model}')

        # Reversa: las columnas desaparecen y los datos de negocio se conservan.
        self.migrate(BEFORE)
        self.assertNotIn('company_id', _columns('catalog_product'))
        self.assertNotIn('company_id', _columns('sales_order'))
        self.assertEqual(old.get_model('catalog', 'ProductModel').objects.count(), 1)
        self.assertEqual(old.get_model('sales', 'OrderModel').objects.count(), 1)

    def test_empty_database_gets_the_default_company_and_nothing_else(self):  # EDGE-05
        new = self.migrate(AFTER)
        self.assertEqual(
            list(new.get_model('accounts', 'Company').objects.values_list('name', flat=True)),
            ['Empresa por defecto'])
        self.assertEqual(new.get_model('catalog', 'ProductModel').objects.count(), 0)
