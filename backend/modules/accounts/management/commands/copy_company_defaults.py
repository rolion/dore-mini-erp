"""Copia la configuración contable y de módulos por defecto a una empresa existente.

Solo completa lo que falta (no pisa lo ya configurado) y es idempotente. Con `--dry-run` calcula sin guardar.
"""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from shared import company_defaults

from ._company import find_company

SECTION_LABELS = {
    'accounting': 'Contabilidad (cuentas, mapeos, clasificaciones, período)', 'expenses': 'Gastos (categorías)',
    'accounting_posting': 'Contabilidad (cuentas de asientos automáticos)', 'purchases': 'Compras (ajustes)',
    'inventory': 'Inventario (almacenes)', 'modularity': 'Módulos y ajustes',
}


class Command(BaseCommand):
    help = 'Aplica la configuración por defecto (snapshot) a una empresa, completando solo lo faltante.'

    def add_arguments(self, parser):
        parser.add_argument('--company', required=True, help='Nombre exacto o UUID de la empresa destino.')
        parser.add_argument('--dry-run', action='store_true', help='Muestra qué se crearía sin guardar nada.')
        parser.add_argument('--snapshot', help='Snapshot alternativo (por defecto, el del repositorio).')

    def handle(self, *args, **options):
        company = find_company(options['company'])
        try:
            snapshot = company_defaults.load_snapshot(Path(options['snapshot']) if options['snapshot']
                                                      else company_defaults.SNAPSHOT_PATH)
            report = company_defaults.apply_all(company.id, snapshot, dry_run=options['dry_run'])
        except company_defaults.DefaultsError as exc:
            raise CommandError(str(exc)) from None
        mode = 'Simulación (no se guardó nada)' if options['dry_run'] else 'Aplicado'
        self.stdout.write(f'{mode} sobre «{company.name}»:')
        for key, counts in report.items():
            label = SECTION_LABELS.get(key, key)
            extra = f', {counts["completed"]} reactivados/completados' if counts.get('completed') else ''
            self.stdout.write(f'  {label}: {counts["created"]} creados, {counts["existing"]} ya existían{extra}')
