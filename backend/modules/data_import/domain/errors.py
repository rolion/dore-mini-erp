from dataclasses import dataclass


@dataclass(frozen=True)
class RowProblem:
    """Un problema atribuible a una fila del archivo (n.º de fila de datos, empezando en 1)."""

    row: int
    sale_key: str
    field: str
    code: str
    message: str

    def as_dict(self) -> dict[str, object]:
        return {'row': self.row, 'sale_key': self.sale_key, 'field': self.field, 'code': self.code,
                'message': self.message}


class ImportValidationError(Exception):
    """Archivo, mapeo u opciones inválidos; `errors` mapea campo -> mensajes (400)."""

    def __init__(self, errors: dict[str, list[str]]):
        super().__init__(errors)
        self.errors = errors


class ImportRuleViolation(Exception):
    """La importación no admite la acción en su estado actual (409); `code` estable."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class ImportNotFound(Exception):
    pass
