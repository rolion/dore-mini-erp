"""Registra como importadas las ventas cargadas antes de que la importación guardara su clave de idempotencia."""
from django.db import migrations

CREATED = ('CREATED', 'CREATED_WITHOUT_POSTING')


def backfill(apps, schema_editor):
    Result = apps.get_model('data_import', 'ImportRowResultModel')
    Sale = apps.get_model('data_import', 'ImportedSaleModel')
    pending = []
    results = (Result.objects.filter(status__in=CREATED, order_id__isnull=False)
               .select_related('run').order_by('run__created_at', 'row_number'))
    for result in results.iterator(chunk_size=500):
        pending.append(Sale(company_id=result.run.company_id, source_key=result.sale_key, order_id=result.order_id,
                            run_id=result.run_id))
        if len(pending) >= 500:
            Sale.objects.bulk_create(pending, ignore_conflicts=True)
            pending = []
    if pending:
        Sale.objects.bulk_create(pending, ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [('data_import', '0001_initial')]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
