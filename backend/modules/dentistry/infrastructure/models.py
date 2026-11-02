import uuid
from django.db import models


class PatientModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    customer_id = models.UUIDField()
    active = models.BooleanField(default=True)
    medical_history = models.TextField(blank=True, default='')
    dental_history = models.TextField(blank=True, default='')
    allergies = models.TextField(blank=True, default='')
    medication = models.TextField(blank=True, default='')
    clinical_notes = models.TextField(blank=True, default='')
    created_by = models.PositiveBigIntegerField()
    updated_by = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dentistry_patient'
        ordering = ['-created_at', 'id']
        constraints = [models.UniqueConstraint(fields=['company_id', 'customer_id'],
                                                name='dentistry_patient_company_customer_unique')]


class PatientHistoryModel(models.Model):
    company_id = models.UUIDField(db_index=True)
    patient = models.ForeignKey(PatientModel, on_delete=models.PROTECT, related_name='history')
    author_id = models.PositiveBigIntegerField()
    author_name = models.CharField(max_length=150)
    action = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    before = models.JSONField()
    after = models.JSONField()

    class Meta:
        db_table = 'dentistry_patient_history'
        ordering = ['-created_at', '-id']
