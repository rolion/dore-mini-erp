"""Catálogo de ajustes por módulo y su validación (puro: sin Django).

Cada ajuste tiene un valor inicial documentado; sin valor guardado por la empresa rige ese valor. Solo existen
tipos `choice` y `percent`: no hay lugar para secretos ni credenciales.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

CHOICE = 'choice'
PERCENT = 'percent'
PERCENT_STEP = Decimal('0.01')
PERCENT_MIN = Decimal('0')
PERCENT_MAX = Decimal('100')
EMPTY_LABEL = 'Sin predeterminado'

# Valores y etiquetas de los enums de Sales (un test los compara con `modules.sales.domain.enums`).
SALES_CHANNELS: tuple[tuple[str, str], ...] = (
    ('WHATSAPP', 'WhatsApp'), ('FACEBOOK', 'Facebook'), ('INSTAGRAM', 'Instagram'),
    ('STORE', 'Venta directa'), ('FAIR', 'Feria'), ('OTHER', 'Otro'),
)
PAYMENT_METHODS: tuple[tuple[str, str], ...] = (
    ('CASH', 'Efectivo'), ('QR', 'QR'), ('BANK_TRANSFER', 'Transferencia'), ('CARD', 'Tarjeta'), ('OTHER', 'Otro'),
)


@dataclass(frozen=True)
class SettingDefinition:
    key: str
    module: str
    label: str
    description: str
    kind: str
    default: str
    choices: tuple[tuple[str, str], ...] = ()
    minimum: Decimal | None = None
    maximum: Decimal | None = None


SETTINGS_CATALOG: tuple[SettingDefinition, ...] = (
    SettingDefinition(
        'sales.default_sales_channel', 'sales', 'Canal de venta predeterminado',
        'Canal que se sugiere al crear un pedido nuevo. Se puede cambiar en cada pedido; no afecta pedidos existentes.',
        CHOICE, '', choices=SALES_CHANNELS),
    SettingDefinition(
        'sales.default_payment_method', 'sales', 'Método de pago predeterminado',
        'Método que se sugiere al registrar un pago. Se puede cambiar en cada pago; no afecta pagos existentes.',
        CHOICE, '', choices=PAYMENT_METHODS),
    SettingDefinition(
        'sales.max_discount_percent', 'sales', 'Descuento máximo (% del subtotal)',
        'Porcentaje máximo del subtotal que admite el descuento de un pedido. Aplica a los descuentos que se '
        'registren desde ahora; los pedidos existentes no cambian.',
        PERCENT, '100.00', minimum=PERCENT_MIN, maximum=PERCENT_MAX),
)
BY_SETTING_KEY: dict[str, SettingDefinition] = {s.key: s for s in SETTINGS_CATALOG}


class ModuleDisabled(Exception):
    """El módulo no está habilitado para la empresa: no admite cambiar sus ajustes."""


class SettingsValidationError(Exception):
    """Errores por clave de ajuste (`{key: [mensaje]}`); no se guarda nada."""

    def __init__(self, errors: dict[str, list[str]]):
        super().__init__(errors)
        self.errors = errors


def settings_for(module_key: str) -> list[SettingDefinition]:
    return [s for s in SETTINGS_CATALOG if s.module == module_key]


def validate(definition: SettingDefinition, raw: object) -> str:
    """Devuelve el valor normalizado (texto) o lanza `ValueError` con el mensaje para el campo."""
    if definition.kind == CHOICE:
        return _validate_choice(definition, raw)
    return _validate_percent(definition, raw)


def _validate_choice(definition: SettingDefinition, raw: object) -> str:
    if raw is None or raw == '':
        return ''
    if not isinstance(raw, str) or raw not in dict(definition.choices):
        raise ValueError('El valor elegido no es válido.')
    return raw


def _validate_percent(definition: SettingDefinition, raw: object) -> str:
    if isinstance(raw, bool) or raw is None or raw == '':
        raise ValueError('Ingrese un porcentaje.')
    try:
        value = Decimal(str(raw).strip())  # nunca `float`: se parsea desde su texto
    except InvalidOperation:
        raise ValueError('Ingrese un número válido.') from None
    if not value.is_finite():
        raise ValueError('Ingrese un número válido.')
    if value != value.quantize(PERCENT_STEP):
        raise ValueError('Admite como máximo 2 decimales.')
    if value < definition.minimum or value > definition.maximum:
        raise ValueError(f'Debe estar entre {definition.minimum} y {definition.maximum}.')
    return str(value.quantize(PERCENT_STEP))


def validate_all(definitions: list[SettingDefinition], raw: dict[str, object]) -> dict[str, str]:
    """Valida todo el lote; si algo falla lanza `SettingsValidationError` y no se guarda nada."""
    errors: dict[str, list[str]] = {}
    values: dict[str, str] = {}
    by_key = {d.key: d for d in definitions}
    for key, value in raw.items():
        definition = by_key.get(key)
        if definition is None:
            errors[key] = ['Ajuste desconocido.']
            continue
        try:
            values[key] = validate(definition, value)
        except ValueError as exc:
            errors[key] = [str(exc)]
    if errors:
        raise SettingsValidationError(errors)
    return values


def display(definition: SettingDefinition, stored: str) -> str:
    """Texto presentable del valor guardado (el que se escribe en el historial)."""
    if definition.kind == CHOICE:
        return dict(definition.choices).get(stored, EMPTY_LABEL if stored == '' else stored)
    return f'{stored} %'
