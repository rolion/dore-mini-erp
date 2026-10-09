from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from .enums import ExpenseStatus, PaymentMethod
from .exceptions import ExpenseRuleViolation, ExpenseValidationError
from .validation import fail, optional_text, positive_money, required_date, required_text, required_uuid, run_checks

DESCRIPTION_MAX_LENGTH = 200
SUPPLIER_MAX_LENGTH = 150
NOTES_MAX_LENGTH = 2000

# Marca "no enviado" para ediciones parciales (distinta de `None`, que es un valor inválido o vacío).
UNSET = object()


def _payment_method(value: object) -> PaymentMethod:
    """Omitido o vacío equivale a efectivo; un código desconocido se rechaza."""
    if value is None or value == '':
        return PaymentMethod.CASH
    try:
        return PaymentMethod(value)
    except ValueError:
        raise fail('payment_method', 'El método de pago no es válido.') from None


def _validate(description: object, amount: object, category_id: object, expense_date: object, payment_method: object,
              supplier_name: object, notes: object) -> dict[str, object]:
    """Valida juntos los datos del gasto y devuelve los valores normalizados (errores de todos los campos)."""
    values, errors = run_checks([
        ('description', lambda: required_text(description, 'description', 'La descripción', DESCRIPTION_MAX_LENGTH)),
        ('amount', lambda: positive_money(amount, 'amount', 'El monto')),
        ('category_id', lambda: required_uuid(category_id, 'category_id', 'La categoría')),
        ('expense_date', lambda: required_date(expense_date, 'expense_date', 'La fecha')),
        ('payment_method', lambda: _payment_method(payment_method)),
        ('supplier_name', lambda: optional_text(supplier_name, 'supplier_name', 'El proveedor', SUPPLIER_MAX_LENGTH)),
        ('notes', lambda: optional_text(notes, 'notes', 'Las notas', NOTES_MAX_LENGTH)),
    ])
    if errors:
        raise ExpenseValidationError(errors)
    return values


@dataclass
class Expense:
    id: UUID
    description: str
    amount: Decimal
    category_id: UUID
    expense_date: date
    payment_method: PaymentMethod = PaymentMethod.CASH
    supplier_name: str = ''
    notes: str = ''
    status: ExpenseStatus = ExpenseStatus.ACTIVE
    voided_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(cls, description: object, amount: object, category_id: object, expense_date: object,
               payment_method: object = None, supplier_name: object = '', notes: object = '') -> 'Expense':
        values = _validate(description, amount, category_id, expense_date, payment_method, supplier_name, notes)
        return cls(id=uuid4(), **values)

    @property
    def voided(self) -> bool:
        return self.status is ExpenseStatus.VOIDED

    def ensure_editable(self) -> None:
        if self.voided:
            raise ExpenseRuleViolation('expense_voided', 'El gasto está anulado y no se puede editar.')

    def update(self, description: object = UNSET, amount: object = UNSET, category_id: object = UNSET,
               expense_date: object = UNSET, payment_method: object = UNSET, supplier_name: object = UNSET,
               notes: object = UNSET) -> None:
        """Edición parcial con las mismas validaciones que la creación; los campos no enviados se conservan."""
        self.ensure_editable()

        def pick(new: object, current: object) -> object:
            return current if new is UNSET else new

        values = _validate(
            pick(description, self.description), pick(amount, self.amount), pick(category_id, self.category_id),
            pick(expense_date, self.expense_date), pick(payment_method, self.payment_method),
            pick(supplier_name, self.supplier_name), pick(notes, self.notes),
        )
        for name, value in values.items():
            setattr(self, name, value)

    def void(self, now: datetime) -> None:
        """Anula el gasto: deja de sumar en los reportes. Es irreversible."""
        if self.voided:
            raise ExpenseRuleViolation('already_voided', 'El gasto ya está anulado.')
        self.status = ExpenseStatus.VOIDED
        self.voided_at = now
