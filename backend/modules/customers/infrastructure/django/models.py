import uuid

from django.db import models


class CustomerModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    # Índice no único: el teléfono repetido es una advertencia confirmable, no una restricción (REQ-CUS-006).
    phone = models.CharField(max_length=30, blank=True, default='', db_index=True)
    email = models.CharField(max_length=254, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customers_customer'
        ordering = ['name', 'id']
