from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.agenda.application.week import week_availability, week_records
from modules.agenda.domain.schedule import shifts_overlap, validate_shift
from modules.agenda.models import Schedule, Shift, Absence
from modules.agenda.infrastructure.adapters import professional_exists
from shared.tenancy import company_id_from


ZONE = ZoneInfo('America/La_Paz')
DAY_NAMES = ('lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo')


class BreakSerializer(serializers.Serializer):
    starts = serializers.TimeField()
    ends = serializers.TimeField()


class ShiftSerializer(serializers.ModelSerializer):
    day = serializers.IntegerField(min_value=0, max_value=6)
    breaks = BreakSerializer(many=True)

    class Meta:
        model = Shift
        fields = ('id', 'day', 'starts', 'ends', 'valid_from', 'valid_until', 'breaks')

    def validate(self, values):
        breaks = [(item['starts'], item['ends']) for item in values['breaks']]
        error = validate_shift(**{**values, 'breaks': breaks})
        if error:
            raise ValidationError(error)
        values['breaks'] = [{'starts': start.isoformat(), 'ends': end.isoformat()} for start, end in breaks]
        return values


class AbsenceSerializer(serializers.ModelSerializer):
    starts = serializers.DateTimeField(default_timezone=ZONE)
    ends = serializers.DateTimeField(default_timezone=ZONE)

    class Meta:
        model = Absence
        fields = ('id', 'starts', 'ends', 'reason')

    def validate(self, values):
        if values['starts'] >= values['ends']:
            raise ValidationError({'ends': 'El fin debe ser posterior al inicio.'})
        return values


class WeekSerializer(serializers.Serializer):
    start = serializers.DateField()

    def validate_start(self, value):
        if value.weekday() != 0 or value.year == 9999:
            raise ValidationError('Indica el lunes de la semana.')
        return value


class AgendaView(APIView):
    required_modules = ('personnel', 'agenda')

    def schedule_filter(self, request, professional_id):
        company_id = company_id_from(request)
        if not professional_exists(company_id, professional_id):
            raise NotFound('Profesional no encontrado.')
        return {'company_id': company_id, 'professional_id': professional_id}


class WeekView(AgendaView):
    def get(self, request, professional_id):
        scope = self.schedule_filter(request, professional_id)
        query = WeekSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        start = query.validated_data['start']
        try:
            end = start + timedelta(days=7)
        except OverflowError as exc:
            raise ValidationError({'start': 'Fecha fuera del rango permitido.'}) from exc
        shifts, absences = week_records(scope['company_id'], professional_id, start, ZONE)
        active_shifts, availability = week_availability(shifts, absences, start, ZONE)
        return Response({
            'timezone': ZONE.key, 'shifts': ShiftSerializer(active_shifts, many=True).data,
            'absences': AbsenceSerializer(absences, many=True).data, 'availability': availability,
        })


class ShiftView(AgendaView):
    def post(self, request, professional_id):
        return self.save(request, professional_id)

    def put(self, request, professional_id, shift_id):
        return self.save(request, professional_id, shift_id)

    @staticmethod
    def multiple_days(data, editing):
        """Días de un alta múltiple (`days`), o None si el envío es de un solo día (`day`)."""
        if not isinstance(data, dict) or 'days' not in data:
            return None
        days = data['days']
        if editing or 'day' in data:
            raise ValidationError({'days': 'Indica un solo día (day) o varios (days) al crear.'})
        if (not isinstance(days, list) or not days
                or any(type(day) is not int or not 0 <= day <= 6 for day in days)
                or len(set(days)) != len(days)):
            raise ValidationError({'days': 'Indica al menos un día distinto entre 0 y 6.'})
        return days

    @transaction.atomic
    def save(self, request, professional_id, shift_id=None):
        scope = self.schedule_filter(request, professional_id)
        days = self.multiple_days(request.data, shift_id is not None)
        common = {key: value for key, value in request.data.items() if key != 'days'} if days else None
        serializers = [ShiftSerializer(data={**common, 'day': day}) for day in days] if days else [
            ShiftSerializer(data=request.data),
        ]
        for serializer in serializers:
            serializer.is_valid(raise_exception=True)
        schedule, _ = Schedule.objects.get_or_create(**scope)
        Schedule.objects.filter(pk=schedule.pk).update(company_id=F('company_id'))
        shifts = schedule.shift_set.all()
        shift = get_object_or_404(shifts, pk=shift_id) if shift_id is not None else None
        for serializer in serializers:
            candidate = Shift(**serializer.validated_data)
            if any(shifts_overlap(candidate, other) for other in shifts.exclude(pk=shift_id)):
                message = 'El turno se solapa con otro turno vigente.'
                if days:
                    message = f'El turno del día {DAY_NAMES[candidate.day]} se solapa con otro turno vigente.'
                raise ValidationError({'starts': message})
        for serializer in serializers:
            serializer.instance = shift
            serializer.save(schedule=schedule)
        if days:
            return Response([serializer.data for serializer in serializers], status=201)
        return Response(serializers[0].data, status=200 if shift else 201)


class AbsenceView(AgendaView):
    @transaction.atomic
    def post(self, request, professional_id):
        scope = self.schedule_filter(request, professional_id)
        serializer = AbsenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        schedule, _ = Schedule.objects.get_or_create(**scope)
        Schedule.objects.filter(pk=schedule.pk).update(company_id=F('company_id'))
        serializer.save(schedule=schedule)
        return Response(serializer.data, status=201)


class AbsenceDetailView(AgendaView):
    def absence(self, request, professional_id, absence_id):
        scope = self.schedule_filter(request, professional_id)
        return get_object_or_404(
            Absence, pk=absence_id,
            schedule__company_id=scope['company_id'], schedule__professional_id=professional_id,
        )

    @transaction.atomic
    def put(self, request, professional_id, absence_id):
        absence = self.absence(request, professional_id, absence_id)
        serializer = AbsenceSerializer(absence, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @transaction.atomic
    def delete(self, request, professional_id, absence_id):
        self.absence(request, professional_id, absence_id).delete()
        return Response(status=204)
