"""Normalización y lectura de valores del archivo (sin Django): nombres, fechas, números y sinónimos."""
import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation

from shared.domain.money import DECIMALS, NEGATIVE, TOO_LARGE, InvalidMoney, parse_money

QUANTITY_MAX = 100_000
_CONTROL = re.compile(r'[\x00-\x08\x0b-\x1f\x7f]')
_SPACES = re.compile(r'\s+')
_CURRENCY = re.compile(r'(?i)\b(bs\.?|bob|usd|us\$|\$)\s*')


class ValueProblem(ValueError):
    """El valor de una celda no es válido; `message` ya está listo para mostrarse."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def clean_text(value: object, max_length: int | None = None) -> str:
    """Texto sin caracteres de control, con espacios colapsados en los extremos y recortado al máximo."""
    text = _CONTROL.sub('', '' if value is None else str(value)).replace('\r', ' ').strip()
    return text[:max_length] if max_length else text


def normalize_name(value: object) -> str:
    """Clave de coincidencia: minúsculas, sin tildes y con espacios colapsados."""
    text = unicodedata.normalize('NFKD', clean_text(value))
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    return _SPACES.sub(' ', text).strip().lower()


def normalize_header(value: object) -> str:
    """Cabecera comparable: sin tildes, sin signos y con espacios simples."""
    text = re.sub(r'[^a-z0-9 ]+', ' ', normalize_name(value))
    return _SPACES.sub(' ', text).strip()


DATE_FORMATS = ('dmy', 'mdy', 'ymd')


def parse_date(raw: object, date_format: str = 'dmy') -> date:
    text = clean_text(raw)
    if not text:
        raise ValueProblem('required', 'La fecha de la venta es obligatoria.')
    iso = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})(?:[T ].*)?$', text)
    if iso:
        parts = (int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
    else:
        found = re.match(r'^(\d{1,4})[/\-.](\d{1,2})[/\-.](\d{1,4})(?:[T ].*)?$', text)
        if not found:
            raise ValueProblem('invalid_date', f'La fecha «{text}» no es válida.')
        a, b, c = (int(found.group(i)) for i in (1, 2, 3))
        if date_format == 'ymd':
            parts = (a, b, c)
        elif date_format == 'mdy':
            parts = (c, a, b)
        else:
            parts = (c, b, a)
    year, month, day = parts
    if year < 1900:
        raise ValueProblem('invalid_date', f'La fecha «{text}» no es válida (el año debe tener 4 dígitos).')
    try:
        return date(year, month, day)
    except ValueError:
        raise ValueProblem('invalid_date', f'La fecha «{text}» no es válida.') from None


def parse_decimal(raw: object) -> Decimal:
    """Número con coma o punto decimal y separadores de miles; ignora símbolos de moneda."""
    text = _CURRENCY.sub('', clean_text(raw)).replace(' ', '')
    if not text:
        raise ValueProblem('required', 'El valor es obligatorio.')
    if ',' in text and '.' in text:
        decimal_sep = ',' if text.rfind(',') > text.rfind('.') else '.'
        thousands = '.' if decimal_sep == ',' else ','
        text = text.replace(thousands, '').replace(decimal_sep, '.')
    elif ',' in text:
        head, _, tail = text.rpartition(',')
        if ',' in head or (len(tail) == 3 and head.lstrip('-').isdigit()):
            text = text.replace(',', '')  # «1,234» o «1,234,567»: separador de miles
        else:
            text = head + '.' + tail  # «12,50»: coma decimal
    elif text.count('.') > 1:
        text = text.replace('.', '')  # «1.234.567»
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise ValueProblem('invalid_number', f'«{clean_text(raw)}» no es un número.') from None
    if not value.is_finite():
        raise ValueProblem('invalid_number', f'«{clean_text(raw)}» no es un número.')
    return value


def parse_quantity(raw: object) -> int:
    value = parse_decimal(raw)
    if value != value.to_integral_value():
        raise ValueProblem('invalid_quantity', 'La cantidad debe ser un número entero.')
    quantity = int(value)
    if quantity <= 0:
        raise ValueProblem('invalid_quantity', 'La cantidad debe ser mayor a cero.')
    if quantity > QUANTITY_MAX:
        raise ValueProblem('invalid_quantity', f'La cantidad no puede superar {QUANTITY_MAX}.')
    return quantity


def parse_money_value(raw: object, label: str) -> Decimal:
    value = parse_decimal(raw)
    try:
        return parse_money(value)
    except InvalidMoney as exc:
        messages = {NEGATIVE: f'{label} no puede ser negativo.', DECIMALS: f'{label} admite como máximo 2 decimales.',
                    TOO_LARGE: f'{label} es demasiado grande.'}
        raise ValueProblem('invalid_amount', messages.get(exc.code, f'{label} no es válido.')) from None


_PAYMENT = {
    'CASH': ('efectivo', 'caja', 'cash', 'contado', 'dinheiro', 'efectivo caja'),
    'QR': ('qr', 'pago qr', 'codigo qr'),
    'BANK_TRANSFER': ('transferencia', 'transferencia bancaria', 'banco', 'deposito', 'bank transfer', 'transfer',
                      'transferencia banco'),
    'CARD': ('tarjeta', 'card', 'cartao', 'debito', 'credito', 'tarjeta debito', 'tarjeta credito'),
    'OTHER': ('otro', 'otros', 'other', 'outro'),
}
_CHANNEL = {
    'WHATSAPP': ('whatsapp', 'wsp', 'wa'),
    'FACEBOOK': ('facebook', 'fb'),
    'INSTAGRAM': ('instagram', 'ig'),
    'STORE': ('tienda', 'local', 'store', 'loja', 'mostrador'),
    'FAIR': ('feria', 'fair', 'feira'),
    'OTHER': ('otro', 'otros', 'other', 'outro'),
}


def _lookup(table: dict[str, tuple[str, ...]], raw: object) -> str | None:
    key = normalize_name(raw)
    for value, synonyms in table.items():
        if key == value.lower().replace('_', ' ') or key in synonyms:
            return value
    return None


def parse_payment_method(raw: object) -> str:
    value = _lookup(_PAYMENT, raw)
    if value is None:
        raise ValueProblem('invalid_payment_method',
                           f'El método de pago «{clean_text(raw)}» no se reconoce (efectivo/caja, QR, transferencia, '
                           'tarjeta u otro).')
    return value


def parse_sales_channel(raw: object) -> str:
    value = _lookup(_CHANNEL, raw)
    if value is None:
        raise ValueProblem('invalid_sales_channel', f'El canal «{clean_text(raw)}» no se reconoce.')
    return value
