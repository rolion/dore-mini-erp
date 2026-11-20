"""Cola de importación: estado QUEUED, progreso, motivo de fallo y una sola corrida activa (en cola o en curso)."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_import', '0002_backfill_imported_sales'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='importrunmodel',
            name='di_run_one_running_per_company',
        ),
        migrations.AddField(
            model_name='importrunmodel',
            name='processed_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='importrunmodel',
            name='total_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='importrunmodel',
            name='failure_code',
            field=models.CharField(blank=True, default='', max_length=60),
        ),
        migrations.AddField(
            model_name='importrunmodel',
            name='failure_message',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='importrunmodel',
            name='status',
            field=models.CharField(
                choices=[('UPLOADED', 'UPLOADED'), ('PREVIEWED', 'PREVIEWED'), ('QUEUED', 'QUEUED'),
                         ('RUNNING', 'RUNNING'), ('COMPLETED', 'COMPLETED'), ('FAILED', 'FAILED')],
                default='UPLOADED', max_length=12),
        ),
        migrations.AddConstraint(
            model_name='importrunmodel',
            constraint=models.UniqueConstraint(
                condition=models.Q(('status__in', ['QUEUED', 'RUNNING'])), fields=('company_id',),
                name='di_run_one_active_per_company'),
        ),
    ]
