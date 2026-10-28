import uuid

from django.db import models
from django.db.models.functions import Lower


class WarehouseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Empresa propietaria; solo UUID, sin FK (los módulos no acoplan modelos ni migraciones).
    company_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default='')
    active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inventory_warehouse'
        ordering = ['name', 'id']
        constraints = [
            models.UniqueConstraint(Lower('name'), 'company_id', name='inventory_warehouse_name_ci_uniq'),
            models.UniqueConstraint(
                fields=['company_id'], condition=models.Q(is_default=True), name='inventory_warehouse_one_default'),
        ]


class StockMovementModel(models.Model):
    """Libro de movimientos: solo se inserta; lo único que se actualiza es `status` al revertir."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField()
    # Sin FK al producto (es de otro módulo); el almacén sí es de este módulo.
    product_id = models.UUIDField()
    warehouse = models.ForeignKey(WarehouseModel, on_delete=models.PROTECT, related_name='+')
    kind = models.CharField(max_length=3)
    quantity = models.DecimalField(max_digits=16, decimal_places=4)
    occurred_at = models.DateTimeField()
    user_id = models.UUIDField(null=True, blank=True)
    user_name = models.CharField(max_length=200, blank=True, default='')
    reference = models.CharField(max_length=200, blank=True, default='')
    reason = models.CharField(max_length=200, blank=True, default='')
    source_type = models.CharField(max_length=40, null=True, blank=True)
    source_id = models.CharField(max_length=100, blank=True, default='')
    source_line = models.CharField(max_length=100, blank=True, default='')
    status = models.CharField(max_length=10, default='confirmed')
    reverses_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'inventory_stock_movement'
        ordering = ['-occurred_at', '-created_at', 'id']
        indexes = [
            models.Index(fields=['company_id', 'occurred_at'], name='inv_mov_company_date_idx'),
            models.Index(fields=['company_id', 'product_id', 'warehouse'], name='inv_mov_company_prod_wh_idx'),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name='inv_mov_quantity_positive'),
            models.UniqueConstraint(
                fields=['company_id', 'source_type', 'source_id', 'source_line', 'product_id', 'warehouse', 'kind'],
                condition=models.Q(source_type__isnull=False), name='inv_mov_source_operation_uniq'),
            models.UniqueConstraint(
                fields=['reverses_id'], condition=models.Q(reverses_id__isnull=False),
                name='inv_mov_one_reversal_uniq'),
        ]
