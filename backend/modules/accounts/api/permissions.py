from rest_framework.permissions import BasePermission

from modules.accounts.models import UserRole


class CompanyAdminPermission(BasePermission):
    """Permiso por defecto de la API: usuario autenticado, de una empresa activa y con rol admin."""

    message = 'Tu usuario no tiene acceso a los datos de una empresa activa.'

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        company = user.company
        return company is not None and company.is_active and user.role == UserRole.ADMIN
