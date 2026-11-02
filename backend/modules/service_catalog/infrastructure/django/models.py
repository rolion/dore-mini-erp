import uuid

from django.db import models
from django.db.models.functions import Trim, Upper


class ServiceModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, blank=True, default='')
    description = models.TextField(blank=True, default='')
    base_price = models.DecimalField(max_digits=12, decimal_places=2)
    duration_minutes = models.PositiveIntegerField()
    specialty_id = models.UUIDField(null=True, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'service_catalog_service'
        ordering = ['name', 'id']
        constraints = [
            models.UniqueConstraint(fields=['company_id', 'code'], condition=~models.Q(code=''),
                                    name='service_company_code_unique'),
            models.CheckConstraint(condition=models.Q(code=Upper(Trim('code'))), name='service_code_upper_trim'),
            models.CheckConstraint(condition=models.Q(base_price__gte=0), name='service_price_nonnegative'),
            models.CheckConstraint(condition=models.Q(duration_minutes__gt=0), name='service_duration_positive'),
        ]
