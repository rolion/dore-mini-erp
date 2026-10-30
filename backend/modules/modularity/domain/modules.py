"""Catálogo de módulos del producto y reglas de habilitación (puro: sin Django)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleDefinition:
    key: str
    name: str
    description: str
    is_base: bool = False
    requires: tuple[str, ...] = ()
    optional: tuple[str, ...] = ()


MODULE_CATALOG: tuple[ModuleDefinition, ...] = (
    ModuleDefinition('access', 'Acceso y Empresa', 'Registro, inicio de sesión y aislamiento por empresa.', is_base=True),
    ModuleDefinition('catalog', 'Catálogo', 'Productos y precios.', is_base=True),
    ModuleDefinition('customers', 'Clientes', 'Agenda de clientes e historial de compras.'),
    ModuleDefinition('sales', 'Ventas', 'Pedidos, entrega y cobros.', requires=('catalog',), optional=('customers',)),
    ModuleDefinition('expenses', 'Gastos', 'Registro de gastos y categorías.'),
    ModuleDefinition('reporting', 'Reportes', 'Dashboard y reportes de ventas y gastos.',
                     requires=('sales', 'expenses'), optional=('customers',)),
    ModuleDefinition('purchases', 'Compras', 'Compras a proveedores.', requires=('catalog', 'expenses')),
    ModuleDefinition('inventory', 'Inventario', 'Existencias de productos.',
                     requires=('catalog',), optional=('sales', 'purchases')),
    ModuleDefinition('costing', 'Costeo', 'Valoración y costo de las existencias.', requires=('inventory',)),
)

BY_KEY: dict[str, ModuleDefinition] = {module.key: module for module in MODULE_CATALOG}
BASE_KEYS: frozenset[str] = frozenset(m.key for m in MODULE_CATALOG if m.is_base)
# Habilitados por defecto en toda empresa la primera vez que se consulta (además de los base).
DEFAULT_ENABLED_KEYS: tuple[str, ...] = ('customers', 'sales', 'expenses', 'reporting')


class UnknownModule(Exception):
    pass


class BaseModuleError(Exception):
    """Los módulos base no se pueden deshabilitar."""


class DependencyError(Exception):
    """Dependencias faltantes (al habilitar) o dependientes habilitados (al deshabilitar)."""

    def __init__(self, names: list[str], *, kind: str):
        super().__init__(names)
        self.names = names
        self.kind = kind  # 'missing' | 'dependents'


def definition(key: str) -> ModuleDefinition:
    try:
        return BY_KEY[key]
    except KeyError:
        raise UnknownModule(key) from None


def effective_enabled(stored: set[str]) -> set[str]:
    """Claves habilitadas: las guardadas más las base (siempre activas)."""
    return (stored & BY_KEY.keys()) | BASE_KEYS


def missing_requires(module: ModuleDefinition, enabled: set[str]) -> list[str]:
    return [BY_KEY[key].name for key in module.requires if key not in enabled]


def dependents(key: str, enabled: set[str]) -> list[str]:
    return [m.name for m in MODULE_CATALOG if key in m.requires and m.key in enabled]


def check_can_enable(key: str, enabled: set[str]) -> None:
    missing = missing_requires(definition(key), enabled)
    if missing:
        raise DependencyError(missing, kind='missing')


def check_can_disable(key: str, enabled: set[str]) -> None:
    module = definition(key)
    if module.is_base:
        raise BaseModuleError(key)
    blocking = dependents(key, enabled)
    if blocking:
        raise DependencyError(blocking, kind='dependents')
