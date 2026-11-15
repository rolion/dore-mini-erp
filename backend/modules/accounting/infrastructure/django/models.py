import uuid

from django.db import models
from django.db.models import Q
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


class EntryModel(models.Model):
    """Entrada del libro: dinero recibido por un pago de origen. Solo se inserta; nunca se actualiza ni se borra."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    # Cuenta usada al cobrar; las cuentas no se eliminan, por eso PROTECT.
    account = models.ForeignKey(AccountModel, on_delete=models.PROTECT, related_name='+')
    currency = models.CharField(max_length=3)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    payment_method = models.CharField(max_length=20)
    # Pago de origen por UUID (sin FK entre módulos) y datos de trazabilidad en texto.
    origin_kind = models.CharField(max_length=10)
    origin_id = models.UUIDField()
    origin_document_ref = models.CharField(max_length=60, blank=True, default='')
    receipt_number = models.CharField(max_length=20, blank=True, default='')
    recorded_by = models.BigIntegerField(null=True, blank=True)
    recorded_by_name = models.CharField(max_length=150, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    # Regularización de pagos históricos (PB-ACC-004): fecha y ejecutor aparte del autor del cobro original.
    regularized_at = models.DateTimeField(null=True, blank=True)
    regularized_by_name = models.CharField(max_length=150, blank=True, default='')

    class Meta:
        db_table = 'accounting_entry'
        ordering = ['-payment_date', '-created_at', 'id']
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name='accounting_entry_amount_gt_0'),
            models.UniqueConstraint(fields=['company_id', 'origin_kind', 'origin_id'], name='accounting_entry_origin_uniq'),
        ]
        indexes = [
            models.Index(fields=['company_id', 'payment_date'], name='accounting_entry_date'),
            models.Index(fields=['company_id', 'account'], name='accounting_entry_account'),
        ]
