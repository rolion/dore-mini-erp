from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.customers.application.commands import (
    ActivateCustomer,
    CreateCustomer,
    DeactivateCustomer,
    UpdateCustomer,
)
from modules.customers.application.exceptions import DuplicateCustomerPhone
from modules.customers.application.queries import GetCustomer, ListCustomers
from modules.customers.domain.exceptions import CustomerNotFound, CustomerValidationError
from modules.customers.infrastructure.django.repositories import DjangoCustomerRepository

from .pagination import CustomerPagination
from .serializers import CustomerInputSerializer, CustomerSerializer

CUSTOMER_NOT_FOUND = 'Cliente no encontrado.'
DUPLICATE_PHONE_CODE = 'duplicate_phone'


def _run(use_case, **kwargs):
    """Ejecuta un caso de uso traduciendo errores de dominio a respuestas HTTP."""
    try:
        return use_case.execute(**kwargs)
    except CustomerValidationError as exc:
        raise ValidationError(exc.errors) from exc
    except CustomerNotFound as exc:
        raise NotFound(CUSTOMER_NOT_FOUND) from exc


def _parse_active(raw: str | None) -> bool | None:
    if raw is None or raw == '':
        return None
    if raw in ('true', 'false'):
        return raw == 'true'
    raise ValidationError({'active': ['Valor inválido: use "true" o "false".']})


def _duplicate_response(error: DuplicateCustomerPhone) -> Response:
    # Respuesta directa: una APIException convertiría `id` y `active` en texto.
    matches = [
        {'id': str(c.id), 'name': c.name, 'phone': c.phone, 'active': c.active} for c in error.matches
    ]
    return Response(
        {'code': DUPLICATE_PHONE_CODE, 'detail': str(error), 'matches': matches},
        status=status.HTTP_409_CONFLICT,
    )


class CustomerListCreateView(APIView):
    def get(self, request):
        active = _parse_active(request.query_params.get('active'))
        search = request.query_params.get('search', '').strip() or None
        customers = ListCustomers(DjangoCustomerRepository()).execute(search=search, active=active)
        paginator = CustomerPagination()
        page = paginator.paginate_queryset(customers, request, view=self)
        return paginator.get_paginated_response(CustomerSerializer(page, many=True).data)

    def post(self, request):
        serializer = CustomerInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        use_case = CreateCustomer(DjangoCustomerRepository(), settings.DEFAULT_PHONE_COUNTRY_CODE)
        try:
            customer = _run(use_case, **{'name': None, **serializer.validated_data})
        except DuplicateCustomerPhone as exc:
            return _duplicate_response(exc)
        return Response(CustomerSerializer(customer).data, status=status.HTTP_201_CREATED)


class CustomerDetailView(APIView):
    def get(self, request, customer_id):
        customer = _run(GetCustomer(DjangoCustomerRepository()), customer_id=customer_id)
        return Response(CustomerSerializer(customer).data)

    def patch(self, request, customer_id):
        serializer = CustomerInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        changes = {k: v for k, v in serializer.validated_data.items() if k != 'confirm_duplicate'}
        use_case = UpdateCustomer(DjangoCustomerRepository(), settings.DEFAULT_PHONE_COUNTRY_CODE)
        customer = _run(use_case, customer_id=customer_id, **changes)
        return Response(CustomerSerializer(customer).data)


class CustomerActivateView(APIView):
    def post(self, request, customer_id):
        customer = _run(ActivateCustomer(DjangoCustomerRepository()), customer_id=customer_id)
        return Response(CustomerSerializer(customer).data)


class CustomerDeactivateView(APIView):
    def post(self, request, customer_id):
        customer = _run(DeactivateCustomer(DjangoCustomerRepository()), customer_id=customer_id)
        return Response(CustomerSerializer(customer).data)
