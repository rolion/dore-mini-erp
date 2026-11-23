"""Serializadores del reporte de ingresos y egresos: validan forma y tipos; el cálculo lo hace el dominio."""
from rest_framework import serializers

from modules.accounting.application.income_expense import IncomeExpenseReport


class IncomeExpenseFiltersSerializer(serializers.Serializer):
    """Query params: `period_id` y `months` (`yyyy-MM` separados por coma), ambos opcionales."""
    period_id = serializers.UUIDField(required=False)
    months = serializers.CharField(required=False, allow_blank=True)

    def validate_months(self, value: str) -> list[str]:
        return [part.strip() for part in value.split(',') if part.strip()]


def _money(value) -> str:
    return f'{value:.2f}'


def serialize_income_expense(report: IncomeExpenseReport) -> dict:
    period = report.period
    return {
        'period': None if period is None else {
            'id': str(period.id), 'name': period.name, 'date_from': period.start_date, 'date_to': period.end_date,
            'status': period.status},
        'months': [{'month': m.month, 'income': _money(m.income), 'expense': _money(m.expense),
                    'profit': _money(m.profit)} for m in report.months],
        'totals': {'income': _money(report.totals.income), 'expense': _money(report.totals.expense),
                   'profit': _money(report.totals.profit)},
    }
