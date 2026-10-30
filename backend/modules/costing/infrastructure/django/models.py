import uuid

from django.db import models


class ValuationAdoptionModel(models.Model):
    """Adopción de la valoración inicial: una por empresa; solo se inserta."""

    id = models.UUIDField(primary_key=True, editable=False)  # clave de idempotencia del cliente
    company_id = models.UUIDField(db_index=True)
    cutoff_at = models.DateTimeField()
    method = models.CharField(max_length=40)
    user_id = models.UUIDField(null=True, blank=True)
    user_name = models.CharField(max_length=200, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'costing_valuation_adoption'
        constraints = [models.UniqueConstraint(fields=['company_id'], name='costing_adoption_one_per_company')]


class ValuationLineModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    adoption = models.ForeignKey(ValuationAdoptionModel, on_delete=models.PROTECT, related_name='lines')
    company_id = models.UUIDField(db_index=True)
    # Sin FK al producto (es de otro módulo).
    product_id = models.UUIDField()
    reconciled_quantity = models.DecimalField(max_digits=16, decimal_places=4)
    total_value = models.DecimalField(max_digits=16, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=20, decimal_places=6)
    declared_zero = models.BooleanField(default=False)
    source = models.CharField(max_length=200)

    class Meta:
        db_table = 'costing_valuation_line'
        constraints = [
            models.UniqueConstraint(fields=['adoption', 'product_id'], name='costing_line_product_uniq'),
            models.CheckConstraint(condition=models.Q(total_value__gte=0), name='costing_line_value_nonneg'),
            models.CheckConstraint(condition=models.Q(reconciled_quantity__gt=0), name='costing_line_qty_positive'),
        ]
