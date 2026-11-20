from uuid import UUID

from django.core.management.base import CommandError

from modules.accounts.models import Company


def find_company(ref: str) -> Company:
    """Busca una empresa por UUID o por nombre exacto (sin distinguir mayúsculas)."""
    try:
        company = Company.objects.filter(pk=UUID(ref)).first()
    except ValueError:
        company = Company.objects.filter(name__iexact=' '.join(ref.split())).first()
    if company is None:
        raise CommandError(f'No existe la empresa «{ref}».')
    return company
