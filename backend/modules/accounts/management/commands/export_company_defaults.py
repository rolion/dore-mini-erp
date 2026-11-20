"""Genera el snapshot de configuración por defecto (`shared/company_defaults/snapshot.json`) desde una empresa.

Solo lee la empresa de origen; el JSON usa claves naturales (sin UUID, personas ni movimientos).
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from shared import company_defaults

from ._company import find_company


class Command(BaseCommand):
    help = 'Exporta la configuración contable y de módulos de una empresa al snapshot de defaults.'

    def add_arguments(self, parser):
        parser.add_argument('--company', required=True, help='Nombre exacto o UUID de la empresa de origen.')
        parser.add_argument('--output', help='Archivo de salida (por defecto, el snapshot del repositorio).')

    def handle(self, *args, **options):
        company = find_company(options['company'])
        data = company_defaults.export_all(company.id)
        target = Path(options['output']) if options['output'] else company_defaults.SNAPSHOT_PATH
        try:
            target.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')
        except OSError as exc:
            raise CommandError(f'No se pudo escribir {target}: {exc}') from None
        self.stdout.write(self.style.SUCCESS(f'Snapshot de «{company.name}» escrito en {target}.'))
