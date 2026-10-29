import uuid

from django.db import models


class SupplierModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Empresa propietaria; solo UUID, sin FK (los módulos no acoplan modelos ni migraciones).
    company_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=150)
    tax_id = models.CharField(max_length=50, blank=True, default='')
    phone = models.CharField(max_length=30, blank=True, default='')
    email = models.CharField(max_length=254, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'purchases_supplier'
        ordering = ['name', 'id']
        indexes = [models.Index(fields=['company_id', 'active'], name='purch_supplier_company_active')]
