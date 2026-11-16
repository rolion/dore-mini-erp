from uuid import UUID

from .models import SettingsModel


class DjangoPurchaseSettingsRepository:
    """Ajustes de Compras acotados a una empresa."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def payment_classification_id(self) -> UUID | None:
        row = SettingsModel.objects.filter(company_id=self.company_id).first()
        return row.payment_classification_id if row else None

    def set_payment_classification(self, classification_id: UUID | None) -> None:
        SettingsModel.objects.update_or_create(
            company_id=self.company_id, defaults={'payment_classification_id': classification_id})
