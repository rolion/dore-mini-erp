"""Las seis clasificaciones contables fijas. Cada empresa solo las habilita o deshabilita (CONT-08)."""
from .account import AccountValidationError

ASSET = 'ASSET'
LIABILITY = 'LIABILITY'
EQUITY = 'EQUITY'
INCOME = 'INCOME'
EXPENSE = 'EXPENSE'
COST = 'COST'

# Orden fijo de presentación: no se crean, renombran ni borran.
ACCOUNT_CLASSES = (ASSET, LIABILITY, EQUITY, INCOME, EXPENSE, COST)


class AccountClassNotFound(Exception):
    pass


def parse_account_class(code: object) -> str:
    """Código del catálogo (sin distinguir mayúsculas) o `AccountClassNotFound`."""
    if isinstance(code, str) and code.strip().upper() in ACCOUNT_CLASSES:
        return code.strip().upper()
    raise AccountClassNotFound(str(code))


def validate_account_class(code: object) -> str:
    try:
        return parse_account_class(code)
    except AccountClassNotFound:
        raise AccountValidationError(
            {'account_class': [f'La clasificación contable debe ser una de: {", ".join(ACCOUNT_CLASSES)}.']}) from None


def ensure_enabled(code: str, disabled: frozenset[str]) -> None:
    """Valida un uso nuevo: la clasificación debe estar habilitada en la empresa."""
    if code in disabled:
        raise AccountValidationError({'account_class': ['La clasificación contable está deshabilitada.']})
