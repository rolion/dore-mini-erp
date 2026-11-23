from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0003_payment_idempotency'),
    ]

    operations = [
        migrations.AddField(
            model_name='ordermodel',
            name='warehouse_id',
            field=models.UUIDField(blank=True, null=True),
        ),
    ]
