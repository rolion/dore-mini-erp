import uuid

from django.db import models


class Schedule(models.Model):
    company_id = models.UUIDField()
    professional_id = models.UUIDField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('company_id', 'professional_id'), name='agenda_schedule_company_professional'
            ),
        ]


class Shift(models.Model):
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    day = models.PositiveSmallIntegerField()
    starts = models.TimeField()
    ends = models.TimeField()
    valid_from = models.DateField()
    valid_until = models.DateField()
    breaks = models.JSONField(default=list)


class Absence(models.Model):
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    starts = models.DateTimeField()
    ends = models.DateTimeField()
    reason = models.CharField(max_length=250)


class Appointment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField()
    professional_id = models.UUIDField()
    customer_id = models.UUIDField()
    customer_name = models.CharField(max_length=150)
    service_id = models.UUIDField()
    service_name = models.CharField(max_length=150)
    starts = models.DateTimeField()
    ends = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField()
    notes = models.TextField(blank=True, default='')
    status = models.CharField(max_length=12, default='scheduled')
    # Reservado para el futuro módulo de tratamientos; hoy no se valida ni se expone.
    treatment_item_id = models.UUIDField(null=True, blank=True)
    created_by = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=('company_id', 'professional_id', 'starts'), name='agenda_appt_prof_starts'),
            models.Index(fields=('company_id', 'status', 'starts'), name='agenda_appt_status_starts'),
        ]


class AppointmentEvent(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='events')
    kind = models.CharField(max_length=12)
    author_id = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=500, blank=True, default='')
    previous_starts = models.DateTimeField(null=True, blank=True)
    previous_ends = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('id',)
