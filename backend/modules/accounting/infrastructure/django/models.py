import uuid

from django.db import models
from django.db.models.functions import Lower


class AccountModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Empresa propietaria; solo UUID, sin FK (los módulos no acoplan modelos ni migraciones).
    company_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=80)
    currency = models.CharField(max_length=3)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounting_account'
        ordering = ['name', 'id']
        constraints = [
            models.UniqueConstraint(Lower('name'), 'company_id', name='accounting_account_name_ci_uniq'),
        ]


class MethodMappingModel(models.Model):
    """Destino vigente de un método de pago por empresa (una fila por método)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    method = models.CharField(max_length=20)
    account = models.ForeignKey(AccountModel, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounting_method_mapping'
        constraints = [
            models.UniqueConstraint(fields=['company_id', 'method'], name='accounting_mapping_method_uniq'),
        ]
