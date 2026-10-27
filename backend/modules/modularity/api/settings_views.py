from datetime import date

from django.db import transaction
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.modularity.application.settings_use_cases import (
    Actor,
    GetModuleSettings,
    ListSettingChanges,
    UpdateModuleSettings,
)
from modules.modularity.domain.modules import UnknownModule
from modules.modularity.domain.settings import ModuleDisabled, SettingsValidationError
from modules.modularity.infrastructure.django.repositories import (
    DjangoCompanyModuleRepository,
    DjangoCompanySettingRepository,
    DjangoSettingChangeRepository,
)
from shared.tenancy import company_id_from

from .serializers import serialize_change, serialize_settings

MODULE_NOT_FOUND = 'Módulo no encontrado.'
MODULE_DISABLED = 'El módulo no está habilitado para tu empresa.'
BAD_SETTINGS = 'Envía los ajustes como un objeto: {"settings": {"clave": valor}}.'


class ModuleDisabledConflict(APIException):
    status_code = 409
    default_detail = MODULE_DISABLED


def actor_from(request) -> Actor:
    user = request.user
    return Actor(user.pk, user.get_full_name().strip() or user.get_username())


def _date_param(request, name: str) -> date | None:
    raw = request.query_params.get(name)
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ValidationError({name: ['Use el formato AAAA-MM-DD.']}) from None


class ModuleSettingsView(APIView):
    def get(self, request, module: str):
        company_id = company_id_from(request)
        try:
            values = GetModuleSettings(DjangoCompanySettingRepository(company_id)).execute(module)
        except UnknownModule as exc:
            raise NotFound(MODULE_NOT_FOUND) from exc
        return Response(serialize_settings(module, values))

    def patch(self, request, module: str):
        raw = request.data.get('settings') if hasattr(request.data, 'get') else None
        if not isinstance(raw, dict) or not raw:
            raise ValidationError({'settings': [BAD_SETTINGS]})
        company_id = company_id_from(request)
        use_case = UpdateModuleSettings(
            DjangoCompanySettingRepository(company_id), DjangoSettingChangeRepository(company_id),
            DjangoCompanyModuleRepository(company_id))
        try:
            with transaction.atomic():
                values = use_case.execute(module, raw, actor_from(request))
        except UnknownModule as exc:
            raise NotFound(MODULE_NOT_FOUND) from exc
        except ModuleDisabled as exc:
            raise ModuleDisabledConflict() from exc
        except SettingsValidationError as exc:
            raise ValidationError({'settings': exc.errors}) from exc
        return Response(serialize_settings(module, values))


class SettingChangeListView(APIView):
    def get(self, request, scope: str):
        date_from, date_to = _date_param(request, 'date_from'), _date_param(request, 'date_to')
        if date_from and date_to and date_from > date_to:
            raise ValidationError({'date_from': ['La fecha inicial no puede ser posterior a la final.']})
        try:
            page = max(int(request.query_params.get('page', 1)), 1)
        except ValueError:
            page = 1
        try:
            result = ListSettingChanges(DjangoSettingChangeRepository(company_id_from(request))).execute(
                scope, date_from=date_from, date_to=date_to,
                setting_key=request.query_params.get('setting') or None, page=page)
        except UnknownModule as exc:
            raise NotFound(MODULE_NOT_FOUND) from exc
        return Response({
            'count': result.count,
            'results': [serialize_change(row) for row in result.rows],
            'settings': [{'key': key, 'label': label} for key, label in result.settings],
        })
