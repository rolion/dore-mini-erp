import uuid

from django.db import models
from django.db.models.functions import Lower


class UnitModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Empresa propietaria; solo UUID, sin FK (los módulos no acoplan modelos ni migraciones).
    company_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=100)
    abbreviation = models.CharField(max_length=10)
    allows_fractions = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'catalog_unit'
        ordering = ['name', 'id']
        constraints = [
            models.UniqueConstraint(Lower('name'), 'company_id', name='catalog_unit_name_ci_uniq'),
            models.UniqueConstraint(Lower('abbreviation'), 'company_id', name='catalog_unit_abbr_ci_uniq'),
        ]


class ProductModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Empresa propietaria; solo UUID, sin FK (los módulos no acoplan modelos ni migraciones).
    company_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default='')
    # Solo obligatorio si el producto se puede vender.
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    # Productos existentes: vendibles, no comprables y sin clasificar hasta que se revisen.
    category = models.CharField(max_length=20, null=True, blank=True)
    can_buy = models.BooleanField(default=False)
    can_sell = models.BooleanField(default=True)
    active = models.BooleanField(default=True)
    # Los productos existentes no controlan stock hasta configurarlos expresamente.
    tracks_stock = models.BooleanField(default=False)
    base_unit = models.ForeignKey(UnitModel, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'catalog_product'
        ordering = ['name', 'id']
