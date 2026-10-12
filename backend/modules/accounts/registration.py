from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction

from .models import Company, UserRole

COMPANY_EXISTS = 'Ya existe una empresa con ese nombre.'
USERNAME_EXISTS = 'Ya existe un usuario con ese nombre.'


class RegistrationError(Exception):
    def __init__(self, errors: dict[str, list[str]]):
        super().__init__(errors)
        self.errors = errors


def _conflicts(company_name: str, username: str) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    if Company.objects.filter(name__iexact=company_name).exists():
        errors['company_name'] = [COMPANY_EXISTS]
    if get_user_model().objects.filter(username=username).exists():
        errors['username'] = [USERNAME_EXISTS]
    return errors


def register_company_admin(*, company_name: str, username: str, first_name: str, last_name: str,
                           email: str, password: str):
    """Crea la empresa y su primer usuario admin en una sola transacción; devuelve el usuario."""
    User = get_user_model()
    company_name = ' '.join(company_name.split())
    errors = _conflicts(company_name, username)
    candidate = User(username=username, first_name=first_name, last_name=last_name, email=email)
    try:
        validate_password(password, user=candidate)
    except DjangoValidationError as exc:
        errors['password'] = list(exc.messages)
    if errors:
        raise RegistrationError(errors)
    try:
        with transaction.atomic():
            company = Company.objects.create(name=company_name)
            return User.objects.create_user(
                username=username, password=password, first_name=first_name, last_name=last_name,
                email=email, company=company, role=UserRole.ADMIN,
            )
    except IntegrityError:
        # Carrera entre dos altas iguales: la restricción de la BD es la última barrera.
        raise RegistrationError(_conflicts(company_name, username) or {'company_name': [COMPANY_EXISTS]}) from None
