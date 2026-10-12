import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class Company(models.Model):
    """Empresa propietaria de los datos de negocio. Las empresas no se borran: se desactivan."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'accounts_company'
        ordering = ['name', 'id']
        constraints = [
            # El nombre es único sin distinguir mayúsculas: el registro público no admite dos "Cuñapés SRL".
            models.UniqueConstraint(Lower('name'), name='accounts_company_name_ci_unique'),
        ]

    def save(self, *args, **kwargs):
        self.name = ' '.join(self.name.split())
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class UserRole(models.TextChoices):
    ADMIN = 'admin', 'Administrador'


class User(AbstractUser):
    """Usuario propio mínimo; pertenece a lo sumo a una empresa y tiene un rol dentro de ella."""

    # Nulo solo para usuarios de operación (p. ej. `createsuperuser`): sin empresa no hay acceso a la API de negocio.
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.PROTECT, related_name='users')
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.ADMIN)
