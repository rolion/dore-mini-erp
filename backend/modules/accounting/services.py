"""Fachada pública de Contabilidad (convención de `docs/architecture/ddd.md`): DTO inmutables, nunca modelos."""
from dataclasses import dataclass
from uuid import UUID

from modules.accounting.application.use_cases import missing_methods
from modules.accounting.domain.catalog import METHOD_LABELS
from modules.accounting.infrastructure.django.repositories import DjangoAccountRepository, DjangoMethodMappingRepository


@dataclass(frozen=True)
class AccountRef:
    account_id: UUID
    name: str
    currency: str


def resolve_account(company_id: UUID, method: str) -> AccountRef | None:
    """Cuenta destino vigente del método para la empresa, o `None` si el método está inactivo o sin destino válido.

    La resuelve el servidor al cobrar; quien registre la entrada debe guardar esta cuenta en ella (no la recalcula).
    """
    mapping = DjangoMethodMappingRepository(company_id).get(method)
    if mapping is None or not mapping.is_active or mapping.account_id is None:
        return None
    account = DjangoAccountRepository(company_id).get(mapping.account_id)
    if account is None or not account.can_receive:
        return None
    return AccountRef(account.id, account.name, account.currency)


def missing_method_labels(company_id: UUID) -> list[str]:
    """Etiquetas de los métodos activos sin destino válido (precondición para habilitar Contabilidad)."""
    codes = missing_methods(DjangoAccountRepository(company_id), DjangoMethodMappingRepository(company_id))
    return [METHOD_LABELS[code] for code in codes]
