from zoneinfo import ZoneInfo

from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from modules.dentistry.application.encounters import EncounterCommands, EncounterQueries
from modules.dentistry.application.evaluations import EvaluationCommands, EvaluationQueries
from modules.dentistry.domain.encounter import (
    CANCELLED, FINISHED, IN_PROGRESS, PENDING, EncounterNotFound, EncounterStateError, EncounterValidationError,
)
from modules.dentistry.domain.odontogram import EvaluationValidationError
from modules.dentistry.domain.patient import PatientNotFound
from modules.dentistry.infrastructure.adapters import AgendaAdapter, CustomersAdapter, PatientGate, ProfessionalLookup
from modules.dentistry.infrastructure.encounter_repository import DjangoEncounterRepository
from modules.dentistry.infrastructure.evaluation_repository import DjangoEvaluationRepository
from modules.dentistry.infrastructure.repository import DjangoPatientRepository
from shared.tenancy import company_id_from

from .evaluation_views import FindingInput, GeneralFindingInput
from .views import ClinicalView, Conflict, PatientPagination

ZONE = ZoneInfo('America/La_Paz')
ENCOUNTER_STATUSES = (PENDING, IN_PROGRESS, FINISHED, CANCELLED)
APPOINTMENT_STATUSES = ('scheduled', 'confirmed', 'cancelled', 'attended', 'no_show')


def run(operation):
    try:
        return operation()
    except (EncounterNotFound, PatientNotFound) as exc:
        raise NotFound(str(exc)) from exc
    except EncounterValidationError as exc:
        raise ValidationError(exc.errors) from exc
    except EvaluationValidationError as exc:
        raise ValidationError(exc.errors) from exc
    except EncounterStateError as exc:
        raise Conflict({'detail': str(exc), 'code': exc.code}) from exc
    except _agenda_errors() as exc:
        code = getattr(exc, 'code', 'invalid_transition')
        raise Conflict({'detail': getattr(exc, 'message', str(exc)), 'code': code}) from exc


def _agenda_errors():
    from modules.agenda import services
    return services.AppointmentConflict, services.AppointmentRuleError


class ListQuery(serializers.Serializer):
    from_ = serializers.DateField(required=False)
    to = serializers.DateField(required=False)
    professional = serializers.UUIDField(required=False)
    customer = serializers.UUIDField(required=False)
    search = serializers.CharField(required=False, allow_blank=True, max_length=150)
    status = serializers.ChoiceField(choices=APPOINTMENT_STATUSES, required=False)
    encounter_status = serializers.ChoiceField(choices=ENCOUNTER_STATUSES, required=False)
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100, default=20)

    def to_internal_value(self, data):
        data = data.copy()
        if 'from' in data:
            data['from_'] = data['from']
        return super().to_internal_value(data)


class CancelInput(serializers.Serializer):
    reason = serializers.CharField(allow_blank=True, max_length=500)


class ObservationsInput(serializers.Serializer):
    observations = serializers.CharField(allow_blank=True, max_length=2000)


class OdontogramInput(serializers.Serializer):
    dentition = serializers.CharField(required=False, max_length=10)
    findings = FindingInput(many=True, required=False, default=list, max_length=64)
    general_findings = GeneralFindingInput(many=True, required=False, default=list, max_length=20)


class EncounterView(ClinicalView):
    required_modules = ('dentistry', 'agenda', 'customers', 'personnel')

    def wiring(self, request):
        company_id = company_id_from(request)
        patients, evaluations = DjangoPatientRepository(company_id), DjangoEvaluationRepository(company_id)
        customers, professionals = CustomersAdapter(company_id), ProfessionalLookup(company_id)
        encounters, agenda = DjangoEncounterRepository(company_id), AgendaAdapter(company_id)
        gate = PatientGate(patients, customers)
        commands = EncounterCommands(
            encounters, evaluations, EvaluationCommands(evaluations, patients, gate, professionals),
            patients, gate, agenda)
        queries = EncounterQueries(encounters, evaluations, patients, customers, agenda, professionals)
        return commands, queries, EvaluationQueries(evaluations, patients, professionals)


class AppointmentListView(EncounterView):
    def get(self, request):
        query = ListQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        values = query.validated_data
        today = timezone.now().astimezone(ZONE).date()
        first, last = values.get('from_', values.get('to', today)), values.get('to', values.get('from_', today))
        if last < first:
            raise ValidationError({'to': ['La fecha final debe ser igual o posterior a la inicial.']})
        _, queries, _ = self.wiring(request)
        page, size = values['page'], values['page_size']
        total, items = run(lambda: queries.listing(
            first_day=first, last_day=last, professional_id=values.get('professional'),
            customer_id=values.get('customer'), search=values.get('search', '').strip(),
            status=values.get('status'), encounter_status=values.get('encounter_status'),
            offset=(page - 1) * size, limit=size))
        return Response({'count': total, 'next': None, 'previous': None, 'results': items,
                         'from': first.isoformat(), 'to': last.isoformat()})


class AppointmentEncounterView(EncounterView):
    def get(self, request, appointment_id):
        _, queries, _ = self.wiring(request)
        return Response(run(lambda: queries.detail(appointment_id)))


class EncounterActionView(EncounterView):
    action = 'start'

    def post(self, request, appointment_id):
        commands, queries, _ = self.wiring(request)
        actor = self.actor(request)
        status = 200
        if self.action == 'start':
            _, created = run(lambda: commands.start(appointment_id, **actor))
            status = 201 if created else 200
        elif self.action == 'finish':
            run(lambda: commands.finish(appointment_id, **actor))
        else:
            data = CancelInput(data=request.data)
            data.is_valid(raise_exception=True)
            run(lambda: commands.cancel(appointment_id, data.validated_data['reason'], **actor))
        return Response(run(lambda: queries.detail(appointment_id)), status=status)


class EncounterDetailView(EncounterView):
    def patch(self, request, encounter_id):
        commands, queries, _ = self.wiring(request)
        data = ObservationsInput(data=request.data)
        data.is_valid(raise_exception=True)
        row = run(lambda: commands.set_observations(encounter_id, data.validated_data['observations']))
        return Response(run(lambda: queries.detail(row.appointment_id)))


class EncounterOdontogramView(EncounterView):
    def post(self, request, encounter_id):
        commands, _, evaluation_queries = self.wiring(request)
        data = OdontogramInput(data=request.data)
        data.is_valid(raise_exception=True)
        row = run(lambda: commands.create_odontogram(encounter_id, data.validated_data, **self.actor(request)))
        return Response(evaluation_queries.detail(row), status=201)


class PatientEncounterListView(EncounterView):
    def get(self, request, customer_id):
        _, queries, _ = self.wiring(request)
        rows = run(lambda: queries.history(customer_id))
        paginator = PatientPagination()
        page = paginator.paginate_queryset(rows, request)
        return paginator.get_paginated_response(queries.history_items(page))
