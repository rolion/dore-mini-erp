"""Fixture de pruebas: un período fiscal abierto amplio, porque confirmar un pedido exige uno (ADR numeración)."""
from datetime import date

from modules.accounting.infrastructure.django.models import FiscalPeriodModel


def open_test_period(company_id, name='Pruebas', start=date(2000, 1, 1), end=date(2099, 12, 31)):
    """Crea (una sola vez por empresa y nombre) un período OPEN que contiene todas las fechas de las pruebas."""
    period, _ = FiscalPeriodModel.objects.get_or_create(
        company_id=company_id, name=name, defaults={'start_date': start, 'end_date': end, 'status': 'OPEN'})
    return period
