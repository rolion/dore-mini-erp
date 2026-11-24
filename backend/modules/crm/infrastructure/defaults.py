"""Sección de configuración por defecto de CRM: el tablero «Ventas», sin etapas."""
from uuid import UUID

from shared import company_defaults

from .django.models import BoardModel

ORDER = 80
DEFAULT_BOARD_NAME = 'Ventas'


def export_boards(company_id: UUID, ctx: dict) -> dict:
    return {'boards': [{'name': b.name} for b in BoardModel.objects.filter(company_id=company_id, is_active=True)
                       .order_by('created_at', 'id')]}


def apply_boards(company_id: UUID, data: dict, ctx: dict) -> dict[str, int]:
    created = existing = 0
    for item in data.get('boards', []):
        exists = BoardModel.objects.filter(company_id=company_id, is_active=True, name__iexact=item['name']).exists()
        if not exists:
            BoardModel.objects.create(company_id=company_id, name=item['name'])
        created, existing = created + (not exists), existing + exists
    return {'created': created, 'existing': existing}


def register() -> None:
    company_defaults.register('crm', order=ORDER, export=export_boards, apply=apply_boards)
