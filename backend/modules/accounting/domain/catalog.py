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

# Tipos de cuenta de dinero (dónde se mueve el dinero). Distintos del método de pago (cómo se paga).
ACCOUNT_KIND_LABELS: dict[str, str] = {'CASH': 'Caja', 'BANK': 'Banco', 'WALLET': 'Billetera'}
ACCOUNT_KINDS: tuple[str, ...] = tuple(ACCOUNT_KIND_LABELS)

# Dirección de una clasificación (por qué se mueve el dinero).
DIRECTION_LABELS: dict[str, str] = {'INCOME': 'Ingreso', 'EXPENSE': 'Egreso'}
DIRECTIONS: tuple[str, ...] = tuple(DIRECTION_LABELS)

# Orígenes de una entrada: el tipo de pago que la genera (productos = pago de pedido; servicios = pago de proforma).
ORIGIN_LABELS: dict[str, str] = {'PRODUCT': 'Productos', 'SERVICE': 'Servicios'}
ORIGIN_KINDS: tuple[str, ...] = tuple(ORIGIN_LABELS)

# Orígenes que generan egresos (Gastos y pagos de Compras) y catálogo completo del libro. `ORIGIN_KINDS` sigue siendo
# solo el de los cobros: lo usan la regularización de pagos históricos y el desglose `by_origin` de los totales.
EXPENSE_ORIGIN_LABELS: dict[str, str] = {'EXPENSE': 'Gastos', 'PURCHASE_PAYMENT': 'Pagos de compras'}
ENTRY_ORIGIN_LABELS: dict[str, str] = {**ORIGIN_LABELS, **EXPENSE_ORIGIN_LABELS}
ENTRY_ORIGIN_KINDS: tuple[str, ...] = tuple(ENTRY_ORIGIN_LABELS)
# La dirección la deriva el origen: no se puede registrar un gasto como ingreso.
ORIGIN_DIRECTION: dict[str, str] = {**{kind: 'INCOME' for kind in ORIGIN_LABELS},
                                    **{kind: 'EXPENSE' for kind in EXPENSE_ORIGIN_LABELS}}

# Operación de una entrada: el registro original o su reversión (movimiento opuesto vinculado).
OPERATION_RECORD = 'RECORD'
OPERATION_REVERSAL = 'REVERSAL'
OPERATIONS: tuple[str, ...] = (OPERATION_RECORD, OPERATION_REVERSAL)
