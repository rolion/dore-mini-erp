"""Empresa de la petición: se deriva siempre del usuario autenticado, nunca de datos que envíe el cliente.

Lee el atributo `company_id` por nombre: los módulos de negocio no importan `accounts`.
"""
from uuid import UUID


class MissingCompanyError(Exception):
    """La petición llegó sin una empresa: el permiso por defecto debió haberla rechazado antes."""


def company_id_from(request) -> UUID:
    company_id = getattr(getattr(request, 'user', None), 'company_id', None)
    if company_id is None:
        raise MissingCompanyError('La petición no tiene una empresa asociada.')
    return company_id
