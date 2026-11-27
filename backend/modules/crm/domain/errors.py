"""Errores de dominio de prospectos y oportunidades (puro: sin Django)."""


class CrmValidationError(Exception):
    """Entrada inválida (400): `errors` es `{campo: [mensajes]}`."""

    def __init__(self, errors: dict[str, list[str]]):
        super().__init__(errors)
        self.errors = errors


class CrmNotFound(Exception):
    """Un id que no existe en la empresa (404): nunca se distingue «ajeno» de «inexistente»."""


class CrmConflict(Exception):
    """Regla de negocio que impide la operación (409): `code` y datos extra para el cliente."""

    def __init__(self, code: str, message: str, **extra):
        super().__init__(message)
        self.code, self.message, self.extra = code, message, extra
