"""Campos de destino de la importación de ventas, sus sinónimos de cabecera y las opciones del asistente."""
from dataclasses import dataclass

from .errors import ImportValidationError
from .normalize import DATE_FORMATS, normalize_header

REQUIRED_FIELDS = ('sale_date', 'product_name', 'quantity', 'unit_price')
OPTIONAL_FIELDS = ('sale_number', 'customer_name', 'payment_method', 'sales_channel', 'supplier_name', 'unit_cost',
                   'discount', 'notes')
TARGET_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS

PAYMENT_METHODS = ('CASH', 'QR', 'BANK_TRANSFER', 'CARD', 'OTHER')
SALES_CHANNELS = ('WHATSAPP', 'FACEBOOK', 'INSTAGRAM', 'STORE', 'FAIR', 'OTHER')

_SYNONYMS: dict[str, tuple[str, ...]] = {
    'sale_date': ('fecha', 'fecha venta', 'fecha de venta', 'fecha de la venta', 'date', 'sale date', 'data',
                  'data da venda', 'data venda'),
    'product_name': ('producto', 'nombre producto', 'nombre del producto', 'articulo', 'item', 'product',
                     'product name', 'produto', 'nome do produto', 'descripcion'),
    'quantity': ('cantidad', 'cant', 'qty', 'quantity', 'unidades', 'quantidade', 'qtd'),
    'unit_price': ('precio', 'precio unitario', 'precio venta', 'precio de venta', 'price', 'unit price', 'preco',
                   'preco unitario', 'pu'),
    'sale_number': ('numero venta', 'n venta', 'nro venta', 'nro', 'numero', 'factura', 'pedido', 'order',
                    'order number', 'ticket', 'id venta', 'n de venta', 'numero de venta', 'venta', 'numero pedido'),
    'customer_name': ('cliente', 'nombre cliente', 'nombre del cliente', 'customer', 'client', 'customer name'),
    'payment_method': ('metodo pago', 'metodo de pago', 'forma de pago', 'pago', 'payment method', 'payment',
                       'forma de pagamento'),
    'sales_channel': ('canal', 'canal venta', 'canal de venta', 'channel', 'sales channel', 'canal de vendas'),
    'supplier_name': ('proveedor', 'supplier', 'fornecedor', 'nombre proveedor'),
    'unit_cost': ('costo', 'costo unitario', 'cost', 'unit cost', 'custo', 'custo unitario', 'costo compra'),
    'discount': ('descuento', 'discount', 'desconto', 'rebaja', 'dto'),
    'notes': ('notas', 'nota', 'observaciones', 'observacion', 'notes', 'comentario', 'comentarios'),
}


def suggest_mapping(headers: list[str]) -> dict[str, str | None]:
    """Sugiere qué columna corresponde a cada campo por sus cabeceras comunes (cada columna se usa una vez)."""
    normalized = {header: normalize_header(header) for header in headers}
    used: set[str] = set()
    mapping: dict[str, str | None] = {}
    for field in TARGET_FIELDS:
        choice = None
        for synonym in _SYNONYMS[field]:
            choice = next((h for h, n in normalized.items() if n == synonym and h not in used), None)
            if choice is not None:
                break
        mapping[field] = choice
        if choice is not None:
            used.add(choice)
    return mapping


def validate_mapping(raw: object, headers: list[str]) -> dict[str, str | None]:
    """Mapeo `campo -> columna|None` válido: campos conocidos, columnas existentes, obligatorios presentes."""
    errors: dict[str, list[str]] = {}
    if not isinstance(raw, dict):
        raise ImportValidationError({'mapping': ['El mapeo es obligatorio.']})
    mapping: dict[str, str | None] = {}
    for field in TARGET_FIELDS:
        column = raw.get(field)
        if column in (None, ''):
            mapping[field] = None
            continue
        if not isinstance(column, str) or column not in headers:
            errors[f'mapping.{field}'] = ['La columna elegida no existe en el archivo.']
            continue
        mapping[field] = column
    unknown = [key for key in raw if key not in TARGET_FIELDS]
    if unknown:
        errors['mapping'] = ['Hay campos de destino desconocidos: ' + ', '.join(sorted(map(str, unknown))) + '.']
    for field in REQUIRED_FIELDS:
        if mapping.get(field) is None and f'mapping.{field}' not in errors:
            errors[f'mapping.{field}'] = ['Este campo es obligatorio: elige la columna del archivo.']
    chosen = [c for c in mapping.values() if c is not None]
    if len(chosen) != len(set(chosen)):
        errors['mapping'] = errors.get('mapping', []) + ['Una misma columna no puede asignarse a dos campos.']
    if errors:
        raise ImportValidationError(errors)
    return mapping


@dataclass(frozen=True)
class ImportOptions:
    infer_products: bool
    infer_customers: bool
    infer_inventory: bool
    infer_accounting: bool
    default_payment_method: str
    default_sales_channel: str
    warehouse_id: str | None
    date_format: str

    def as_dict(self) -> dict[str, object]:
        return {'infer_products': self.infer_products, 'infer_customers': self.infer_customers,
                'infer_inventory': self.infer_inventory, 'infer_accounting': self.infer_accounting,
                'default_payment_method': self.default_payment_method,
                'default_sales_channel': self.default_sales_channel, 'warehouse_id': self.warehouse_id,
                'date_format': self.date_format}


def parse_options(raw: object) -> ImportOptions:
    errors: dict[str, list[str]] = {}
    data = raw if isinstance(raw, dict) else {}
    flags = {}
    for key in ('infer_products', 'infer_customers', 'infer_inventory', 'infer_accounting'):
        value = data.get(key, False)
        if not isinstance(value, bool):
            errors[f'options.{key}'] = ['Debe ser verdadero o falso.']
        flags[key] = value is True
    method = data.get('default_payment_method') or 'CASH'
    if method not in PAYMENT_METHODS:
        errors['options.default_payment_method'] = ['El método de pago no es válido.']
    channel = data.get('default_sales_channel') or 'OTHER'
    if channel not in SALES_CHANNELS:
        errors['options.default_sales_channel'] = ['El canal de venta no es válido.']
    date_format = data.get('date_format') or 'dmy'
    if date_format not in DATE_FORMATS:
        errors['options.date_format'] = ['El formato de fecha no es válido.']
    warehouse = data.get('warehouse_id') or None
    if warehouse is not None and not isinstance(warehouse, str):
        errors['options.warehouse_id'] = ['El almacén no es válido.']
    if errors:
        raise ImportValidationError(errors)
    return ImportOptions(default_payment_method=method, default_sales_channel=channel, warehouse_id=warehouse,
                         date_format=date_format, **flags)
