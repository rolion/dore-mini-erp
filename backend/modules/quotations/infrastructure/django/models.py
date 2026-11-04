import uuid

from django.db import models


class ProformaModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    number = models.CharField(max_length=20)
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=12, default='draft')
    customer_id = models.UUIDField()
    customer_name = models.CharField(max_length=150)
    date = models.DateField()
    valid_until = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=3, default='BOB')
    notes = models.TextField(blank=True, default='')
    # Reservado para una historia posterior (aceptación); no se expone ni se calcula.
    accepted_total = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    created_by = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'quotations_proforma'
        ordering = ['-date', '-number', '-version']
        constraints = [
            models.UniqueConstraint(fields=['company_id', 'number', 'version'], name='proforma_number_version_unique'),
        ]
        indexes = [
            models.Index(fields=['company_id', 'status', 'date'], name='proforma_status_date'),
            models.Index(fields=['company_id', 'customer_id'], name='proforma_customer'),
        ]


class ProformaLineModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proforma = models.ForeignKey(ProformaModel, on_delete=models.CASCADE, related_name='lines')
    position = models.PositiveIntegerField()
    service_id = models.UUIDField()
    description = models.CharField(max_length=150)
    quantity = models.DecimalField(max_digits=8, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    # Reservados: aún no existe el módulo de tratamientos; no se validan ni se ofrecen en la UI.
    treatment_item_id = models.UUIDField(null=True, blank=True)
    piece = models.CharField(max_length=20, blank=True, default='')

    class Meta:
        db_table = 'quotations_proforma_line'
        ordering = ['position']
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name='proforma_line_quantity_positive'),
            models.CheckConstraint(condition=models.Q(unit_price__gte=0), name='proforma_line_price_nonnegative'),
        ]


class ProformaCounterModel(models.Model):
    company_id = models.UUIDField(primary_key=True)
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'quotations_proforma_counter'
