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
    # PB-COT-002: vínculo con la línea de la versión anterior (sin FK) y su tipo en esta versión.
    origin_line_id = models.UUIDField(null=True, blank=True)
    line_kind = models.CharField(max_length=12, default='original')

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


class ProformaLineDecisionModel(models.Model):
    """Libro append-only de decisiones por línea: nunca se actualiza ni se borra (salvo `carried` en borradores)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    line = models.ForeignKey(ProformaLineModel, on_delete=models.CASCADE, related_name='decisions')
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
        db_table = 'quotations_proforma_line_decision'
        ordering = ['decided_at', 'id']


class ProformaDecisionBatchModel(models.Model):
    """Una fila por operación confirmada: hace idempotentes los reintentos con la misma clave."""
    id = models.BigAutoField(primary_key=True)
    company_id = models.UUIDField()
    idempotency_key = models.UUIDField()
    proforma_id = models.UUIDField()
    payload_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'quotations_proforma_decision_batch'
        constraints = [
            models.UniqueConstraint(fields=['company_id', 'idempotency_key'], name='proforma_batch_key_unique'),
        ]
