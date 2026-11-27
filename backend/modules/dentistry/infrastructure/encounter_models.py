import uuid

from django.db import models


class EncounterModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    appointment_id = models.UUIDField()  # cita de Agenda; sin FK entre módulos
    customer_id = models.UUIDField()  # paciente (= cliente), copiado de la cita al iniciar
    professional_id = models.UUIDField()
    status = models.CharField(max_length=12, default='in_progress')
    started_at = models.DateTimeField()
    started_by = models.PositiveBigIntegerField()
    started_by_name = models.CharField(max_length=150)
    finished_at = models.DateTimeField(null=True, blank=True)
    finished_by = models.PositiveBigIntegerField(null=True, blank=True)
    finished_by_name = models.CharField(max_length=150, blank=True, default='')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.PositiveBigIntegerField(null=True, blank=True)
    cancelled_by_name = models.CharField(max_length=150, blank=True, default='')
    cancellation_reason = models.CharField(max_length=500, blank=True, default='')
    observations = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dentistry_encounter'
        ordering = ['-started_at', 'id']
        constraints = [
            models.UniqueConstraint(fields=['company_id', 'appointment_id'],
                                    name='dentistry_encounter_appointment_unique'),
        ]
        indexes = [models.Index(fields=['company_id', 'customer_id', 'started_at'],
                                name='dentistry_encounter_patient')]
