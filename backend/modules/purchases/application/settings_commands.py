from uuid import UUID

from modules.purchases.domain.repositories import PurchaseSettingsRepository

from .ports import ClassificationGateway, ClassificationInfo


class GetPaymentClassification:
    """Clasificación configurada para pagos a proveedores (con su nombre y estado actuales), o `None`."""

    def __init__(self, settings: PurchaseSettingsRepository, classifications: ClassificationGateway):
        self.settings = settings
        self.classifications = classifications

    def execute(self) -> ClassificationInfo | None:
        classification_id = self.settings.payment_classification_id()
        if classification_id is None:
            return None
        return self.classifications.describe([classification_id]).get(classification_id)


class SetPaymentClassification:
    """Configura (o quita con `None`) la clasificación de egreso de los pagos a proveedores.

    Solo afecta a los pagos nuevos: los registrados conservan la clasificación con que se crearon. No crea gastos.
    """

    def __init__(self, settings: PurchaseSettingsRepository, classifications: ClassificationGateway):
        self.settings = settings
        self.classifications = classifications

    def execute(self, classification_id: UUID | None = None) -> ClassificationInfo | None:
        info = None
        if classification_id is not None:
            info = self.classifications.validate_expense_classification(classification_id)
        self.settings.set_payment_classification(classification_id)
        return info
