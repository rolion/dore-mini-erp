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
    # PB-COT-002: vínculo con la línea de la versión anterior (sin FK) y su tipo en esta versión.
    origin_line_id = models.UUIDField(null=True, blank=True)
    line_kind = models.CharField(max_length=12, default='original')

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


class DentalProformaLineDecisionModel(models.Model):
    """Libro append-only de decisiones por línea: nunca se actualiza ni se borra (salvo `carried` en borradores)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    line = models.ForeignKey(DentalProformaLineModel, on_delete=models.CASCADE, related_name='decisions')
    kind = models.CharField(max_length=14)
    decision = models.CharField(max_length=10)
    decided_at = models.DateTimeField()
    recorded_by = models.BigIntegerField(null=True, blank=True)
    recorded_by_name = models.CharField(max_length=150, blank=True, default='')
    accepted_by_name = models.CharField(max_length=120, blank=True, default='')
    medium = models.CharField(max_length=20, blank=True, default='')
    reference = models.CharField(max_length=200, blank=True, default='')
    reason = models.CharField(max_length=500, blank=True, default='')
    batch_key = models.UUIDField(null=True, blank=True)
    source_decision_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'dentistry_proforma_line_decision'
        ordering = ['decided_at', 'id']


class DentalProformaDecisionBatchModel(models.Model):
    """Una fila por operación confirmada: hace idempotentes los reintentos con la misma clave."""
    id = models.BigAutoField(primary_key=True)
    company_id = models.UUIDField(db_index=True)
    idempotency_key = models.UUIDField()
    proforma_id = models.UUIDField()
    payload_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'dentistry_proforma_decision_batch'
        constraints = [
            models.UniqueConstraint(fields=['company_id', 'idempotency_key'], name='dental_batch_key_unique'),
        ]
