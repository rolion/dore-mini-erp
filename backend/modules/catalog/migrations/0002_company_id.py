from django.db import migrations, models

# Empresa por defecto (UUID literal; ver `accounts/0002`): recibe las filas existentes antes del aislamiento.
DEFAULT_COMPANY_ID = '00000000-0000-4000-8000-000000000001'


def assign_default_company(apps, schema_editor):
    ProductModel = apps.get_model('catalog', 'ProductModel')
    ProductModel.objects.filter(company_id__isnull=True).update(company_id=DEFAULT_COMPANY_ID)


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='productmodel',
            name='company_id',
            field=models.UUIDField(db_index=True, null=True),
        ),
        migrations.RunPython(assign_default_company, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='productmodel',
            name='company_id',
            field=models.UUIDField(db_index=True),
        ),
    ]
