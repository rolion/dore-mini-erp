"""Sección de configuración por defecto de Compras: clasificación de pagos a proveedores."""
from uuid import UUID

from shared import company_defaults

from .django.models import SettingsModel

ORDER = 50


def export_settings(company_id: UUID, ctx: dict) -> dict:
    row = SettingsModel.objects.filter(company_id=company_id).first()
    pair = ctx.get('classification_names', {}).get(row.payment_classification_id) if row else None
    return {'payment_classification': dict(zip(('name', 'direction'), pair)) if pair else None}


def apply_settings(company_id: UUID, data: dict, ctx: dict) -> dict[str, int]:
    wanted = data.get('payment_classification')
    if not wanted:
        return {'created': 0, 'existing': 0}
    classification_id = ctx.get('classification_ids', {}).get((wanted['name'].lower(), wanted['direction']))
    if classification_id is None:
        raise company_defaults.DefaultsError(f'Clasificación «{wanted["name"]}» inexistente.')
    row, created = SettingsModel.objects.get_or_create(
        company_id=company_id, defaults={'payment_classification_id': classification_id})
    if not created and row.payment_classification_id is None:  # solo completa un ajuste vacío
        row.payment_classification_id = classification_id
        row.save(update_fields=['payment_classification_id', 'updated_at'])
        return {'created': 1, 'existing': 0}
    return {'created': int(created), 'existing': int(not created)}


def register() -> None:
    company_defaults.register('purchases', order=ORDER, export=export_settings, apply=apply_settings)
