"""Borra los datos operativos de PRUEBA de la base conectada (arranca Django solo para usar su conexión; sin modelos).

Ejecución: `python - < scripts/ops/purge_operational_data.py` desde `backend/` (en producción, vía `docker compose exec -T`).

Qué borra (solo las tablas que existan en esa base):
  - Contabilidad: entradas y cuentas de dinero.
  - Ventas, cobros de servicios (receivables), inventario, costeo, compras, gastos (registros), proformas de
    servicios y dentales, agenda, clientes, pacientes, catálogo de productos y servicios.
Qué conserva:
  - Usuarios, empresas, migraciones y ajustes de módulos.
  - Configuración contable: clasificaciones, mapeos de método de pago (quedan sin cuenta y desactivados), cortes y
    períodos de cobertura.
  - Categorías de gastos y unidades de medida.

Seguridad:
  - Por defecto es un ENSAYO: ejecuta todo dentro de una transacción y la revierte.
  - Para aplicar hacen falta APPLY=1 y CONFIRM_DB=<nombre exacto de la base>.
  - Usa TRUNCATE sin CASCADE: si alguna tabla fuera de la lista depende de las vaciadas, falla y no borra nada.
  - Todo ocurre en UNA transacción: o se borra todo o nada.
  - Haz un respaldo ANTES (ver docs/deployment/limpiar-datos-de-prueba.md). Este script no hace respaldo.
"""
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from django.db import connection, transaction  # noqa: E402  (requiere django.setup() previo)

APPLY = os.environ.get('APPLY') == '1'
CONFIRM_DB = os.environ.get('CONFIRM_DB', '')

# Prefijos de módulos operativos que se vacían completos.
PREFIXES = ('sales_', 'receivables_', 'inventory_', 'costing_', 'purchases_', 'quotations_', 'dentistry_', 'agenda_',
            'service_catalog_', 'customers_')
# Tablas sueltas que se vacían (gastos registrados, productos y entradas del libro).
EXTRA = ('expenses_expense', 'catalog_product', 'accounting_entry')
# Del catálogo se conservan las unidades de medida; el resto (productos y lo que dependa de ellos) se vacía.
KEEP_IN_CATALOG = ('catalog_unit',)

db_name = connection.settings_dict['NAME']
cursor = connection.cursor()


def count(table):
    cursor.execute(f'SELECT count(*) FROM "{table}"')
    return cursor.fetchone()[0]


def exists(table):
    cursor.execute("SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=%s", [table])
    return cursor.fetchone() is not None


cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' "
               "AND table_type='BASE TABLE' ORDER BY 1")
names = [name for (name,) in cursor.fetchall()]
tables = [t for t in names if t.startswith(PREFIXES)]
tables += [t for t in EXTRA if t in names and t not in tables]
tables += [t for t in names if t.startswith('catalog_') and t not in tables and t not in KEEP_IN_CATALOG]

print(f'Base: {db_name}  ·  modo: {"APLICAR" if APPLY else "ENSAYO (se revierte)"}')
if APPLY and CONFIRM_DB != db_name:
    raise SystemExit(f'Cancelado: CONFIRM_DB debe ser exactamente "{db_name}" (recibido "{CONFIRM_DB}").')

before = {t: count(t) for t in tables + ['accounting_account'] if exists(t)}
print('\nFilas que se borrarán (solo tablas con datos):')
for table, n in before.items():
    if n:
        print(f'  {table}: {n}')
print(f'  (tablas revisadas: {len(before)}; vacías: {sum(1 for n in before.values() if not n)})')
print('\nSe conservan: ' + ', '.join(f'{t}={count(t)}' for t in (
    'accounts_company', 'accounts_user', 'accounting_classification', 'accounting_settings',
    'accounting_coverage_period', 'accounting_method_mapping', 'expenses_category', 'catalog_unit') if exists(t)))

try:
    with transaction.atomic():
        # Los mapeos referencian cuentas: se desvinculan y se desactivan para poder borrar las cuentas.
        if exists('accounting_method_mapping'):
            cursor.execute('UPDATE accounting_method_mapping SET account_id = NULL, is_active = false')
            print(f'\nMapeos de método de pago desvinculados: {cursor.rowcount}')
        if tables:
            cursor.execute('TRUNCATE ' + ', '.join(f'"{t}"' for t in tables))  # sin CASCADE a propósito
        if exists('accounting_account'):
            cursor.execute('DELETE FROM accounting_account')
            print(f'Cuentas de dinero borradas: {cursor.rowcount}')
        remaining = {t: count(t) for t in before if count(t)}
        if remaining:
            raise RuntimeError(f'Quedaron filas, se revierte todo: {remaining}')
        if not APPLY:
            raise RuntimeError('ENSAYO terminado sin errores: se revierte (no se borró nada). '
                               'Para aplicar: APPLY=1 CONFIRM_DB=' + db_name)
    print('\nOK: datos operativos borrados y transacción confirmada.')
except RuntimeError as exc:
    print(f'\n{exc}')
