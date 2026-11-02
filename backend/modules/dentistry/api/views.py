from rest_framework import serializers
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from config.permissions import CompanyClinicalPermission
from modules.dentistry.application.patients import PatientCommands, PatientQueries
from modules.dentistry.domain.patient import (
    DuplicatePatient, PatientArchived, PatientInvalid, PatientNotFound,
)
from modules.dentistry.infrastructure.adapters import CustomersAdapter
from modules.dentistry.infrastructure.repository import DjangoPatientRepository
from shared.tenancy import company_id_from


class Conflict(APIException):
    status_code = 409


class ClinicalInput(serializers.Serializer):
    medical_history = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    dental_history = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    allergies = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    medication = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    clinical_notes = serializers.CharField(required=False, allow_blank=True, max_length=4000)


class PatientCreateInput(ClinicalInput):
    customer_id = serializers.UUIDField()


class PatientPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


def run(operation):
    try:
        return operation()
    except PatientNotFound as exc:
        raise NotFound(str(exc)) from exc
    except PatientInvalid as exc:
        raise ValidationError(exc.errors) from exc
    except (DuplicatePatient, PatientArchived) as exc:
        raise Conflict(str(exc)) from exc


class ClinicalView(APIView):
    required_modules = ('dentistry', 'customers')
    permission_classes = [CompanyClinicalPermission]

    def context(self, request):
        company_id = company_id_from(request)
        repo, customers = DjangoPatientRepository(company_id), CustomersAdapter(company_id)
        return repo, PatientCommands(repo, customers), PatientQueries(repo, customers)

    @staticmethod
    def actor(request):
        return {'author_id': request.user.pk, 'author_name': request.user.get_username()}


class CapabilitiesView(ClinicalView):
    def get(self, request):
        return Response({'clinical_access': True})


class PatientListView(ClinicalView):
    def get(self, request):
        _, _, queries = self.context(request)
        active = request.query_params.get('active', 'true')
        if active not in ('', 'true', 'false'):
            raise ValidationError({'active': ['Use true, false o vacío.']})
        rows = queries.list(request.query_params.get('search', '').strip(),
                            None if active == '' else active == 'true')
        paginator = PatientPagination()
        page = paginator.paginate_queryset(rows, request)
        return paginator.get_paginated_response(queries.summaries(page))

    def post(self, request):
        data = PatientCreateInput(data=request.data)
        data.is_valid(raise_exception=True)
        values = dict(data.validated_data)
        customer_id = values.pop('customer_id')
        _, commands, queries = self.context(request)
        row = run(lambda: commands.create(customer_id, values, **self.actor(request)))
        return Response(queries.detail(row), status=201)


class PatientDetailView(ClinicalView):
    def get(self, request, customer_id):
        repo, _, queries = self.context(request)
        return Response(queries.detail(run(lambda: repo.get(customer_id))))

    def patch(self, request, customer_id):
        data = ClinicalInput(data=request.data)
        data.is_valid(raise_exception=True)
        _, commands, queries = self.context(request)
        row = run(lambda: commands.change(customer_id, data.validated_data, 'edit', **self.actor(request)))
        return Response(queries.detail(row))


class PatientStateView(ClinicalView):
    action = 'archive'

    def post(self, request, customer_id):
        _, commands, queries = self.context(request)
        row = run(lambda: commands.change(customer_id, {}, self.action, **self.actor(request)))
        return Response(queries.detail(row))


class PatientHistoryView(ClinicalView):
    def get(self, request, customer_id):
        repo, _, _ = self.context(request)
        rows = run(lambda: repo.history(customer_id))
        paginator = PatientPagination()
        page = paginator.paginate_queryset(rows, request)
        return paginator.get_paginated_response([
            {'id': row.pk, 'author_id': row.author_id, 'author_name': row.author_name, 'action': row.action,
             'created_at': row.created_at, 'before': row.before, 'after': row.after} for row in page])
