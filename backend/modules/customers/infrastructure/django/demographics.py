from django.db import models


class CustomerDemographicsModel(models.Model):
    company_id = models.UUIDField(db_index=True)
    customer = models.OneToOneField('customers.CustomerModel', on_delete=models.PROTECT,
                                   related_name='demographics')
    birth_date = models.DateField(null=True, blank=True)
    responsible_name = models.CharField(max_length=150, blank=True, default='')
    responsible_phone = models.CharField(max_length=30, blank=True, default='')

    class Meta:
        db_table = 'customers_demographics'


class CustomerDemographicsHistoryModel(models.Model):
    company_id = models.UUIDField(db_index=True)
    customer = models.ForeignKey('customers.CustomerModel', on_delete=models.PROTECT)
    author_id = models.PositiveBigIntegerField()
    author_name = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    before = models.JSONField()
    after = models.JSONField()

    class Meta:
        db_table = 'customers_demographics_history'
        ordering = ['-created_at', '-id']
