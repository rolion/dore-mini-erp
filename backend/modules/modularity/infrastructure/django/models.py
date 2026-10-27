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


class CompanySettingModel(models.Model):
    """Valor guardado de un ajuste para una empresa. Sin fila rige el valor inicial del catálogo."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    setting_key = models.CharField(max_length=80)
    value = models.CharField(max_length=200, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'modularity_company_setting'
        constraints = [
            models.UniqueConstraint(fields=['company_id', 'setting_key'], name='modularity_company_setting_unique'),
        ]


class SettingChangeModel(models.Model):
    """Historial append-only de cambios de ajustes (y de activación de módulos, ámbito `modules`).

    Guarda valores presentables y snapshots de etiqueta y usuario para que no cambien con el tiempo.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField()
    scope = models.CharField(max_length=40)
    setting_key = models.CharField(max_length=80)
    setting_label = models.CharField(max_length=150)
    old_value = models.CharField(max_length=200, blank=True)
    new_value = models.CharField(max_length=200, blank=True)
    changed_by_id = models.IntegerField(null=True)
    changed_by_name = models.CharField(max_length=150)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'modularity_setting_change'
        ordering = ['-changed_at', '-id']
        indexes = [models.Index(fields=['company_id', 'scope', '-changed_at'], name='modularity_change_lookup')]
