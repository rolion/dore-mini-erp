from django.db import transaction
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.modularity.application.use_cases import DisableModule, EnableModule, ListModules
from modules.modularity.domain.modules import BaseModuleError, DependencyError, UnknownModule
from modules.modularity.infrastructure.django.repositories import (
    DjangoCompanyModuleRepository,
    DjangoSettingChangeRepository,
)
from shared.tenancy import company_id_from

from .serializers import serialize_module
from .settings_views import actor_from

MODULE_NOT_FOUND = 'Módulo no encontrado.'
BASE_MODULE = 'Los módulos base no se pueden deshabilitar.'
MISSING = 'Faltan módulos por habilitar: {}.'
DEPENDENTS = 'No se puede deshabilitar: lo requieren {}.'


class DependencyConflict(APIException):
    status_code = 409
    default_detail = 'Conflicto de dependencias.'

    def __init__(self, detail: str, extra: dict):
        super().__init__(detail)
        self.extra = extra


def _repository(request) -> DjangoCompanyModuleRepository:
    return DjangoCompanyModuleRepository(company_id_from(request))


def _run(use_case, *args):
    try:
        with transaction.atomic():
            return use_case.execute(*args)
    except UnknownModule as exc:
        raise NotFound(MODULE_NOT_FOUND) from exc
    except BaseModuleError as exc:
        raise ValidationError({'detail': BASE_MODULE}) from exc
    except DependencyError as exc:
        template, field = (MISSING, 'missing') if exc.kind == 'missing' else (DEPENDENTS, 'dependents')
        raise DependencyConflict(template.format(', '.join(exc.names)), {field: exc.names}) from exc


class _ConflictAwareView(APIView):
    def handle_exception(self, exc):
        if isinstance(exc, DependencyConflict):
            return Response({'detail': str(exc.detail), **exc.extra}, status=409)
        return super().handle_exception(exc)


class ModuleListView(_ConflictAwareView):
    def get(self, request):
        return Response([serialize_module(v) for v in ListModules(_repository(request)).execute()])


class _ModuleActionView(_ConflictAwareView):
    use_case = None

    def post(self, request, key: str):
        company_id = company_id_from(request)
        use_case = self.use_case(DjangoCompanyModuleRepository(company_id), DjangoSettingChangeRepository(company_id))
        views = _run(use_case, key, actor_from(request))
        return Response(serialize_module(next(v for v in views if v.definition.key == key)))


class ModuleEnableView(_ModuleActionView):
    use_case = EnableModule


class ModuleDisableView(_ModuleActionView):
    use_case = DisableModule
