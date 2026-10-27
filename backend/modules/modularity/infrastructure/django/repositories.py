from uuid import UUID

from django.db import transaction

from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS

from .models import CompanyModuleModel, CompanySettingModel, CompanySettingsModel, SettingChangeModel


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


class DjangoCompanySettingRepository:
    """Valores guardados de los ajustes de una empresa: toda consulta filtra por `company_id`."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def values(self) -> dict[str, str]:
        rows = CompanySettingModel.objects.filter(company_id=self.company_id)
        return {row.setting_key: row.value for row in rows}

    def lock_values(self) -> dict[str, str]:
        """Serializa los guardados de la empresa (bloquea su fila de configuración) y devuelve los valores."""
        CompanySettingsModel.objects.get_or_create(company_id=self.company_id)
        CompanySettingsModel.objects.select_for_update().get(company_id=self.company_id)
        return self.values()

    def save(self, key: str, value: str) -> None:
        CompanySettingModel.objects.update_or_create(
            company_id=self.company_id, setting_key=key, defaults={'value': value})


class DjangoSettingChangeRepository:
    """Historial de cambios de una empresa: solo inserta y lista (append-only)."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def add(self, *, scope: str, setting_key: str, setting_label: str, old_value: str, new_value: str,
            actor_id: int | None, actor_name: str) -> None:
        SettingChangeModel.objects.create(
            company_id=self.company_id, scope=scope, setting_key=setting_key, setting_label=setting_label,
            old_value=old_value, new_value=new_value, changed_by_id=actor_id, changed_by_name=actor_name)

    def list(self, scope: str, *, date_from=None, date_to=None, setting_key: str | None = None,
             offset: int = 0, limit: int = 20) -> tuple[int, list[SettingChangeModel]]:
        rows = SettingChangeModel.objects.filter(company_id=self.company_id, scope=scope)
        if date_from is not None:
            rows = rows.filter(changed_at__date__gte=date_from)
        if date_to is not None:
            rows = rows.filter(changed_at__date__lte=date_to)
        if setting_key:
            rows = rows.filter(setting_key=setting_key)
        return rows.count(), list(rows[offset:offset + limit])
