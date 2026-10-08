import re
from collections.abc import Sequence
from uuid import UUID

from django.db.models import Q, QuerySet

from modules.customers.domain.customer import Customer

from .mappers import to_entity, to_model_values
from .models import CustomerModel


class CustomerList:
    """Vista perezosa de entidades sobre un queryset: permite paginar sin cargar todos los clientes."""

    def __init__(self, queryset: QuerySet):
        self._queryset = queryset

    def count(self) -> int:
        return self._queryset.count()

    def __len__(self) -> int:
        return self.count()

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [to_entity(model) for model in self._queryset[index]]
        return to_entity(self._queryset[index])

    def __iter__(self):
        return (to_entity(model) for model in self._queryset)


class DjangoCustomerRepository:
    def get(self, customer_id: UUID) -> Customer | None:
        model = CustomerModel.objects.filter(pk=customer_id).first()
        return to_entity(model) if model else None

    def save(self, customer: Customer) -> Customer:
        model, _ = CustomerModel.objects.update_or_create(id=customer.id, defaults=to_model_values(customer))
        return to_entity(model)

    def list(self, search: str | None = None, active: bool | None = None) -> CustomerList:
        queryset = CustomerModel.objects.order_by('name', 'id')
        if search:
            condition = Q(name__icontains=search)
            digits = re.sub(r'\D', '', search)
            if digits:
                condition |= Q(phone__contains=digits)
            queryset = queryset.filter(condition)
        if active is not None:
            queryset = queryset.filter(active=active)
        return CustomerList(queryset)

    def find_by_phone(self, phone: str, exclude_id: UUID | None = None, limit: int = 10) -> Sequence[Customer]:
        queryset = CustomerModel.objects.filter(phone=phone).order_by('name', 'id')
        if exclude_id is not None:
            queryset = queryset.exclude(pk=exclude_id)
        return [to_entity(model) for model in queryset[:limit]]
