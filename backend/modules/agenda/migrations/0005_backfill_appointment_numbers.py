"""Numera las citas anteriores a la serie correlativa (decisión del usuario).

Cada cita recibe número en la gestión fiscal (período) que contiene su fecha de creación en America/La_Paz, por
empresa y en orden `created_at, id`. Las citas cuya fecha de creación cae fuera de toda gestión quedan sin número y
siguen mostrando su código corto. Repetible: solo toca citas sin número y continúa desde el contador.
"""
from zoneinfo import ZoneInfo

from django.db import migrations

ZONE = ZoneInfo('America/La_Paz')


def backfill(apps, schema_editor):
    Appointment = apps.get_model('agenda', 'Appointment')
    Counter = apps.get_model('agenda', 'AppointmentNumberCounter')
    Period = apps.get_model('accounting', 'FiscalPeriodModel')

    pending = Appointment.objects.filter(number__isnull=True).order_by('company_id', 'created_at', 'id')
    periods: dict = {}
    last: dict = {}
    touched: set = set()
    for appointment in pending.iterator(chunk_size=500):
        company_id = appointment.company_id
        if company_id not in periods:
            periods[company_id] = list(Period.objects.filter(company_id=company_id))
        day = appointment.created_at.astimezone(ZONE).date()
        period = next((p for p in periods[company_id] if p.start_date <= day <= p.end_date), None)
        if period is None:
            continue
        key = (company_id, period.id)
        if key not in last:
            counter = Counter.objects.filter(company_id=company_id, fiscal_period_id=period.id).first()
            last[key] = counter.last_number if counter else 0
        last[key] += 1
        touched.add(key)
        Appointment.objects.filter(pk=appointment.pk).update(
            fiscal_period_id=period.id, fiscal_period_name=period.name, number=last[key])
    for company_id, period_id in touched:
        Counter.objects.update_or_create(
            company_id=company_id, fiscal_period_id=period_id,
            defaults={'last_number': last[(company_id, period_id)]})


class Migration(migrations.Migration):
    dependencies = [
        ('agenda', '0004_appointment_numbers'),
        ('accounting', '0009_fiscal_period'),
    ]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
