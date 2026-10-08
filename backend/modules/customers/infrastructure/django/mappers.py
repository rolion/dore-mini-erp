from modules.customers.domain.customer import Customer

from .models import CustomerModel


def to_entity(model: CustomerModel) -> Customer:
    return Customer(
        id=model.id,
        name=model.name,
        phone=model.phone,
        email=model.email,
        notes=model.notes,
        active=model.active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def to_model_values(customer: Customer) -> dict[str, object]:
    return {
        'name': customer.name,
        'phone': customer.phone,
        'email': customer.email,
        'notes': customer.notes,
        'active': customer.active,
    }
