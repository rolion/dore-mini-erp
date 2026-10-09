"""Validación de importes monetarios (Shared Kernel mínimo).

La moneda es única e implícita, así que no hay un value object con divisa: solo la regla común de que el dinero
es `Decimal` con hasta 2 decimales, nunca `float`.
"""
from decimal import Decimal, InvalidOperation

MONEY_MAX = Decimal('9999999999.99')
_CENTS = Decimal('0.01')

TYPE = 'type'
NEGATIVE = 'negative'
DECIMALS = 'decimals'
TOO_LARGE = 'too_large'


class InvalidMoney(ValueError):
    """El valor no es un importe válido; `code` indica el motivo (`type`, `negative`, `decimals`, `too_large`)."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def parse_money(value: object) -> Decimal:
    """Devuelve el importe como `Decimal` con 2 decimales, o lanza `InvalidMoney`.

    Acepta `Decimal`, `int` y `str`; rechaza `float` y `bool`. El rango es 0 … MONEY_MAX.
    """
    if isinstance(value, bool) or not isinstance(value, (Decimal, int, str)):
        raise InvalidMoney(TYPE)
    try:
        amount = Decimal(value.strip() if isinstance(value, str) else value)
    except InvalidOperation:
        raise InvalidMoney(TYPE) from None
    if not amount.is_finite():
        raise InvalidMoney(TYPE)
    if amount < 0:
        raise InvalidMoney(NEGATIVE)
    if amount != amount.quantize(_CENTS):
        raise InvalidMoney(DECIMALS)
    amount = amount.quantize(_CENTS)
    if amount > MONEY_MAX:
        raise InvalidMoney(TOO_LARGE)
    return amount
