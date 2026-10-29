from uuid import UUID

from modules.purchases.domain.exceptions import SupplierNotFound, SupplierValidationError
from modules.purchases.domain.repositories import SupplierRepository
from modules.purchases.domain.supplier import Supplier

UNSET = object()


class CreateSupplier:
    def __init__(self, repository: SupplierRepository):
        self.repository = repository

    def execute(self, name: object, tax_id: object = '', phone: object = '', email: object = '',
                notes: object = '') -> Supplier:
        supplier = Supplier.create(name=name, tax_id=tax_id, phone=phone, email=email, notes=notes)
        return self.repository.save(supplier)


class UpdateSupplier:
    """Edición parcial de datos; el estado (`active`) no se cambia por aquí."""

    def __init__(self, repository: SupplierRepository):
        self.repository = repository

    def execute(self, supplier_id: UUID, name: object = UNSET, tax_id: object = UNSET, phone: object = UNSET,
                email: object = UNSET, notes: object = UNSET) -> Supplier:
        supplier = self.repository.get(supplier_id)
        if supplier is None:
            raise SupplierNotFound(supplier_id)
        errors: dict[str, list[str]] = {}
        changed = False

        def attempt(apply) -> bool:
            try:
                apply()
                return True
            except SupplierValidationError as exc:
                errors.update(exc.errors)
                return False

        if name is not UNSET:
            changed |= attempt(lambda: supplier.rename(name))
        if tax_id is not UNSET:
            changed |= attempt(lambda: supplier.change_tax_id(tax_id))
        if phone is not UNSET or email is not UNSET:
            new_phone = supplier.phone if phone is UNSET else phone
            new_email = supplier.email if email is UNSET else email
            changed |= attempt(lambda: supplier.change_contact(new_phone, new_email))
        if notes is not UNSET:
            changed |= attempt(lambda: supplier.change_notes(notes))
        if errors:
            raise SupplierValidationError(errors)
        return self.repository.save(supplier) if changed else supplier


class ActivateSupplier:
    def __init__(self, repository: SupplierRepository):
        self.repository = repository

    def execute(self, supplier_id: UUID) -> Supplier:
        supplier = self.repository.get(supplier_id)
        if supplier is None:
            raise SupplierNotFound(supplier_id)
        supplier.activate()
        return self.repository.save(supplier)


class DeactivateSupplier:
    def __init__(self, repository: SupplierRepository):
        self.repository = repository

    def execute(self, supplier_id: UUID) -> Supplier:
        supplier = self.repository.get(supplier_id)
        if supplier is None:
            raise SupplierNotFound(supplier_id)
        supplier.deactivate()
        return self.repository.save(supplier)
