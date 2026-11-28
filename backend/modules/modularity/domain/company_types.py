"""Plantillas de módulos por tipo de empresa (puro: sin Django).

El tipo se elige al registrarse y solo define los módulos con que nace la empresa; después el admin puede habilitar o
deshabilitar los que quiera. Los módulos base (`access`, `catalog`) están siempre y no se listan aquí.
"""

COMPRAVENTA = 'compraventa'
SERVICIOS = 'servicios'
ODONTOLOGIA = 'odontologia'
GENERAL = 'general'  # empresas anteriores al tipo: conservan todos los módulos del snapshot

_SERVICES = ('services', 'personnel', 'agenda', 'customers', 'quotations', 'receivables',
             'accounting', 'expenses', 'reporting')

TEMPLATES: dict[str, tuple[str, ...]] = {
    COMPRAVENTA: ('customers', 'sales', 'purchases', 'inventory', 'accounting', 'expenses', 'reporting'),
    SERVICIOS: _SERVICES,
    ODONTOLOGIA: (*_SERVICES, 'dentistry'),
}


def template_modules(company_type: str) -> tuple[str, ...] | None:
    """Módulos no base de la plantilla del tipo; `None` si el tipo no tiene plantilla (usa el snapshot)."""
    return TEMPLATES.get(company_type)
