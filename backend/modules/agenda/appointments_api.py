from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import ErrorDetail, NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.agenda.application import appointments as service
from modules.agenda.domain.appointment import STATUSES, AppointmentRuleError
from modules.agenda.infrastructure.adapters import professional_names
from modules.agenda.models import Appointment
from shared.tenancy import company_id_from

ZONE = ZoneInfo('America/La_Paz')
MAX_RANGE_DAYS = 31


class AppointmentPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


def actor_from(request):
    return service.Actor(request.user.pk, request.user.get_username())


def _local(value):
    return value.astimezone(ZONE).isoformat() if value else None


class CreateSerializer(serializers.Serializer):
    professional_id = serializers.UUIDField()
    customer_id = serializers.UUIDField()
    service_id = serializers.UUIDField()
    starts = serializers.DateTimeField(default_timezone=ZONE)
    duration_minutes = serializers.IntegerField(min_value=1, max_value=1440)
    notes = serializers.CharField(max_length=1000, allow_blank=True, required=False, default='')


class RescheduleSerializer(serializers.Serializer):
    starts = serializers.DateTimeField(default_timezone=ZONE)
    duration_minutes = serializers.IntegerField(min_value=1, max_value=1440, required=False)
    reason = serializers.CharField(max_length=500, allow_blank=True)


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, allow_blank=True)


class NotesSerializer(serializers.Serializer):
    notes = serializers.CharField(max_length=1000, allow_blank=True)


class ListQuerySerializer(serializers.Serializer):
    from_ = serializers.DateField(required=False, source='from_date')
    to = serializers.DateField(required=False, source='to_date')
    professional = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(choices=STATUSES, required=False)
    search = serializers.CharField(required=False, allow_blank=True, max_length=150)

    def to_internal_value(self, data):
        data = data.copy()
        if 'from' in data:
            data['from_'] = data['from']
        return super().to_internal_value(data)


class SlotsQuerySerializer(serializers.Serializer):
    professional = serializers.UUIDField()
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    duration = serializers.IntegerField(min_value=1, max_value=1440, required=False)

    def validate(self, values):
        if values['date_to'] < values['date_from'] or (values['date_to'] - values['date_from']).days >= MAX_RANGE_DAYS:
            raise ValidationError({'date_to': f'Indica un rango de hasta {MAX_RANGE_DAYS} días.'})
        return values


def present(appointment, names, detail=False):
    data = {
        'id': str(appointment.id), 'professional_id': str(appointment.professional_id),
        'professional_name': names.get(appointment.professional_id, ''),
        'customer_id': str(appointment.customer_id), 'customer_name': appointment.customer_name,
        'service_id': str(appointment.service_id), 'service_name': appointment.service_name,
        'starts': _local(appointment.starts), 'ends': _local(appointment.ends),
        'duration_minutes': appointment.duration_minutes, 'notes': appointment.notes,
        'status': appointment.status, 'allowed_actions': service.allowed_actions(appointment),
        'timezone': ZONE.key,
    }
    if detail:
        data['created_at'] = _local(appointment.created_at)
        data['history'] = [
            {'id': event.id, 'kind': event.kind, 'author_id': event.author_id, 'author_name': event.author_name, 'created_at': _local(event.created_at),
             'reason': event.reason, 'previous_starts': _local(event.previous_starts),
             'previous_ends': _local(event.previous_ends)}
            for event in appointment.events.all()
        ]
    return data


class AppointmentView(APIView):
    required_modules = ('personnel', 'agenda', 'customers', 'services')

    def handle_exception(self, exc):
        """Los errores 400 añaden `codes` (campo → código estable) para que el cliente los traduzca a su idioma."""
        response = super().handle_exception(exc)
        if isinstance(exc, ValidationError) and isinstance(response.data, dict):
            codes = exc.get_codes()
            if isinstance(codes, dict):
                response.data = {**response.data, 'codes': {
                    field: (code[0] if isinstance(code, list) and code else code) for field, code in codes.items()}}
        return response

    def run(self, action, *args, **kwargs):
        try:
            return action(*args, **kwargs)
        except AppointmentRuleError as exc:
            raise ValidationError({exc.field: [ErrorDetail(exc.message, code=exc.code)]}) from exc
        except service.AppointmentNotFound as exc:
            raise NotFound('Cita no encontrada.') from exc
        except service.AppointmentConflict as exc:
            return Response({'detail': exc.message, 'code': exc.code}, status=status.HTTP_409_CONFLICT)

    def respond(self, result, code=status.HTTP_200_OK):
        if isinstance(result, Response):
            return result
        result = Appointment.objects.prefetch_related('events').get(pk=result.pk)
        names = professional_names(result.company_id, {result.professional_id})
        return Response(present(result, names, detail=True), status=code)

    def get_appointment(self, request, appointment_id):
        appointment = Appointment.objects.filter(
            company_id=company_id_from(request), pk=appointment_id).prefetch_related('events').first()
        if appointment is None:
            raise NotFound('Cita no encontrada.')
        return appointment


class AppointmentListCreateView(AppointmentView):
    def get(self, request):
        query = ListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        values = query.validated_data
        rows = Appointment.objects.filter(company_id=company_id_from(request))
        if 'from_date' in values:
            rows = rows.filter(starts__gte=datetime.combine(values['from_date'], datetime.min.time(), ZONE))
        if 'to_date' in values:
            rows = rows.filter(starts__lt=datetime.combine(values['to_date'] + timedelta(days=1),
                                                           datetime.min.time(), ZONE))
        if 'professional' in values:
            rows = rows.filter(professional_id=values['professional'])
        if 'status' in values:
            rows = rows.filter(status=values['status'])
        if values.get('search', '').strip():
            rows = rows.filter(customer_name__icontains=values['search'].strip())
        paginator = AppointmentPagination()
        page = paginator.paginate_queryset(rows.order_by('starts', 'id'), request)
        names = professional_names(company_id_from(request), {row.professional_id for row in page})
        return paginator.get_paginated_response([present(row, names) for row in page])

    def post(self, request):
        serializer = CreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = self.run(service.create, company_id_from(request), actor_from(request), **serializer.validated_data)
        return self.respond(result, status.HTTP_201_CREATED)


class AppointmentDetailView(AppointmentView):
    def get(self, request, appointment_id):
        appointment = self.get_appointment(request, appointment_id)
        names = professional_names(appointment.company_id, {appointment.professional_id})
        return Response(present(appointment, names, detail=True))

    def patch(self, request, appointment_id):
        serializer = NotesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = self.run(service.update_notes, company_id_from(request), appointment_id,
                          serializer.validated_data['notes'])
        return self.respond(result)


class AppointmentActionView(AppointmentView):
    action = ''

    def post(self, request, appointment_id):
        company_id, user_id = company_id_from(request), actor_from(request)
        if self.action == 'confirm':
            call = (service.confirm, company_id, user_id, appointment_id)
        elif self.action == 'attend':
            call = (service.mark_attended, company_id, user_id, appointment_id)
        elif self.action == 'no_show':
            call = (service.mark_no_show, company_id, user_id, appointment_id)
        elif self.action == 'cancel':
            data = ReasonSerializer(data=request.data)
            data.is_valid(raise_exception=True)
            call = (service.cancel, company_id, user_id, appointment_id, data.validated_data['reason'])
        else:
            data = RescheduleSerializer(data=request.data)
            data.is_valid(raise_exception=True)
            call = (service.reschedule, company_id, user_id, appointment_id, data.validated_data['starts'],
                    data.validated_data.get('duration_minutes'), data.validated_data['reason'])
        return self.respond(self.run(*call))


class FreeSlotsView(AppointmentView):
    def get(self, request):
        query = SlotsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        values = query.validated_data
        company_id = company_id_from(request)
        from modules.agenda.infrastructure.adapters import professional_exists
        if not professional_exists(company_id, values['professional']):
            raise NotFound('Profesional no encontrado.')
        slots = service.free_slots(company_id, values['professional'], values['date_from'],
                                   values['date_to'], values.get('duration'))
        return Response({'timezone': ZONE.key, 'slots': slots, 'now': timezone.now().astimezone(ZONE).isoformat()})
