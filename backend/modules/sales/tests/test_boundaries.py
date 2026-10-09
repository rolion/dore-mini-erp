"""Límites de arquitectura (docs/architecture/ddd.md): se comprueban leyendo los imports del código fuente."""
import ast
from pathlib import Path

from django.test import SimpleTestCase

BACKEND = Path(__file__).resolve().parents[3]
MODULES = BACKEND / 'modules'
NON_BUSINESS = {'accounts'}


def source_files(base: Path):
    for path in sorted(base.rglob('*.py')):
        parts = path.relative_to(base).parts
        if 'tests' in parts or 'migrations' in parts or path.name in ('tests.py',):
            continue
        yield path


def imports(path: Path):
    """(módulo importado, nombres importados) de cada import del archivo."""
    tree = ast.parse(path.read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, ()
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module, tuple(alias.name for alias in node.names)


class ModuleBoundaryTests(SimpleTestCase):
    def test_modules_only_reach_each_other_through_services(self):  # AC-21
        offenders = []
        for module_dir in sorted(p for p in MODULES.iterdir() if p.is_dir() and not p.name.startswith('__')):
            owner = module_dir.name
            for path in source_files(module_dir):
                for module, names in imports(path):
                    parts = module.split('.')
                    if parts[0] != 'modules' or len(parts) < 2 or parts[1] in (owner, ''):
                        continue
                    other = parts[1]
                    if other in NON_BUSINESS:
                        offenders.append(f'{path.relative_to(BACKEND)} importa {module}')
                        continue
                    is_facade = module == f'modules.{other}.services' or (
                        module == f'modules.{other}' and names == ('services',))
                    if not is_facade:
                        offenders.append(f'{path.relative_to(BACKEND)} importa {module}')
        self.assertEqual(offenders, [])

    def test_only_sales_consumes_the_facades_and_nobody_imports_sales(self):  # AC-21
        offenders = []
        for module_dir in sorted(p for p in MODULES.iterdir() if p.is_dir() and not p.name.startswith('__')):
            if module_dir.name == 'sales':
                continue
            for path in source_files(module_dir):
                for module, _ in imports(path):
                    if module.startswith('modules.sales'):
                        offenders.append(f'{path.relative_to(BACKEND)} importa {module}')
        self.assertEqual(offenders, [])

    def test_sales_reaches_other_modules_only_from_its_adapters(self):  # AC-21
        offenders = []
        for path in source_files(MODULES / 'sales'):
            for module, _ in imports(path):
                parts = module.split('.')
                if parts[0] == 'modules' and len(parts) > 1 and parts[1] in ('catalog', 'customers'):
                    if path.name != 'adapters.py':
                        offenders.append(f'{path.relative_to(BACKEND)} importa {module}')
        self.assertEqual(offenders, [])

    def test_domain_layers_do_not_import_django_or_drf(self):  # ddd.md
        offenders = []
        domain_dirs = [p for p in MODULES.glob('*/domain')] + [BACKEND / 'shared' / 'domain']
        for domain in domain_dirs:
            for path in source_files(domain):
                for module, _ in imports(path):
                    if module.split('.')[0] in ('django', 'rest_framework'):
                        offenders.append(f'{path.relative_to(BACKEND)} importa {module}')
        self.assertEqual(offenders, [])

    def test_sales_application_does_not_import_django_or_infrastructure(self):  # ADR persistencia
        offenders = []
        for path in source_files(MODULES / 'sales' / 'application'):
            for module, _ in imports(path):
                if module.split('.')[0] in ('django', 'rest_framework') or '.infrastructure' in module:
                    offenders.append(f'{path.relative_to(BACKEND)} importa {module}')
        self.assertEqual(offenders, [])
