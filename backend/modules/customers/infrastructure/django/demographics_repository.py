from contextlib import contextmanager
from django.db import transaction

from modules.customers.domain.demographics import Demographics
from modules.customers.domain.exceptions import CustomerNotFound
from .demographics import CustomerDemographicsHistoryModel, CustomerDemographicsModel
from .models import CustomerModel


class DjangoDemographicsRepository:
    def __init__(self, company_id):
        self.company_id = company_id

    @contextmanager
    def locked(self, customer_id):
        # Lock the existing parent, including the first write where no demographics row exists yet.
        with transaction.atomic():
            customer = CustomerModel.objects.select_for_update().filter(
                company_id=self.company_id, id=customer_id).first()
            if customer is None:
                raise CustomerNotFound(customer_id)
            yield

    def save(self, customer_id, current, previous, author_id, author_name):
        CustomerDemographicsModel.objects.update_or_create(
            company_id=self.company_id, customer_id=customer_id,
            defaults={'birth_date': current.birth_date, 'responsible_name': current.responsible_name,
                      'responsible_phone': current.responsible_phone})
        CustomerDemographicsHistoryModel.objects.create(
            company_id=self.company_id, customer_id=customer_id, author_id=author_id,
            author_name=author_name, before=previous.snapshot(), after=current.snapshot())

    def get(self, customer_id):
        if not CustomerModel.objects.filter(company_id=self.company_id, id=customer_id).exists():
            raise CustomerNotFound(customer_id)
        row = CustomerDemographicsModel.objects.filter(company_id=self.company_id, customer_id=customer_id).first()
        return Demographics(row.birth_date, row.responsible_name, row.responsible_phone) if row else Demographics()

    def history(self, customer_id):
        self.get(customer_id)
        return CustomerDemographicsHistoryModel.objects.filter(company_id=self.company_id, customer_id=customer_id)
