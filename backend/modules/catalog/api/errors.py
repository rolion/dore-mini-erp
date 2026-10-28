from rest_framework import status
from rest_framework.exceptions import APIException


class Conflict(APIException):
    """409 con `{detail, code}`: la acción choca con el estado actual (historial, unidad en uso, ...)."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = 'La acción no es posible en el estado actual.'

    def __init__(self, detail: str, code: str):
        super().__init__({'detail': detail, 'code': code})
