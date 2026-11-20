"""Rechazo común de las fachadas de escritura que usa la importación de datos.

Cada módulo traduce sus errores de dominio a `ImportRejected` para que `data_import` los muestre por fila sin
conocer las excepciones internas de otros módulos.
"""


class ImportRejected(Exception):
    """Una operación de importación fue rechazada por las reglas del módulo dueño."""

    def __init__(self, code: str, message: str, field: str = ''):
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field


def first_error(errors: object) -> tuple[str, str]:
    """`(campo, mensaje)` del primer error de un `dict` de errores de validación de dominio."""
    if isinstance(errors, dict):
        for field, value in errors.items():
            if isinstance(value, (list, tuple)) and value:
                first = value[0]
                return str(field), str(first if not isinstance(first, dict) else next(iter(first.values()), ''))
            if isinstance(value, str):
                return str(field), value
    return '', str(errors)
