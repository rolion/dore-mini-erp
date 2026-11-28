from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('messaging', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='conversationmodel',
            name='owner_id',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='conversationmodel',
            name='customer_id',
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='conversationmodel',
            name='lead_id',
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='conversationmodel',
            name='opportunity_id',
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name='conversationmodel',
            index=models.Index(fields=['company_id', 'owner_id'], name='messaging_conv_owner_idx'),
        ),
        migrations.AddIndex(
            model_name='conversationmodel',
            index=models.Index(fields=['company_id', 'opportunity_id'], name='messaging_conv_opp_idx'),
        ),
    ]
