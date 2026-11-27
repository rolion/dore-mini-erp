"""Sección de configuración por defecto de Modularidad: módulos habilitados y ajustes por módulo.

Va al final: habilitar un módulo dispara su gancho de ciclo de vida (p. ej. Contabilidad abre su tramo de cobertura y su
fecha de corte = hoy) cuando ya existe el resto de la configuración.
"""
from uuid import UUID

from modules.modularity.domain.company_types import template_modules
from modules.modularity.domain.modules import BASE_KEYS, BY_KEY
from modules.modularity.domain.settings import BY_SETTING_KEY, validate
from shared import company_defaults, module_lifecycle

from .django.models import CompanyModuleModel, CompanySettingModel, CompanySettingsModel

ORDER = 70


def export_modularity(company_id: UUID, ctx: dict) -> dict:
    modules = CompanyModuleModel.objects.filter(company_id=company_id).order_by('module_key')
    settings = CompanySettingModel.objects.filter(company_id=company_id).order_by('setting_key')
    return {'modules': [m.module_key for m in modules], 'settings': {s.setting_key: s.value for s in settings}}


def apply_modularity(company_id: UUID, data: dict, ctx: dict) -> dict[str, int]:
    created = existing = 0
    # Marca la empresa como inicializada para que la siembra perezosa no vuelva a añadir los módulos por defecto.
    CompanySettingsModel.objects.get_or_create(company_id=company_id)
    # Con perfil (tipo de empresa) los módulos salen de su plantilla; sin perfil, del snapshot.
    modules = template_modules(ctx.get('profile') or '')
    for key in (data.get('modules', []) if modules is None else modules):
        if key in BASE_KEYS:
            continue
        if key not in BY_KEY:
            raise company_defaults.DefaultsError(f'Módulo desconocido «{key}».')
        _, was_created = CompanyModuleModel.objects.get_or_create(company_id=company_id, module_key=key)
        if was_created:
            module_lifecycle.enabled(company_id, key)
        created, existing = created + was_created, existing + (not was_created)
    for key, raw in data.get('settings', {}).items():
        if key not in BY_SETTING_KEY:
            raise company_defaults.DefaultsError(f'Ajuste desconocido «{key}».')
        try:
            value = validate(BY_SETTING_KEY[key], raw)
        except ValueError as exc:
            raise company_defaults.DefaultsError(f'Ajuste «{key}»: {exc}') from None
        _, was_created = CompanySettingModel.objects.get_or_create(
            company_id=company_id, setting_key=key, defaults={'value': value})
        created, existing = created + was_created, existing + (not was_created)
    return {'created': created, 'existing': existing}


def register() -> None:
    company_defaults.register('modularity', order=ORDER, export=export_modularity, apply=apply_modularity)
