"""Numera las compras que ya se habían confirmado antes de la serie correlativa (ADR numeración de compras).

Se numera toda compra con `confirmed_at` (confirmadas y **canceladas que llegaron a confirmarse**, porque cancelar no
borra `confirmed_at`), por empresa y período fiscal que contiene `purchase_date`, en orden `confirmed_at, created_at,
id`. Quedan sin número los borradores, las canceladas que nunca se confirmaron y las de fecha fuera de todo período.
Los períodos cerrados sí se numeran (es histórico). Repetible: continúa desde el contador de cada período y solo toca
compras sin número. Solo lee `accounting_fiscal_period` (company_id, start_date, end_date, name).
"""
from django.db import migrations


def backfill(apps, schema_editor):
    Purchase = apps.get_model('purchases', 'PurchaseModel')
    Counter = apps.get_model('purchases', 'PurchaseNumberCounterModel')
    Period = apps.get_model('accounting', 'FiscalPeriodModel')

    pending = (Purchase.objects.filter(number__isnull=True, confirmed_at__isnull=False)
               .order_by('company_id', 'confirmed_at', 'created_at', 'id'))
    periods: dict = {}
    last: dict = {}
    touched: set = set()
    for purchase in pending.iterator(chunk_size=500):
        if purchase.company_id not in periods:
            periods[purchase.company_id] = list(Period.objects.filter(company_id=purchase.company_id))
        period = next((p for p in periods[purchase.company_id]
                       if p.start_date <= purchase.purchase_date <= p.end_date), None)
        if period is None:
            continue
        key = (purchase.company_id, period.id)
        if key not in last:
            counter = Counter.objects.filter(company_id=purchase.company_id, fiscal_period_id=period.id).first()
            last[key] = counter.last_number if counter else 0
        last[key] += 1
        touched.add(key)
        Purchase.objects.filter(pk=purchase.pk).update(
            fiscal_period_id=period.id, fiscal_period_name=period.name, number=last[key])
    for company_id, period_id in touched:
        Counter.objects.update_or_create(
            company_id=company_id, fiscal_period_id=period_id,
            defaults={'last_number': last[(company_id, period_id)]})


class Migration(migrations.Migration):
    dependencies = [
        ('purchases', '0010_purchase_number_fields'),
        ('accounting', '0009_fiscal_period'),
    ]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
