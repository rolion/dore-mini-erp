from typing import Sequence
from uuid import UUID

from modules.customers.domain.customer import Customer
from modules.customers.domain.exceptions import CustomerNotFound
from modules.customers.domain.repositories import CustomerRepository


class GetCustomer:
    def __init__(self, repository: CustomerRepository):
        self.repository = repository

    def execute(self, customer_id: UUID) -> Customer:
        customer = self.repository.get(customer_id)
        if customer is None:
            raise CustomerNotFound(customer_id)
        return customer


class ListCustomers:
    def __init__(self, repository: CustomerRepository):
        self.repository = repository

    def execute(self, search: str | None = None, active: bool | None = None) -> Sequence[Customer]:
        return self.repository.list(search=search, active=active)
