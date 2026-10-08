from collections.abc import Sequence

from modules.customers.domain.customer import Customer


class DuplicateCustomerPhone(Exception):
    """Ya existe al menos un cliente con el mismo teléfono normalizado; el alta requiere confirmación."""

    def __init__(self, matches: Sequence[Customer]):
        super().__init__('Ya existe un cliente con este teléfono.')
        self.matches = list(matches)
