from uuid import UUID

from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.service_catalog.application.services import ServiceCatalog, UnavailableSpecialties
from modules.service_catalog.domain.service import ServiceNotFound, ServiceValidationError
from modules.service_catalog.infrastructure.django.repositories import DjangoServiceRepository
from shared.tenancy import company_id_from

from .serializers import ServiceInputSerializer, ServiceSerializer


class ServicePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        for field in ('page', 'page_size'):
            raw = request.query_params.get(field)
            if raw is not None and (len(raw) > 10 or not raw.isascii() or not raw.isdigit() or int(raw) < 1):
                raise ValidationError({field: ['Ingresa un entero mayor que cero.']})
        try:
            return super().paginate_queryset(queryset, request, view=view)
        except NotFound as exc:
            raise ValidationError({'page': ['La página solicitada ya no está disponible.']}) from exc


def _catalog(request):
    return ServiceCatalog(DjangoServiceRepository(company_id_from(request)), UnavailableSpecialties())


def _run(callback, **values):
    try:
        with transaction.atomic():
            service = callback(**values)
        return ServiceSerializer(service).data
    except ServiceNotFound as exc:
        raise NotFound('Servicio no encontrado.') from exc
    except ServiceValidationError as exc:
        raise ValidationError(exc.errors) from exc


class ServiceListCreateView(APIView):
    required_modules = ('services',)

    def get(self, request):
        active = request.query_params.get('active', '')
        if active not in ('', 'true', 'false'):
            raise ValidationError({'active': ['Usa true o false.']})
        specialty_id = request.query_params.get('specialty_id', '')
        if specialty_id and specialty_id != 'none':
            try:
                UUID(specialty_id)
            except ValueError as exc:
                raise ValidationError({'specialty_id': ['UUID inválido.']}) from exc
        services = _catalog(request).repository.list(
            search=request.query_params.get('search', '').strip(),
            active=None if not active else active == 'true', specialty_id=specialty_id)
        paginator = ServicePagination()
        page = paginator.paginate_queryset(services, request, view=self)
        return paginator.get_paginated_response(ServiceSerializer(page, many=True).data)

    def post(self, request):
        serializer = ServiceInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = {'name': '', 'base_price': None, 'duration_minutes': None, **serializer.validated_data}
        return Response(_run(_catalog(request).create, **values), status=201)


class ServiceDetailView(APIView):
    required_modules = ('services',)

    def get(self, request, service_id):
        return Response(_run(_catalog(request).get, service_id=service_id))

    def patch(self, request, service_id):
        serializer = ServiceInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(_run(_catalog(request).update, service_id=service_id, **serializer.validated_data))


class ServiceActivateView(APIView):
    required_modules = ('services',)
    active = True

    def post(self, request, service_id):
        return Response(_run(_catalog(request).set_active, service_id=service_id, active=self.active))


class ServiceDeactivateView(ServiceActivateView):
    active = False
