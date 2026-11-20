"""Sección de configuración por defecto de Inventario: almacenes."""
from uuid import UUID

from shared import company_defaults

from .django.models import WarehouseModel

ORDER = 60
FIELDS = ('description', 'active')


def export_warehouses(company_id: UUID, ctx: dict) -> dict:
    return {'warehouses': [
        {'name': w.name, 'is_default': w.is_default, **{f: getattr(w, f) for f in FIELDS}}
        for w in WarehouseModel.objects.filter(company_id=company_id).order_by('name')]}


def apply_warehouses(company_id: UUID, data: dict, ctx: dict) -> dict[str, int]:
    created = existing = 0
    has_default = WarehouseModel.objects.filter(company_id=company_id, is_default=True).exists()
    for item in data.get('warehouses', []):
        make_default = bool(item.get('is_default')) and not has_default
        _, was_created = WarehouseModel.objects.get_or_create(
            company_id=company_id, name__iexact=item['name'],
            defaults={'name': item['name'], 'is_default': make_default, **{f: item[f] for f in FIELDS}})
        has_default = has_default or (was_created and make_default)
        created, existing = created + was_created, existing + (not was_created)
    return {'created': created, 'existing': existing}


def register() -> None:
    company_defaults.register('inventory', order=ORDER, export=export_warehouses, apply=apply_warehouses)
