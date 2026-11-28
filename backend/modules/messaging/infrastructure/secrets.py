"""Resuelve `secret_ref` (nombre de variable de entorno) a su valor, en el momento de usarlo y sin guardarlo."""
import os

from ..domain.errors import SecretUnavailable
from ..domain.rules import SECRET_REF_PATTERN, secret_ref_prefix


def _belongs_to(ref: str, company_id) -> bool:
    """La variable solo se lee si cumple el patrón Y lleva el prefijo de la empresa dueña de la conexión (REV-07):
    una fila creada fuera de la API no puede apuntar al secreto de otra empresa."""
    text = ref or ''
    prefix = secret_ref_prefix(company_id)
    return bool(SECRET_REF_PATTERN.match(text) and text.startswith(prefix) and len(text) > len(prefix))


class EnvSecretResolver:
    def available(self, ref: str, company_id) -> bool:
        return bool(_belongs_to(ref, company_id) and os.environ.get(ref))

    def get(self, ref: str, company_id) -> str:
        value = os.environ.get(ref, '') if _belongs_to(ref, company_id) else ''
        if not value:
            raise SecretUnavailable(ref)  # el mensaje lleva el NOMBRE de la variable, nunca un valor
        return value
