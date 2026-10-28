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
    """Movimiento de existencias: inmutable (solo se agregan filas). `quantity` lleva signo; la apertura es >= 0."""

    OPENING = 'opening'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField()
    warehouse = models.ForeignKey(WarehouseModel, on_delete=models.PROTECT, related_name='movements')
    # Producto de Catálogo: solo UUID, sin FK entre módulos.
    product_id = models.UUIDField()
    movement_type = models.CharField(max_length=20, choices=[(OPENING, 'Apertura')])
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    movement_date = models.DateField()
    reference = models.CharField(max_length=100)
    # Clave de idempotencia de la apertura que lo originó (todas sus líneas la comparten).
    opening_id = models.UUIDField(null=True, blank=True)
    created_by_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'inventory_stock_movement'
        ordering = ['-movement_date', '-created_at', '-id']
        indexes = [
            models.Index(fields=['company_id', 'product_id'], name='inventory_mov_company_product'),
            models.Index(fields=['company_id', 'warehouse', 'product_id'], name='inventory_mov_company_wh_prod'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['company_id', 'opening_id', 'product_id'], condition=models.Q(opening_id__isnull=False),
                name='inventory_movement_opening_product_uniq'),
            models.UniqueConstraint(
                fields=['company_id', 'warehouse', 'product_id'], condition=models.Q(movement_type='opening'),
                name='inventory_movement_one_opening'),
            models.CheckConstraint(
                condition=~models.Q(movement_type='opening') | models.Q(quantity__gte=0),
                name='inventory_movement_opening_qty_gte_0'),
        ]


class StockBalanceModel(models.Model):
    """Existencia actual de un producto en un almacén; cambia solo junto con un movimiento."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField()
    warehouse = models.ForeignKey(WarehouseModel, on_delete=models.PROTECT, related_name='balances')
    product_id = models.UUIDField()
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inventory_stock_balance'
        ordering = ['warehouse__name', '-updated_at', 'product_id']
        constraints = [
            models.UniqueConstraint(
                fields=['company_id', 'warehouse', 'product_id'], name='inventory_balance_company_wh_prod_uniq'),
        ]
