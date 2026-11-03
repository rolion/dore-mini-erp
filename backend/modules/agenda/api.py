from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.agenda.domain.schedule import shifts_overlap, subtract, validate_shift
from modules.agenda.models import Schedule, Shift, Absence
from modules.agenda.infrastructure.adapters import professional_exists
from shared.tenancy import company_id_from


ZONE = ZoneInfo('America/La_Paz')


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
        shifts = list(Shift.objects.filter(
            schedule__company_id=scope['company_id'], schedule__professional_id=professional_id,
            valid_from__lt=end, valid_until__gte=start,
        ).order_by('day', 'starts'))
        absences = list(Absence.objects.filter(
            schedule__company_id=scope['company_id'], schedule__professional_id=professional_id,
            starts__lt=datetime.combine(end, datetime.min.time(), ZONE),
            ends__gt=datetime.combine(start, datetime.min.time(), ZONE),
        ).order_by('starts'))
        availability = []
        active_shifts = []
        for shift in shifts:
            date = start + timedelta(days=shift.day)
            if not shift.valid_from <= date <= shift.valid_until:
                continue
            active_shifts.append(shift)
            begins = datetime.combine(date, shift.starts, ZONE)
            finishes = datetime.combine(date, shift.ends, ZONE)
            blocks = [(absence.starts, absence.ends) for absence in absences]
            for pause in shift.breaks:
                blocks.append(tuple(datetime.fromisoformat(f'{date}T{pause[key]}').replace(tzinfo=ZONE)
                                    for key in ('starts', 'ends')))
            availability.extend(
                {'starts': left.astimezone(ZONE).isoformat(), 'ends': right.astimezone(ZONE).isoformat()}
                for left, right in subtract(begins, finishes, blocks)
            )
        return Response({
            'timezone': ZONE.key, 'shifts': ShiftSerializer(active_shifts, many=True).data,
            'absences': AbsenceSerializer(absences, many=True).data, 'availability': availability,
        })


class ShiftView(AgendaView):
    def post(self, request, professional_id):
        return self.save(request, professional_id)

    def put(self, request, professional_id, shift_id):
        return self.save(request, professional_id, shift_id)

    @transaction.atomic
    def save(self, request, professional_id, shift_id=None):
        scope = self.schedule_filter(request, professional_id)
        serializer = ShiftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        schedule, _ = Schedule.objects.get_or_create(**scope)
        Schedule.objects.filter(pk=schedule.pk).update(company_id=F('company_id'))
        shifts = schedule.shift_set.all()
        shift = get_object_or_404(shifts, pk=shift_id) if shift_id is not None else None
        candidate = Shift(**serializer.validated_data)
        if any(shifts_overlap(candidate, other) for other in shifts.exclude(pk=shift_id)):
            raise ValidationError({'starts': 'El turno se solapa con otro turno vigente.'})
        serializer.instance = shift
        serializer.save(schedule=schedule)
        return Response(serializer.data, status=200 if shift else 201)


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
