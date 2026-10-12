"""Ayudas para las pruebas de los módulos de negocio (usuarios con empresa y cliente autenticado)."""
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

from .models import Company

PASSWORD = 'x-Pass-123'


def make_company(name: str = 'Empresa Demo', **extra) -> Company:
    return Company.objects.create(name=name, **extra)


def make_admin(company: Company | None = None, username: str = 'ana', **extra):
    """Usuario admin de `company` (si no se pasa, crea una empresa nueva)."""
    company = company or make_company(f'Empresa de {username}')
    return get_user_model().objects.create_user(username=username, password=PASSWORD, company=company, **extra)


def authenticate(client, user) -> Token:
    token, _ = Token.objects.get_or_create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return token
