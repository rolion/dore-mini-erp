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
    requires_capabilities: tuple[str, ...] = ()
    records_adoption: bool = False


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
    ModuleDefinition('production', 'Producción', 'Recetas, elaboraciones y envasados.',
                     requires=('catalog', 'inventory'), optional=('purchases',)),
    ModuleDefinition('costing', 'Costeo', 'Costos por lote y análisis.', requires=('production',),
                     requires_capabilities=('inventory.valuation',), records_adoption=True),
)

# Capacidades que un módulo ofrece a otros sin ser un módulo habilitable (clave -> etiqueta).
CAPABILITIES: dict[str, str] = {'inventory.valuation': 'Valoración de Inventario'}

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
        self.kind = kind  # 'missing' | 'capabilities' | 'dependents'


class DisableBlocked(DependencyError):
    """No se puede deshabilitar: lo requieren otros módulos (`names`) y/o hay datos abiertos (`blockers`)."""

    def __init__(self, names: list[str], blockers: list):
        super().__init__(names, kind='dependents')
        self.blockers = blockers


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


def missing_capabilities(module: ModuleDefinition, available: set[str]) -> list[str]:
    return [CAPABILITIES[key] for key in module.requires_capabilities if key not in available]


def dependents(key: str, enabled: set[str]) -> list[str]:
    return [m.name for m in MODULE_CATALOG if key in m.requires and m.key in enabled]


def check_can_enable(key: str, enabled: set[str], available_capabilities: set[str] = frozenset()) -> None:
    module = definition(key)
    missing = missing_requires(module, enabled)
    if missing:
        raise DependencyError(missing, kind='missing')
    absent = missing_capabilities(module, available_capabilities)
    if absent:
        raise DependencyError(absent, kind='capabilities')


def check_can_disable(key: str, enabled: set[str], blockers: list | None = None) -> None:
    module = definition(key)
    if module.is_base:
        raise BaseModuleError(key)
    blocking = dependents(key, enabled)
    if blocking or blockers:
        raise DisableBlocked(blocking, list(blockers or []))
