from uuid import UUID

from django.db import transaction

from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS

from .models import CompanyModuleModel, CompanySettingsModel


class DjangoCompanyModuleRepository:
    """Módulos habilitados de una empresa: toda consulta filtra por `company_id`."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def enabled_keys(self) -> set[str]:
        """Claves no base habilitadas; la primera vez siembra los valores por defecto (sin migración por empresa)."""
        with transaction.atomic():
            _, created = CompanySettingsModel.objects.get_or_create(company_id=self.company_id)
            if created:
                CompanyModuleModel.objects.bulk_create(
                    [CompanyModuleModel(company_id=self.company_id, module_key=key) for key in DEFAULT_ENABLED_KEYS],
                    ignore_conflicts=True,
                )
        return set(CompanyModuleModel.objects.filter(company_id=self.company_id).values_list('module_key', flat=True))

    def enable(self, key: str) -> None:
        CompanyModuleModel.objects.get_or_create(company_id=self.company_id, module_key=key)

    def disable(self, key: str) -> None:
        CompanyModuleModel.objects.filter(company_id=self.company_id, module_key=key).delete()
