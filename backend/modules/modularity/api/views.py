from django.db import transaction
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.modularity.application.use_cases import DisableModule, EnableModule, ListModules
from modules.modularity.domain.modules import (
    BaseModuleError,
    DependencyError,
    DisableBlocked,
    UnknownModule,
)
from modules.modularity.infrastructure.django.gate import SharedModuleExtensions
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
MISSING_CAPABILITIES = 'Falta la capacidad: {}.'


class DependencyConflict(APIException):
    status_code = 409
    default_detail = 'Conflicto de dependencias.'

    def __init__(self, detail: str, extra: dict):
        super().__init__(detail)
        self.extra = extra


def _repository(request) -> DjangoCompanyModuleRepository:
    return DjangoCompanyModuleRepository(company_id_from(request))


def _blocked_conflict(exc: DisableBlocked) -> DependencyConflict:
    extra: dict = {}
    pieces = []
    if exc.names:
        extra['dependents'] = exc.names
        pieces.append(f"lo requieren {', '.join(exc.names)}.")
    if exc.blockers:
        extra['blockers'] = [{'code': b.code, 'message': b.message, 'resolution': b.resolution}
                             for b in exc.blockers]
        pieces += [f'{b.message}. {b.resolution}' for b in exc.blockers]
    detail = 'No se puede deshabilitar: ' + ' '.join(pieces)
    return DependencyConflict(detail, extra)


def _run(use_case, *args):
    try:
        with transaction.atomic():
            return use_case.execute(*args)
    except UnknownModule as exc:
        raise NotFound(MODULE_NOT_FOUND) from exc
    except BaseModuleError as exc:
        raise ValidationError({'detail': BASE_MODULE}) from exc
    except DisableBlocked as exc:
        raise _blocked_conflict(exc) from exc
    except DependencyError as exc:
        if exc.kind == 'capabilities':
            raise DependencyConflict(MISSING_CAPABILITIES.format(', '.join(exc.names)),
                                     {'missing_capabilities': exc.names}) from exc
        raise DependencyConflict(MISSING.format(', '.join(exc.names)), {'missing': exc.names}) from exc


class _ConflictAwareView(APIView):
    required_modules = ()  # configurar los módulos no depende de ningún módulo (solo del admin de la empresa)

    def handle_exception(self, exc):
        if isinstance(exc, DependencyConflict):
            return Response({'detail': str(exc.detail), **exc.extra}, status=409)
        return super().handle_exception(exc)


class ModuleListView(_ConflictAwareView):
    def get(self, request):
        use_case = ListModules(_repository(request), SharedModuleExtensions(company_id_from(request)))
        return Response([serialize_module(v) for v in use_case.execute()])


class _ModuleActionView(_ConflictAwareView):
    use_case = None

    def post(self, request, key: str):
        company_id = company_id_from(request)
        use_case = self.use_case(DjangoCompanyModuleRepository(company_id), DjangoSettingChangeRepository(company_id),
                                 SharedModuleExtensions(company_id))
        views = _run(use_case, key, actor_from(request))
        return Response(serialize_module(next(v for v in views if v.definition.key == key)))


class ModuleEnableView(_ModuleActionView):
    use_case = EnableModule


class ModuleDisableView(_ModuleActionView):
    use_case = DisableModule
