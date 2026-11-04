import uuid

from django.db import models


class DentalProformaModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    number = models.CharField(max_length=20)
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=12, default='draft')
    # Identidad del paciente en Odontología (= cliente); solo UUID, sin FK entre módulos.
    customer_id = models.UUIDField()
    patient_name = models.CharField(max_length=150)
    date = models.DateField()
    valid_until = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=3, default='BOB')
    notes = models.TextField(blank=True, default='')
    created_by = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dentistry_proforma'
        ordering = ['-date', '-number', '-version']
        constraints = [
            models.UniqueConstraint(fields=['company_id', 'number', 'version'], name='dental_proforma_number_version'),
        ]
        indexes = [
            models.Index(fields=['company_id', 'customer_id', 'status'], name='dental_proforma_patient_status'),
        ]


class DentalProformaLineModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proforma = models.ForeignKey(DentalProformaModel, on_delete=models.CASCADE, related_name='lines')
    position = models.PositiveIntegerField()
    service_id = models.UUIDField()
    description = models.CharField(max_length=150)
    quantity = models.DecimalField(max_digits=8, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    dental_piece = models.CharField(max_length=20, blank=True, default='')

    class Meta:
        db_table = 'dentistry_proforma_line'
        ordering = ['position']
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name='dental_line_quantity_positive'),
            models.CheckConstraint(condition=models.Q(unit_price__gte=0), name='dental_line_price_nonnegative'),
        ]


class DentalProformaCounterModel(models.Model):
    company_id = models.UUIDField(primary_key=True, db_index=True)  # la PK ya lo indexa; db_index lo declara
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'dentistry_proforma_counter'
