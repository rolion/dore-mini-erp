from uuid import UUID

from modules.customers.domain.customer import Customer
from modules.customers.domain.exceptions import CustomerNotFound, CustomerValidationError
from modules.customers.domain.repositories import CustomerRepository

from .exceptions import DuplicateCustomerPhone

UNSET = object()
MAX_DUPLICATE_MATCHES = 10


class CreateCustomer:
    def __init__(self, repository: CustomerRepository, default_country_code: str):
        self.repository = repository
        self.default_country_code = default_country_code

    def execute(self, name: object, phone: object = '', email: object = '', notes: object = '',
                confirm_duplicate: bool = False) -> Customer:
        customer = Customer.create(
            name=name, default_country_code=self.default_country_code, phone=phone, email=email, notes=notes,
        )
        if customer.phone and not confirm_duplicate:
            matches = self.repository.find_by_phone(customer.phone, limit=MAX_DUPLICATE_MATCHES)
            if matches:
                raise DuplicateCustomerPhone(matches)
        return self.repository.save(customer)


class UpdateCustomer:
    """Edición parcial de datos de contacto y notas; el estado (`active`) no se cambia por aquí."""

    def __init__(self, repository: CustomerRepository, default_country_code: str):
        self.repository = repository
        self.default_country_code = default_country_code

    def execute(self, customer_id: UUID, name: object = UNSET, phone: object = UNSET, email: object = UNSET,
                notes: object = UNSET) -> Customer:
        customer = self.repository.get(customer_id)
        if customer is None:
            raise CustomerNotFound(customer_id)
        errors: dict[str, list[str]] = {}
        changed = False

        def attempt(apply) -> bool:
            try:
                apply()
                return True
            except CustomerValidationError as exc:
                errors.update(exc.errors)
                return False

        if name is not UNSET:
            changed |= attempt(lambda: customer.rename(name))
        if phone is not UNSET or email is not UNSET:
            new_phone = customer.phone if phone is UNSET else phone
            new_email = customer.email if email is UNSET else email
            changed |= attempt(lambda: customer.change_contact(self.default_country_code, new_phone, new_email))
        if notes is not UNSET:
            changed |= attempt(lambda: customer.change_notes(notes))
        if errors:
            raise CustomerValidationError(errors)
        return self.repository.save(customer) if changed else customer


class ActivateCustomer:
    def __init__(self, repository: CustomerRepository):
        self.repository = repository

    def execute(self, customer_id: UUID) -> Customer:
        customer = self.repository.get(customer_id)
        if customer is None:
            raise CustomerNotFound(customer_id)
        customer.activate()
        return self.repository.save(customer)


class DeactivateCustomer:
    def __init__(self, repository: CustomerRepository):
        self.repository = repository

    def execute(self, customer_id: UUID) -> Customer:
        customer = self.repository.get(customer_id)
        if customer is None:
            raise CustomerNotFound(customer_id)
        customer.deactivate()
        return self.repository.save(customer)
