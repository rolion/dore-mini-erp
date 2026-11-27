"""Resuelve `secret_ref` (nombre de variable de entorno) a su valor, en el momento de usarlo y sin guardarlo."""
import os

from ..domain.errors import SecretUnavailable
from ..domain.rules import SECRET_REF_PATTERN


class EnvSecretResolver:
    def available(self, ref: str) -> bool:
        return bool(SECRET_REF_PATTERN.match(ref or '') and os.environ.get(ref))

    def get(self, ref: str) -> str:
        value = os.environ.get(ref, '') if SECRET_REF_PATTERN.match(ref or '') else ''
        if not value:
            raise SecretUnavailable(ref)  # el mensaje lleva el NOMBRE de la variable, nunca un valor
        return value
