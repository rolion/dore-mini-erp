import uuid

from django.db import models
from django.db.models import Q


class ImportRunModel(models.Model):
    """Un archivo subido con su mapeo, opciones y resultado. Las filas guardadas ya están normalizadas a texto."""

    UPLOADED = 'UPLOADED'
    PREVIEWED = 'PREVIEWED'
    QUEUED = 'QUEUED'
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    STATUSES = [(s, s) for s in (UPLOADED, PREVIEWED, QUEUED, RUNNING, COMPLETED, FAILED)]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)  # solo UUID, sin FK entre módulos
    kind = models.CharField(max_length=20, default='SALES')
    filename = models.CharField(max_length=255)
    file_sha256 = models.CharField(max_length=64)
    headers = models.JSONField(default=list)
    rows = models.JSONField(default=list)
    row_count = models.PositiveIntegerField(default=0)
    mapping = models.JSONField(default=dict, blank=True)
    options = models.JSONField(default=dict, blank=True)
    preview_signature = models.CharField(max_length=64, blank=True, default='')
    status = models.CharField(max_length=12, choices=STATUSES, default=UPLOADED)
    counts = models.JSONField(default=dict, blank=True)
    processed_count = models.PositiveIntegerField(default=0)  # ventas ya tratadas por el worker
    total_count = models.PositiveIntegerField(default=0)  # ventas que el worker debe tratar (0 hasta que arranca)
    failure_code = models.CharField(max_length=60, blank=True, default='')
    failure_message = models.TextField(blank=True, default='')
    idempotency_key = models.UUIDField(null=True, blank=True)
    created_by_id = models.UUIDField(null=True, blank=True)
    created_by_name = models.CharField(max_length=150, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    heartbeat_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'data_import_run'
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['company_id', '-created_at'], name='di_run_company_created_idx')]
        constraints = [
            # INV-09: una sola ejecución activa (en cola o en curso) por empresa.
            models.UniqueConstraint(fields=['company_id'], condition=Q(status__in=['QUEUED', 'RUNNING']),
                                    name='di_run_one_active_per_company'),
        ]


class ImportRowResultModel(models.Model):
    """Resultado de una venta importada (identificada por su primera fila) con los ids que creó."""

    CREATED = 'CREATED'
    SKIPPED_DUPLICATE = 'SKIPPED_DUPLICATE'
    FAILED = 'FAILED'
    CREATED_WITHOUT_POSTING = 'CREATED_WITHOUT_POSTING'
    STATUSES = [(s, s) for s in (CREATED, SKIPPED_DUPLICATE, FAILED, CREATED_WITHOUT_POSTING)]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(ImportRunModel, on_delete=models.CASCADE, related_name='results')
    row_number = models.PositiveIntegerField()
    sale_key = models.CharField(max_length=100)
    status = models.CharField(max_length=24, choices=STATUSES)
    code = models.CharField(max_length=60, blank=True, default='')
    message = models.TextField(blank=True, default='')
    order_id = models.UUIDField(null=True, blank=True)
    created_refs = models.JSONField(default=dict, blank=True)  # purchase_ids, product_ids, customer_id

    class Meta:
        db_table = 'data_import_row_result'
        ordering = ['row_number', 'id']
        indexes = [models.Index(fields=['run', 'row_number'], name='di_result_run_row_idx')]


class ImportedSaleModel(models.Model):
    """Garantía de idempotencia (INV-05): una venta ya importada nunca se vuelve a crear."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    source_key = models.CharField(max_length=100)
    order_id = models.UUIDField()
    run_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'data_import_sale'
        constraints = [models.UniqueConstraint(fields=['company_id', 'source_key'], name='di_sale_company_key_uniq')]
