"""Traducción común de errores de dominio de prospectos/oportunidades a HTTP (400, 404, 409)."""
from uuid import UUID

from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from modules.crm.domain.errors import CrmConflict, CrmNotFound, CrmValidationError


def run(callback, render, *, status=200):
    """Ejecuta un caso de uso en una transacción y presenta el resultado con `render`."""
    try:
        with transaction.atomic():
            result = callback()
            data = render(result)
        return Response(data, status=status)
    except CrmNotFound as exc:
        raise NotFound(str(exc) or 'No encontrado.') from exc
    except CrmValidationError as exc:
        raise ValidationError(exc.errors) from exc
    except CrmConflict as exc:
        # Respuesta directa: DRF convertiría en texto los datos extra (p. ej. `candidates`).
        return Response({'detail': exc.message, 'code': exc.code, **exc.extra}, status=409)


def body(serializer_class, request, **kwargs) -> dict:
    serializer = serializer_class(data=request.data, **kwargs)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def query_uuid(request, name: str, *, required: bool = False) -> UUID | None:
    raw = request.query_params.get(name, '').strip()
    if not raw:
        if required:
            raise ValidationError({name: ['Este parámetro es obligatorio.']})
        return None
    try:
        return UUID(raw)
    except ValueError as exc:
        raise ValidationError({name: ['Identificador inválido.']}) from exc


def query_choice(request, name: str, choices: tuple[str, ...]) -> str | None:
    raw = request.query_params.get(name, '').strip()
    if raw and raw not in choices:
        raise ValidationError({name: [f"Usa {' o '.join(choices)}."]})
    return raw or None
