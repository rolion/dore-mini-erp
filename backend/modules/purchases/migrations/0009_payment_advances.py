from django.db import migrations, models
from django.db.models import F


def paid_debt_for_existing_payments(apps, schema_editor):
    """Los pagos anteriores cuentan como deuda pagada (sin anticipo): `debt_amount = amount`."""
    apps.get_model('purchases', 'PaymentModel').objects.update(debt_amount=F('amount'))


class Migration(migrations.Migration):

    dependencies = [
        ('purchases', '0008_payment_classification'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentmodel',
            name='debt_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='paymentmodel',
            name='advance_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='receiptmodel',
            name='advance_applied',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.RunPython(paid_debt_for_existing_payments, migrations.RunPython.noop),
    ]
