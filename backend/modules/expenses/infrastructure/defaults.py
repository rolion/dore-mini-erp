"""Sección de configuración por defecto de Gastos: categorías (`shared.company_defaults`)."""
from uuid import UUID

from shared import company_defaults

from .django.models import ExpenseCategoryModel

ORDER = 30


def export_categories(company_id: UUID, ctx: dict) -> dict:
    rows = list(ExpenseCategoryModel.objects.filter(company_id=company_id).order_by('name'))
    ctx['category_names'] = {c.id: c.name for c in rows}
    names = ctx.get('classification_names', {})
    return {'categories': [
        {'name': c.name, 'active': c.active, 'classification': (
            dict(zip(('name', 'direction'), names[c.classification_id])) if c.classification_id in names else None)}
        for c in rows]}


def apply_categories(company_id: UUID, data: dict, ctx: dict) -> dict[str, int]:
    created = existing = 0
    classification_ids = ctx.get('classification_ids', {})
    for item in data.get('categories', []):
        classification = item.get('classification')
        classification_id = None
        if classification:
            classification_id = classification_ids.get((classification['name'].lower(), classification['direction']))
            if classification_id is None:
                raise company_defaults.DefaultsError(f'Clasificación «{classification["name"]}» inexistente.')
        _, was_created = ExpenseCategoryModel.objects.get_or_create(
            company_id=company_id, name__iexact=item['name'],
            defaults={'name': item['name'], 'active': item.get('active', True), 'classification_id': classification_id})
        created, existing = created + was_created, existing + (not was_created)
    ctx['category_ids'] = {c.name.lower(): c.id for c in ExpenseCategoryModel.objects.filter(company_id=company_id)}
    return {'created': created, 'existing': existing}


def register() -> None:
    company_defaults.register('expenses', order=ORDER, export=export_categories, apply=apply_categories)
