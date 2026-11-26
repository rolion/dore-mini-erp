"""Numera los pedidos ya confirmados antes de la serie correlativa (ADR numeración correlativa).

Por empresa y período fiscal que contiene `order_date`, en orden `created_at, id`. Quedan sin número los pedidos NEW,
los CANCELLED heredados (no hay historial para saber si llegaron a confirmarse) y los de fecha fuera de todo período.
Los períodos cerrados sí se numeran (es histórico). Es repetible: continúa desde el contador de cada período y solo
toca pedidos sin número. Solo lee `accounting_fiscal_period` (company_id, start_date, end_date).
"""
from django.db import migrations

UNNUMBERED_STATUSES = ('NEW', 'CANCELLED')


def backfill(apps, schema_editor):
    Order = apps.get_model('sales', 'OrderModel')
    Counter = apps.get_model('sales', 'OrderNumberCounterModel')
    Period = apps.get_model('accounting', 'FiscalPeriodModel')

    pending = (Order.objects.filter(number__isnull=True).exclude(status__in=UNNUMBERED_STATUSES)
               .order_by('company_id', 'created_at', 'id'))
    periods: dict = {}
    last: dict = {}
    touched: set = set()
    for order in pending.iterator(chunk_size=500):
        if order.company_id not in periods:
            periods[order.company_id] = list(Period.objects.filter(company_id=order.company_id))
        period = next((p for p in periods[order.company_id] if p.start_date <= order.order_date <= p.end_date), None)
        if period is None:
            continue
        key = (order.company_id, period.id)
        if key not in last:
            counter = Counter.objects.filter(company_id=order.company_id, fiscal_period_id=period.id).first()
            last[key] = counter.last_number if counter else 0
        last[key] += 1
        touched.add(key)
        Order.objects.filter(pk=order.pk).update(
            fiscal_period_id=period.id, fiscal_period_name=period.name, number=last[key])
    for company_id, period_id in touched:
        Counter.objects.update_or_create(
            company_id=company_id, fiscal_period_id=period_id,
            defaults={'last_number': last[(company_id, period_id)]})


class Migration(migrations.Migration):
    dependencies = [
        ('sales', '0006_order_number_fields'),
        ('accounting', '0009_fiscal_period'),
    ]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
