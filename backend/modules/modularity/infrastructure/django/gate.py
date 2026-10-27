from uuid import UUID

from modules.modularity.domain.modules import effective_enabled

from .repositories import DjangoCompanyModuleRepository


def enabled_keys(company_id: UUID) -> set[str]:
    """Módulos habilitados de la empresa (base + elegidos), tal como los consulta el puerto `shared.module_gate`."""
    return effective_enabled(DjangoCompanyModuleRepository(company_id).enabled_keys())
