from uuid import UUID

from modules.modularity.domain.modules import effective_enabled
from shared import module_extensions

from .repositories import DjangoCompanyModuleRepository


def enabled_keys(company_id: UUID) -> set[str]:
    """Módulos habilitados de la empresa (base + elegidos), tal como los consulta el puerto `shared.module_gate`."""
    return effective_enabled(DjangoCompanyModuleRepository(company_id).enabled_keys())


class SharedModuleExtensions:
    """Adaptador del puerto de extensiones de `shared` para una empresa."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def available_capabilities(self, keys) -> set[str]:
        return {key for key in keys if module_extensions.capability_available(self.company_id, key)}

    def disable_blockers(self, module_key: str) -> list:
        return module_extensions.disable_blockers(self.company_id, module_key)

    def on_enabled(self, module_key: str, adopted_at) -> None:
        module_extensions.run_enable_hooks(self.company_id, module_key, adopted_at)
