import uuid

from django.db import models

from .encounter_models import EncounterModel


class EvaluationModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    customer_id = models.UUIDField()  # identidad del paciente (= cliente); sin FK entre módulos
    sequence = models.PositiveIntegerField()
    status = models.CharField(max_length=10, default='draft')
    dentition = models.CharField(max_length=10)
    clinical_date = models.DateField()
    professional_id = models.UUIDField(null=True, blank=True)
    catalog_version = models.PositiveIntegerField(default=1)
    amends = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='amendments')
    amendment_reason = models.CharField(max_length=500, blank=True, default='')
    # Atención de la que nace (PB-ODO-007); NULL = evaluación previa o creada desde la ficha del paciente.
    encounter = models.ForeignKey(EncounterModel, null=True, blank=True, on_delete=models.PROTECT,
                                  related_name='evaluations')
    created_by = models.PositiveBigIntegerField()
    created_by_name = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_by = models.PositiveBigIntegerField(null=True, blank=True)
    confirmed_by_name = models.CharField(max_length=150, blank=True, default='')
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'dentistry_evaluation'
        ordering = ['-sequence']
        constraints = [
            models.UniqueConstraint(fields=['company_id', 'customer_id', 'sequence'],
                                    name='dentistry_evaluation_sequence_unique'),
            models.UniqueConstraint(fields=['company_id', 'customer_id'], condition=models.Q(status='draft'),
                                    name='dentistry_evaluation_one_draft'),
            models.UniqueConstraint(fields=['encounter'],
                                    condition=models.Q(amends__isnull=True, encounter__isnull=False),
                                    name='dentistry_evaluation_one_root_per_encounter'),
        ]


class EvaluationFindingModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    evaluation = models.ForeignKey(EvaluationModel, on_delete=models.CASCADE, related_name='findings')
    position = models.PositiveIntegerField()
    piece = models.PositiveSmallIntegerField()
    condition = models.CharField(max_length=20)
    surfaces = models.CharField(max_length=10, blank=True, default='')
    diagnosis = models.CharField(max_length=500, blank=True, default='')
    notes = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'dentistry_evaluation_finding'
        ordering = ['position']


class EvaluationGeneralFindingModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    evaluation = models.ForeignKey(EvaluationModel, on_delete=models.CASCADE, related_name='general_findings')
    position = models.PositiveIntegerField()
    diagnosis = models.CharField(max_length=500)
    notes = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'dentistry_evaluation_general_finding'
        ordering = ['position']
