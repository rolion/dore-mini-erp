import uuid

from django.db import models


class CompanySettingsModel(models.Model):
    """Marca que la empresa ya recibió sus módulos por defecto (distingue 'sin inicializar' de 'todo apagado')."""

    company_id = models.UUIDField(primary_key=True)
    initialized_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'modularity_company_settings'


class CompanyModuleModel(models.Model):
    """Módulo no base habilitado para una empresa. `company_id` sin FK, como el resto de módulos."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    module_key = models.CharField(max_length=40)
    enabled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'modularity_company_module'
        constraints = [
            models.UniqueConstraint(fields=['company_id', 'module_key'], name='modularity_company_module_unique'),
        ]
