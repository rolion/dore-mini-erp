from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from modules.dentistry.application.evaluations import EvaluationCommands, EvaluationQueries
from modules.dentistry.domain import odontogram_catalog as catalog
from modules.dentistry.domain.odontogram import (
    EvaluationNotFound, EvaluationStateError, EvaluationValidationError,
)
from modules.dentistry.domain.patient import PatientArchived, PatientNotFound
from modules.dentistry.infrastructure.adapters import CustomersAdapter, PatientGate, ProfessionalLookup
from modules.dentistry.infrastructure.evaluation_repository import DjangoEvaluationRepository
from modules.dentistry.infrastructure.repository import DjangoPatientRepository
from shared.tenancy import company_id_from

from .views import ClinicalView, Conflict, PatientPagination


class FindingInput(serializers.Serializer):
    piece = serializers.IntegerField()
    condition = serializers.CharField(max_length=20)
    surfaces = serializers.ListField(child=serializers.CharField(max_length=2), required=False, default=list,
                                     max_length=8)
    diagnosis = serializers.CharField(required=False, allow_blank=True, default='', max_length=500)
    notes = serializers.CharField(required=False, allow_blank=True, default='', max_length=1000)


class GeneralFindingInput(serializers.Serializer):
    diagnosis = serializers.CharField(max_length=500)
    notes = serializers.CharField(required=False, allow_blank=True, default='', max_length=1000)


class EvaluationInput(serializers.Serializer):
    dentition = serializers.CharField(max_length=10)
    clinical_date = serializers.DateField()
    professional_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    findings = FindingInput(many=True, required=False, default=list, max_length=64)
    general_findings = GeneralFindingInput(many=True, required=False, default=list, max_length=20)


class AmendInput(serializers.Serializer):
    reason = serializers.CharField(max_length=500)


def run(operation):
    try:
        return operation()
    except (EvaluationNotFound, PatientNotFound) as exc:
        raise NotFound(str(exc)) from exc
    except EvaluationValidationError as exc:
        raise ValidationError(exc.errors) from exc
    except (EvaluationStateError, PatientArchived) as exc:
        raise Conflict(str(exc)) from exc


class EvaluationView(ClinicalView):
    def evaluation_context(self, request):
        company_id = company_id_from(request)
        repository, patients = DjangoEvaluationRepository(company_id), DjangoPatientRepository(company_id)
        gate = PatientGate(patients, CustomersAdapter(company_id))
        professionals = ProfessionalLookup(company_id)
        return (EvaluationCommands(repository, patients, gate, professionals),
                EvaluationQueries(repository, patients, professionals), repository)

    @staticmethod
    def payload(request):
        data = EvaluationInput(data=request.data)
        data.is_valid(raise_exception=True)
        return data.validated_data


class CatalogView(ClinicalView):
    def get(self, request):
        return Response(catalog.as_dict())


class PatientEvaluationListView(EvaluationView):
    def get(self, request, customer_id):
        _, queries, _ = self.evaluation_context(request)
        rows, replaced = run(lambda: queries.list(customer_id))
        paginator = PatientPagination()
        page = paginator.paginate_queryset(rows, request)
        return paginator.get_paginated_response(queries.summaries(page, replaced))

    def post(self, request, customer_id):
        commands, queries, _ = self.evaluation_context(request)
        data = self.payload(request)
        row = run(lambda: commands.create(customer_id, data, **self.actor(request)))
        return Response(queries.detail(row), status=201)


class EvaluationDetailView(EvaluationView):
    def get(self, request, evaluation_id):
        _, queries, repository = self.evaluation_context(request)
        return Response(queries.detail(run(lambda: repository.get(evaluation_id))))

    def put(self, request, evaluation_id):
        commands, queries, _ = self.evaluation_context(request)
        data = self.payload(request)
        return Response(queries.detail(run(lambda: commands.update(evaluation_id, data))))

    def delete(self, request, evaluation_id):
        commands, _, _ = self.evaluation_context(request)
        run(lambda: commands.discard(evaluation_id))
        return Response(status=204)


class EvaluationConfirmView(EvaluationView):
    def post(self, request, evaluation_id):
        commands, queries, _ = self.evaluation_context(request)
        row = run(lambda: commands.confirm(evaluation_id, **self.actor(request)))
        return Response(queries.detail(row))


class EvaluationAmendView(EvaluationView):
    def post(self, request, evaluation_id):
        commands, queries, _ = self.evaluation_context(request)
        data = AmendInput(data=request.data)
        data.is_valid(raise_exception=True)
        row = run(lambda: commands.amend(evaluation_id, data.validated_data['reason'], **self.actor(request)))
        return Response(queries.detail(row), status=201)
