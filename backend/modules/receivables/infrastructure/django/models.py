import uuid

from django.db import models
from django.db.models import Q


class ObligationModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    source_kind = models.CharField(max_length=10)
    source_number = models.CharField(max_length=20)
    # Instantánea para listar sin leer la fuente; referencias solo por UUID, sin FK entre módulos.
    customer_id = models.UUIDField()
    customer_name = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'receivables_obligation'
        ordering = ['-created_at', 'id']
        constraints = [
            models.UniqueConstraint(fields=['company_id', 'source_kind', 'source_number'],
                                    name='obligation_source_unique'),
        ]
        indexes = [models.Index(fields=['company_id', 'customer_id'], name='obligation_customer')]


class PaymentModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    obligation = models.ForeignKey(ObligationModel, on_delete=models.CASCADE, related_name='payments')
    receipt_number = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20)
    payment_date = models.DateField()
    reference = models.CharField(max_length=100, blank=True, default='')
    recorded_by = models.BigIntegerField(null=True, blank=True)
    recorded_by_name = models.CharField(max_length=150, blank=True, default='')
    idempotency_key = models.UUIDField()
    payload_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'receivables_payment'
        ordering = ['created_at', 'id']
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name='receivables_payment_amount_gt_0'),
            models.UniqueConstraint(fields=['company_id', 'idempotency_key'], name='receivables_payment_key_unique'),
            models.UniqueConstraint(fields=['company_id', 'receipt_number'], name='receivables_receipt_unique'),
        ]


class AllocationModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(PaymentModel, on_delete=models.CASCADE, related_name='allocations')
    lineage_id = models.UUIDField(db_index=True)
    line_id = models.UUIDField()
    description = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'receivables_allocation'
        ordering = ['id']
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name='receivables_allocation_amount_gt_0')]


class ReceiptCounterModel(models.Model):
    company_id = models.UUIDField(primary_key=True)
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'receivables_counter'
