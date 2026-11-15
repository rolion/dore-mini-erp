from collections.abc import Iterable
from datetime import date, datetime
from uuid import UUID

from django.utils import timezone

from modules.accounting import services as accounting
from modules.expenses.application.ports import ClassificationInfo
from modules.expenses.domain.exceptions import ExpenseValidationError


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
