"""Límites de arquitectura (docs/architecture/ddd.md): se comprueban leyendo los imports del código fuente."""
import ast
from pathlib import Path

from django.test import SimpleTestCase

BACKEND = Path(__file__).resolve().parents[3]
MODULES = BACKEND / 'modules'
NON_BUSINESS = {'accounts'}

# Dependencias permitidas entre módulos de negocio, siempre y solo a través de `modules.<otro>.services`.
ALLOWED_DEPENDENCIES: dict[str, set[str]] = {
    'catalog': set(),
    'customers': set(),
    'expenses': set(),
    'sales': {'catalog', 'customers'},
    'reporting': {'sales', 'expenses', 'customers'},
}
# Módulos que consumen a otros: solo desde sus adaptadores de infraestructura.
CONSUMERS = ('sales', 'reporting')


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


def business_modules():
    return sorted(p for p in MODULES.iterdir() if p.is_dir() and not p.name.startswith('__'))


def is_facade(other: str, module: str, names: tuple[str, ...]) -> bool:
    return module == f'modules.{other}.services' or (module == f'modules.{other}' and names == ('services',))


class ModuleBoundaryTests(SimpleTestCase):
    def test_every_business_module_has_a_declared_dependency_entry(self):  # AC-19
        declared = set(ALLOWED_DEPENDENCIES)
        existing = {p.name for p in business_modules()} - NON_BUSINESS
        self.assertEqual(existing, declared)

    def test_modules_only_reach_allowed_modules_and_only_through_services(self):  # AC-19
        offenders = []
        for module_dir in business_modules():
            owner = module_dir.name
            if owner in NON_BUSINESS:
                continue
            for path in source_files(module_dir):
                for module, names in imports(path):
                    parts = module.split('.')
                    if parts[0] != 'modules' or len(parts) < 2 or parts[1] in (owner, ''):
                        continue
                    other = parts[1]
                    if other in NON_BUSINESS or other not in ALLOWED_DEPENDENCIES.get(owner, set()):
                        offenders.append(f'{path.relative_to(BACKEND)} importa {module}')
                    elif not is_facade(other, module, names):
                        offenders.append(f'{path.relative_to(BACKEND)} importa {module}')
        self.assertEqual(offenders, [])

    def test_nobody_imports_reporting(self):  # AC-19: Reporting solo lee, nadie depende de él
        offenders = []
        for module_dir in business_modules():
            if module_dir.name == 'reporting':
                continue
            for path in source_files(module_dir):
                for module, _ in imports(path):
                    if module.startswith('modules.reporting'):
                        offenders.append(f'{path.relative_to(BACKEND)} importa {module}')
        self.assertEqual(offenders, [])

    def test_consumers_reach_other_modules_only_from_their_adapters(self):  # AC-19
        offenders = []
        for owner in CONSUMERS:
            for path in source_files(MODULES / owner):
                for module, _ in imports(path):
                    parts = module.split('.')
                    if parts[0] == 'modules' and len(parts) > 1 and parts[1] != owner and parts[1] in ALLOWED_DEPENDENCIES:
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

    def test_application_layers_do_not_import_django_or_infrastructure(self):  # ADR persistencia
        offenders = []
        for owner in ('sales', 'expenses', 'reporting'):
            for path in source_files(MODULES / owner / 'application'):
                for module, _ in imports(path):
                    if module.split('.')[0] in ('django', 'rest_framework') or '.infrastructure' in module:
                        offenders.append(f'{path.relative_to(BACKEND)} importa {module}')
        self.assertEqual(offenders, [])
