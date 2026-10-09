"""Fachada pública de solo lectura del módulo Expenses para otros módulos (p. ej. Reporting).

Es la única vía de entrada entre módulos: devuelve DTO inmutables, nunca entidades ni modelos.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from django.db.models import Sum

from modules.expenses.domain.enums import ExpenseStatus
from modules.expenses.infrastructure.django.models import ExpenseModel

ZERO = Decimal('0.00')


@dataclass(frozen=True)
class CategoryExpense:
    category_id: UUID
    name: str
    active: bool
    total: Decimal


@dataclass(frozen=True)
class ExpenseReport:
    """Gastos vigentes del rango; `total` es siempre la suma de `rows` (misma consulta)."""

    total: Decimal
    rows: tuple[CategoryExpense, ...]


def get_expense_report(date_from: date, date_to: date) -> ExpenseReport:
    """Gastos vigentes con `expense_date` entre ambas fechas (inclusive), por categoría y de mayor a menor monto.

    Incluye categorías inactivas con monto; excluye los gastos anulados.
    """
    grouped = (
        ExpenseModel.objects
        .filter(status=ExpenseStatus.ACTIVE.value, expense_date__gte=date_from, expense_date__lte=date_to)
        .values('category_id', 'category__name', 'category__active')
        .annotate(total=Sum('amount'))
        .order_by('-total', 'category__name', 'category_id')
    )
    rows = tuple(
        CategoryExpense(category_id=row['category_id'], name=row['category__name'],
                        active=row['category__active'], total=row['total'])
        for row in grouped
    )
    return ExpenseReport(total=sum((row.total for row in rows), ZERO), rows=rows)
