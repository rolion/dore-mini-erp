"""Catálogo de métodos de pago y monedas de Contabilidad (puro: sin Django).

Los códigos de método son los mismos que usan Ventas (`sales.domain.enums.PaymentMethod`) y Cobros
(`receivables.domain.obligation.PaymentMethod`); un test comprueba la correspondencia por código.
"""
PAYMENT_METHODS: tuple[tuple[str, str], ...] = (
    ('CASH', 'Efectivo'), ('QR', 'QR'), ('BANK_TRANSFER', 'Transferencia'), ('CARD', 'Tarjeta'), ('OTHER', 'Otro'),
)
METHOD_LABELS: dict[str, str] = dict(PAYMENT_METHODS)
METHOD_CODES: tuple[str, ...] = tuple(code for code, _ in PAYMENT_METHODS)

# Moneda de los flujos de cobro (Ventas y Cobros trabajan en bolivianos).
FLOW_CURRENCY = 'BOB'
CURRENCIES: tuple[str, ...] = ('BOB', 'USD')

# Orígenes de una entrada: el tipo de pago que la genera (productos = pago de pedido; servicios = pago de proforma).
ORIGIN_LABELS: dict[str, str] = {'PRODUCT': 'Productos', 'SERVICE': 'Servicios'}
ORIGIN_KINDS: tuple[str, ...] = tuple(ORIGIN_LABELS)
