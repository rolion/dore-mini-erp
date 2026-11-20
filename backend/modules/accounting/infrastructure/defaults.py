"""Secciones de configuración por defecto de Contabilidad (`shared.company_defaults`).

Dos secciones por el orden de dependencias: `accounting` (plan de cuentas, mapeos, clasificaciones, período fiscal) va
antes de Gastos; `accounting_posting` (cuentas por rol y por categoría de gasto) va después, porque referencia las
categorías por nombre a través de `ctx` (sin importar Gastos). Todo se identifica por claves naturales (código de
cuenta, nombre, dirección).
"""
from uuid import UUID

from django.utils import timezone

from shared import company_defaults

from .django.models import (
    AccountClassSettingModel,
    AccountModel,
    ClassificationModel,
    FiscalPeriodModel,
    MethodMappingModel,
    PostingAccountModel,
)

ACCOUNT_FIELDS = ('name', 'currency', 'kind', 'account_class', 'is_contra', 'is_active')
ORDER_ACCOUNTING = 20
ORDER_POSTING = 40


def _account_by_code(company_id: UUID, code: str, ctx: dict) -> AccountModel:
    account = ctx.get('accounts_by_code', {}).get(code.lower())
    if account is None:
        account = AccountModel.objects.filter(company_id=company_id, code__iexact=code).first()
    if account is None:
        raise company_defaults.DefaultsError(f'Cuenta con código «{code}» inexistente en la configuración.')
    return account


def export_accounting(company_id: UUID, ctx: dict) -> dict:
    accounts = AccountModel.objects.filter(company_id=company_id).order_by('code', 'name')
    code_by_id = {a.id: a.code for a in accounts}
    classifications = ClassificationModel.objects.filter(company_id=company_id).order_by('direction', 'name')
    ctx['classification_names'] = {c.id: (c.name, c.direction) for c in classifications}
    return {
        'accounts': [{'code': a.code, **{f: getattr(a, f) for f in ACCOUNT_FIELDS}} for a in accounts if a.code],
        'method_mappings': [
            {'method': m.method, 'account_code': code_by_id.get(m.account_id), 'is_active': m.is_active}
            for m in MethodMappingModel.objects.filter(company_id=company_id).order_by('method')
        ],
        'classifications': [
            {'name': c.name, 'direction': c.direction, 'is_active': c.is_active}
            for c in classifications
        ],
        'account_class_settings': [
            {'code': s.code, 'is_enabled': s.is_enabled}
            for s in AccountClassSettingModel.objects.filter(company_id=company_id).order_by('code')
        ],
    }


def _complete(account: AccountModel, item: dict) -> bool:
    """Reactiva la cuenta y completa sus datos vacíos desde el snapshot; devuelve si cambió algo."""
    changes: dict = {}
    if item.get('is_active', True) and not account.is_active:
        changes['is_active'] = True
    for field in ('code', 'kind', 'account_class', 'currency'):
        if not getattr(account, field) and item.get(field):
            changes[field] = item[field]
    for field, value in changes.items():
        setattr(account, field, value)
    if changes:
        account.save(update_fields=[*changes, 'updated_at'])
    return bool(changes)


def apply_accounting(company_id: UUID, data: dict, ctx: dict) -> dict[str, int]:
    created = existing = completed = 0
    resolved = ctx.setdefault('accounts_by_code', {})
    for item in data.get('accounts', []):
        # Existe si coincide el código o el nombre (el nombre es único por empresa). Una cuenta existente se reactiva
        # si el snapshot la define activa y se le completan solo los datos vacíos; lo ya cargado no se pisa.
        account = (AccountModel.objects.filter(company_id=company_id, code__iexact=item['code']).first()
                   or AccountModel.objects.filter(company_id=company_id, name__iexact=item['name']).first())
        was_created = account is None
        if was_created:
            account = AccountModel.objects.create(
                company_id=company_id, code=item['code'], opening_balance=0, **{f: item[f] for f in ACCOUNT_FIELDS})
        elif _complete(account, item):
            completed += 1
        resolved[item['code'].lower()] = account
        created, existing = created + was_created, existing + (not was_created)
    for item in data.get('method_mappings', []):
        account = _account_by_code(company_id, item['account_code'], ctx) if item.get('account_code') else None
        _, was_created = MethodMappingModel.objects.get_or_create(
            company_id=company_id, method=item['method'],
            defaults={'account': account, 'is_active': item.get('is_active', True)})
        created, existing = created + was_created, existing + (not was_created)
    for item in data.get('classifications', []):
        _, was_created = ClassificationModel.objects.get_or_create(
            company_id=company_id, name__iexact=item['name'], direction=item['direction'],
            defaults={'name': item['name'], 'is_active': item.get('is_active', True)})
        created, existing = created + was_created, existing + (not was_created)
    for item in data.get('account_class_settings', []):
        _, was_created = AccountClassSettingModel.objects.get_or_create(
            company_id=company_id, code=item['code'], defaults={'is_enabled': item['is_enabled']})
        created, existing = created + was_created, existing + (not was_created)
    ctx['classification_ids'] = {
        (c.name.lower(), c.direction): c.id for c in ClassificationModel.objects.filter(company_id=company_id)}
    if data and not FiscalPeriodModel.objects.filter(company_id=company_id).exists():
        today = timezone.localdate()
        FiscalPeriodModel.objects.create(
            company_id=company_id, name=str(today.year), start_date=today.replace(month=1, day=1),
            end_date=today.replace(month=12, day=31))
        created += 1
    return {'created': created, 'existing': existing, 'completed': completed}


def export_posting(company_id: UUID, ctx: dict) -> dict:
    names = ctx.get('category_names', {})
    rows = PostingAccountModel.objects.filter(company_id=company_id).select_related('account').order_by('scope', 'key')
    categories = [{'category_name': names[UUID(r.key)], 'account_code': r.account.code}
                  for r in rows if r.scope == 'CATEGORY' and UUID(r.key) in names]
    return {
        'roles': [{'key': r.key, 'account_code': r.account.code} for r in rows if r.scope == 'ROLE'],
        'categories': sorted(categories, key=lambda c: c['category_name']),
    }


def apply_posting(company_id: UUID, data: dict, ctx: dict) -> dict[str, int]:
    created = existing = 0
    entries = [('ROLE', item['key'], item['account_code']) for item in data.get('roles', [])]
    for item in data.get('categories', []):
        category_id = ctx.get('category_ids', {}).get(item['category_name'].lower())
        if category_id is None:
            raise company_defaults.DefaultsError(f'Categoría de gasto «{item["category_name"]}» inexistente.')
        entries.append(('CATEGORY', str(category_id), item['account_code']))
    for scope, key, code in entries:
        _, was_created = PostingAccountModel.objects.get_or_create(
            company_id=company_id, scope=scope, key=key, defaults={'account': _account_by_code(company_id, code, ctx)})
        created, existing = created + was_created, existing + (not was_created)
    return {'created': created, 'existing': existing}


def register() -> None:
    company_defaults.register('accounting', order=ORDER_ACCOUNTING, export=export_accounting, apply=apply_accounting)
    company_defaults.register('accounting_posting', order=ORDER_POSTING, export=export_posting, apply=apply_posting)
