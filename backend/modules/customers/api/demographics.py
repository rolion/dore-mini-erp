from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.customers.domain.demographics import DemographicsInvalid
from modules.customers.application.demographics import UpdateDemographics
from modules.customers.domain.exceptions import CustomerNotFound
from modules.customers.infrastructure.django.demographics_repository import DjangoDemographicsRepository
from shared.tenancy import company_id_from


class DemographicsInput(serializers.Serializer):
    birth_date = serializers.DateField(required=False, allow_null=True)
    responsible_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    responsible_phone = serializers.CharField(required=False, allow_blank=True, max_length=30)


def run(operation):
    try:
        return operation()
    except CustomerNotFound as exc:
        raise NotFound('Cliente no encontrado.') from exc
    except DemographicsInvalid as exc:
        raise ValidationError(exc.errors) from exc


class CustomerDemographicsView(APIView):
    required_modules = ('customers',)

    def get(self, request, customer_id):
        repo = DjangoDemographicsRepository(company_id_from(request))
        return Response(run(lambda: repo.get(customer_id)).snapshot())

    def patch(self, request, customer_id):
        data = DemographicsInput(data=request.data)
        data.is_valid(raise_exception=True)
        repo = DjangoDemographicsRepository(company_id_from(request))
        # Actor identity comes from authentication, never from the payload.
        current = run(lambda: UpdateDemographics(repo).execute(
            customer_id, data.validated_data, timezone.localdate(), request.user.pk, request.user.get_username()))
        return Response(current.snapshot())


class CustomerDemographicsHistoryView(APIView):
    required_modules = ('customers',)

    def get(self, request, customer_id):
        repo = DjangoDemographicsRepository(company_id_from(request))
        rows = run(lambda: repo.history(customer_id))
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(rows, request)
        return paginator.get_paginated_response([
            {'id': row.pk, 'author_id': row.author_id, 'author_name': row.author_name,
             'created_at': row.created_at, 'before': row.before, 'after': row.after} for row in page])
