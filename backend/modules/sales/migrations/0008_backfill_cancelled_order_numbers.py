"""Numera los pedidos CANCELLED anteriores a la serie correlativa que `0007` dejó sin número.

Decisión del usuario (PLAN v2): todo cancelado heredado cuya fecha cae en un período fiscal recibe número, aunque quizá
nunca se confirmó (no hay historial para saberlo). `0007` ya numeró el resto, así que estos toman los siguientes
números de su período, en orden `created_at, id`. Repetible: solo toca pedidos sin número y continúa desde el contador.
"""
from django.db import migrations


def backfill(apps, schema_editor):
    Order = apps.get_model('sales', 'OrderModel')
    Counter = apps.get_model('sales', 'OrderNumberCounterModel')
    Period = apps.get_model('accounting', 'FiscalPeriodModel')

    pending = Order.objects.filter(number__isnull=True, status='CANCELLED').order_by('company_id', 'created_at', 'id')
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
        ('sales', '0007_backfill_order_numbers'),
        ('accounting', '0009_fiscal_period'),
    ]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
