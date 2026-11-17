from modules.expenses.domain.category import ExpenseCategory
from modules.expenses.domain.enums import ExpenseStatus, PaymentMethod
from modules.expenses.domain.expense import Expense

from .models import ExpenseCategoryModel, ExpenseModel


def category_to_entity(model: ExpenseCategoryModel) -> ExpenseCategory:
    return ExpenseCategory(id=model.id, name=model.name, active=model.active,
                           classification_id=model.classification_id, created_at=model.created_at,
                           updated_at=model.updated_at)


def category_to_values(category: ExpenseCategory) -> dict[str, object]:
    return {'name': category.name, 'active': category.active, 'classification_id': category.classification_id}


def expense_to_entity(model: ExpenseModel) -> Expense:
    return Expense(
        id=model.id,
        description=model.description,
        amount=model.amount,
        category_id=model.category_id,
        expense_date=model.expense_date,
        payment_method=PaymentMethod(model.payment_method),
        supplier_name=model.supplier_name,
        notes=model.notes,
        status=ExpenseStatus(model.status),
        voided_at=model.voided_at,
        classification_id=model.classification_id,
        expense_account_id=model.expense_account_id,
        payment_account_id=model.payment_account_id,
        idempotency_key=model.idempotency_key,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def expense_to_values(expense: Expense) -> dict[str, object]:
    return {
        'category_id': expense.category_id,
        'description': expense.description,
        'amount': expense.amount,
        'expense_date': expense.expense_date,
        'payment_method': expense.payment_method.value,
        'supplier_name': expense.supplier_name,
        'notes': expense.notes,
        'status': expense.status.value,
        'voided_at': expense.voided_at,
        'classification_id': expense.classification_id,
        'expense_account_id': expense.expense_account_id,
        'payment_account_id': expense.payment_account_id,
        'idempotency_key': expense.idempotency_key,
    }
