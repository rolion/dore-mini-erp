import uuid

from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower


class ExpenseCategoryModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'expenses_category'
        ordering = ['name', 'id']
        constraints = [
            # El nombre es único sin distinguir mayúsculas: dos "Empaque" repartirían un mismo concepto en los reportes.
            models.UniqueConstraint(Lower('name'), name='expenses_category_name_ci_unique'),
        ]


class ExpenseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # FK dentro del mismo módulo; PROTECT impide borrar físicamente una categoría usada (REQ-EXP-006).
    category = models.ForeignKey(ExpenseCategoryModel, on_delete=models.PROTECT, related_name='expenses')
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField(db_index=True)
    payment_method = models.CharField(max_length=20)
    supplier_name = models.CharField(max_length=150, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    status = models.CharField(max_length=10, db_index=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'expenses_expense'
        ordering = ['-expense_date', '-created_at', 'id']
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name='expenses_expense_amount_gt_0'),
        ]
