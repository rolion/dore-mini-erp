import uuid

from django.db import models


class ProfileModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=150)
    active = models.BooleanField(default=True)
    # Referencias históricas, separadas del vínculo de acceso y sin FK entre contextos.
    created_by = models.BigIntegerField()
    updated_by = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['name', 'id']


class SpecialtyModel(ProfileModel):
    class Meta(ProfileModel.Meta):
        db_table = 'personnel_specialty'


class ProfessionalModel(ProfileModel):
    identification = models.CharField(max_length=50, blank=True, default='')
    phone = models.CharField(max_length=30, blank=True, default='')
    email = models.CharField(max_length=254, blank=True, default='')
    registration_number = models.CharField(max_length=100, blank=True, default='')
    user_id = models.BigIntegerField(null=True, blank=True)
    specialties = models.ManyToManyField(SpecialtyModel, related_name='professionals', blank=True)

    class Meta(ProfileModel.Meta):
        db_table = 'personnel_professional'
        constraints = [models.UniqueConstraint(fields=['user_id'], name='personnel_user_unique')]
