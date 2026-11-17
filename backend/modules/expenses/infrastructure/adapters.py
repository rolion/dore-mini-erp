from collections.abc import Iterable
from datetime import date, datetime
from uuid import UUID

from django.utils import timezone

from modules.accounting import services as accounting
from modules.expenses.application.ports import ClassificationInfo, PostedAccounts
from modules.expenses.domain.exceptions import ExpensePostingError, ExpenseValidationError


EXPENSE_RECORD = 'EXPENSE_RECORD'  # evento del catálogo de Contabilidad (CONT-12)
EXPENSE_ROLE = 'EXPENSE_BY_CATEGORY'
PAYMENT_ROLE = 'MONEY'
VOID_REASON = 'Anulación de gasto'


class SystemClock:
    def now(self) -> datetime:
        return timezone.now()


class AccountingClassifications:
    """Clasificaciones y cobertura de Contabilidad, solo por su fachada `services`."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def validate_expense_classification(self, classification_id: UUID) -> ClassificationInfo:
        try:
            ref = accounting.validate_classification(self.company_id, classification_id, 'EXPENSE')
        except accounting.AccountValidationError as exc:
            raise ExpenseValidationError(exc.errors) from exc
        return ClassificationInfo(ref.classification_id, ref.name, ref.direction, True)

    def describe(self, classification_ids: Iterable[UUID]) -> dict[UUID, ClassificationInfo]:
        found = accounting.describe_classifications(self.company_id, classification_ids)
        return {k: ClassificationInfo(v.classification_id, v.name, v.direction, v.is_active) for k, v in found.items()}

    def is_covered(self, on: date) -> bool:
        return accounting.coverage_status(self.company_id, on).covered


def _posting_error(exc: Exception) -> ExpensePostingError:
    """Traduce los errores de la fachada de Contabilidad a uno propio, con código estable y mensaje accionable."""
    if isinstance(exc, accounting.PostingConfigurationMissing):
        issues = [{'code': i.code, 'role': i.role, 'subject': i.subject, 'message': i.message} for i in exc.issues]
        return ExpensePostingError('posting_configuration_missing', str(exc), issues)
    if isinstance(exc, accounting.FiscalPeriodClosed):
        return ExpensePostingError('fiscal_period_closed', str(exc))
    if isinstance(exc, accounting.DateOutsideFiscalPeriod):
        return ExpensePostingError('date_outside_fiscal_period', str(exc))
    return ExpensePostingError('posting_failed', str(exc))


_POSTING_ERRORS = (accounting.PostingConfigurationMissing, accounting.FiscalPeriodClosed,
                   accounting.DateOutsideFiscalPeriod, accounting.JournalValidationError, accounting.JournalConflict)


class AccountingPosting:
    """Asiento del gasto sobre la fachada de Contabilidad (`accounting.services`), dentro de la transacción del llamante."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def is_covered(self, on: date) -> bool:
        return accounting.coverage_status(self.company_id, on).covered

    def validate_accounts(self, expense_account_id: UUID | None, payment_account_id: UUID | None) -> None:
        errors: dict[str, list[str]] = {}
        for field, role, account_id in (('expense_account_id', EXPENSE_ROLE, expense_account_id),
                                        ('payment_account_id', PAYMENT_ROLE, payment_account_id)):
            if account_id is None:
                continue
            try:
                accounting.validate_posting_account(self.company_id, role, account_id)
            except accounting.AccountValidationError as exc:
                errors[field] = [m for messages in exc.errors.values() for m in messages]
        if errors:
            raise ExpenseValidationError(errors)

    def post(self, expense, category_name: str, expense_account_id: UUID | None,
             payment_account_id: UUID | None) -> PostedAccounts | None:
        overrides = {role: account for role, account in ((EXPENSE_ROLE, expense_account_id),
                                                          (PAYMENT_ROLE, payment_account_id)) if account}
        try:
            result = accounting.post_automatic_entry(
                self.company_id, EXPENSE_RECORD, expense.id, expense.expense_date,
                f'Gasto: {expense.description}', expense.amount, method=expense.payment_method.value,
                category_id=expense.category_id, category_label=category_name, account_overrides=overrides)
        except _POSTING_ERRORS as exc:
            raise _posting_error(exc) from exc
        if not result.posted:
            return None
        debit = next(line.account_id for line in result.entry.lines if line.debit > 0)
        credit = next(line.account_id for line in result.entry.lines if line.credit > 0)
        return PostedAccounts(debit, credit)

    def reverse(self, expense_id: UUID) -> None:
        try:
            accounting.reverse_automatic_entry(self.company_id, EXPENSE_RECORD, expense_id, timezone.localdate(),
                                               VOID_REASON)
        except _POSTING_ERRORS as exc:
            raise _posting_error(exc) from exc

    def entry_id(self, expense_id: UUID) -> UUID | None:
        """Asiento del gasto (o `None` si no se contabilizó)."""
        entry = accounting.find_automatic_entry(self.company_id, EXPENSE_RECORD, expense_id)
        return entry.id if entry else None


class AccountingAccounts:
    """Datos de cuentas contables para mostrar y para el formulario, por la fachada de Contabilidad."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def describe(self, account_ids: Iterable[UUID]) -> dict[UUID, accounting.AccountInfo]:
        return accounting.describe_accounts(self.company_id, account_ids)

    def options(self, expense_date: date, method: str | None, category_id: UUID | None, category_name: str):
        return accounting.posting_options(self.company_id, EXPENSE_RECORD, expense_date, method=method,
                                          category_id=category_id, category_label=category_name)
