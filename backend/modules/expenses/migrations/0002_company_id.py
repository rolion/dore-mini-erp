import django.db.models.functions.text
from django.db import migrations, models

# Empresa por defecto (UUID literal; ver `accounts/0002`): recibe las filas existentes antes del aislamiento.
DEFAULT_COMPANY_ID = '00000000-0000-4000-8000-000000000001'


def assign_default_company(apps, schema_editor):
    for name in ('ExpenseCategoryModel', 'ExpenseModel'):
        model = apps.get_model('expenses', name)
        model.objects.filter(company_id__isnull=True).update(company_id=DEFAULT_COMPANY_ID)


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='expensecategorymodel',
            name='company_id',
            field=models.UUIDField(db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='expensemodel',
            name='company_id',
            field=models.UUIDField(db_index=True, null=True),
        ),
        migrations.RunPython(assign_default_company, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='expensecategorymodel',
            name='company_id',
            field=models.UUIDField(db_index=True),
        ),
        migrations.AlterField(
            model_name='expensemodel',
            name='company_id',
            field=models.UUIDField(db_index=True),
        ),
        # La unicidad del nombre de categoría pasa de global a por empresa.
        migrations.RemoveConstraint(
            model_name='expensecategorymodel',
            name='expenses_category_name_ci_unique',
        ),
        migrations.AddConstraint(
            model_name='expensecategorymodel',
            constraint=models.UniqueConstraint(
                models.F('company_id'), django.db.models.functions.text.Lower('name'),
                name='expenses_category_company_name_ci_unique'),
        ),
    ]
