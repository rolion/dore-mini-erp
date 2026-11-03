import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='Schedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company_id', models.UUIDField()),
                ('professional_id', models.UUIDField()),
            ],
            options={'constraints': [models.UniqueConstraint(
                fields=('company_id', 'professional_id'), name='agenda_schedule_company_professional'
            )]},
        ),
        migrations.CreateModel(
            name='Shift',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day', models.PositiveSmallIntegerField()),
                ('starts', models.TimeField()),
                ('ends', models.TimeField()),
                ('valid_from', models.DateField()),
                ('valid_until', models.DateField()),
                ('breaks', models.JSONField(default=list)),
                ('schedule', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='agenda.schedule')),
            ],
        ),
        migrations.CreateModel(
            name='Absence',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('starts', models.DateTimeField()),
                ('ends', models.DateTimeField()),
                ('reason', models.CharField(max_length=250)),
                ('schedule', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='agenda.schedule')),
            ],
        ),
    ]
