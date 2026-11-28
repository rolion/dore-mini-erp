"""Autovínculo de la bandeja: al llegar un mensaje entrante, vincula el contacto por teléfono si es único (INV-07)."""
import logging
from uuid import UUID

from modules.crm.infrastructure.adapters import subscribe_inbound

logger = logging.getLogger(__name__)
_registered = False


def link_inbound(company_id: UUID, conversation_id: UUID) -> None:
    from modules.crm.api.inbox_views import inbox_service

    try:
        inbox_service(company_id).auto_link(conversation_id)
    except Exception:  # no debe afectar al mensaje ya guardado ni a otros suscriptores
        logger.exception('No se pudo autovincular la conversación %s', conversation_id)


def register() -> None:
    """Se llama al arrancar la app: así queda activo también en el proceso del worker (ADR)."""
    global _registered
    if not _registered:
        subscribe_inbound(link_inbound)
        _registered = True
