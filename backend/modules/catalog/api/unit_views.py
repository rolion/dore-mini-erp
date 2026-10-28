from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.catalog.application.commands import CreateUnit, SetUnitActive, UpdateUnit
from modules.catalog.application.queries import GetUnit, ListUnits
from modules.catalog.domain.exceptions import UnitInUse, UnitNotFound, UnitValidationError
from modules.catalog.infrastructure.django.repositories import DjangoUnitRepository
from shared.tenancy import company_id_from

from .errors import Conflict
from .pagination import ProductPagination
from .serializers import UnitInputSerializer, UnitSerializer
from .views import _parse_active

UNIT_NOT_FOUND = 'Unidad no encontrada.'
# La pantalla de unidades vive en Inventario: la API exige ese módulo habilitado (clave, no import).
REQUIRED_MODULES = ('inventory',)


def _repository(request) -> DjangoUnitRepository:
    return DjangoUnitRepository(company_id_from(request))


def _run(use_case, **kwargs):
    try:
        return use_case.execute(**kwargs)
    except UnitValidationError as exc:
        raise ValidationError(exc.errors) from exc
    except UnitNotFound as exc:
        raise NotFound(UNIT_NOT_FOUND) from exc
    except UnitInUse as exc:
        raise Conflict(str(exc), 'unit_in_use') from exc


class UnitListCreateView(APIView):
    required_modules = REQUIRED_MODULES

    def get(self, request):
        active = _parse_active(request.query_params.get('active'))
        search = request.query_params.get('search', '').strip() or None
        units = ListUnits(_repository(request)).execute(search=search, active=active)
        paginator = ProductPagination()
        page = paginator.paginate_queryset(units, request, view=self)
        return paginator.get_paginated_response(UnitSerializer(page, many=True).data)

    def post(self, request):
        serializer = UnitInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        unit = _run(CreateUnit(_repository(request)), **serializer.validated_data)
        return Response(UnitSerializer(unit).data, status=status.HTTP_201_CREATED)


class UnitDetailView(APIView):
    required_modules = REQUIRED_MODULES

    def get(self, request, unit_id):
        return Response(UnitSerializer(_run(GetUnit(_repository(request)), unit_id=unit_id)).data)

    def patch(self, request, unit_id):
        serializer = UnitInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        unit = _run(UpdateUnit(_repository(request)), unit_id=unit_id, **serializer.validated_data)
        return Response(UnitSerializer(unit).data)


class UnitActivateView(APIView):
    required_modules = REQUIRED_MODULES

    def post(self, request, unit_id):
        return Response(UnitSerializer(_run(SetUnitActive(_repository(request), True), unit_id=unit_id)).data)


class UnitDeactivateView(APIView):
    required_modules = REQUIRED_MODULES

    def post(self, request, unit_id):
        return Response(UnitSerializer(_run(SetUnitActive(_repository(request), False), unit_id=unit_id)).data)
