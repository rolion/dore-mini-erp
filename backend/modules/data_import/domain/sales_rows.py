"""De filas del archivo a ventas: validación por celda, agrupación por n.º de venta y clave de idempotencia."""
import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from .errors import RowProblem
from .fields import ImportOptions
from .normalize import (
    ValueProblem,
    clean_text,
    normalize_name,
    parse_date,
    parse_money_value,
    parse_payment_method,
    parse_quantity,
    parse_sales_channel,
)

NAME_MAX = 200
NOTES_MAX = 500


@dataclass(frozen=True)
class SaleLine:
    row: int
    product_name: str
    product_key: str
    quantity: int
    unit_price: Decimal
    unit_cost: Decimal | None
    supplier_name: str

    @property
    def subtotal(self) -> Decimal:
        return (self.unit_price * self.quantity).quantize(Decimal('0.01'))


@dataclass(frozen=True)
class SaleGroup:
    key: str  # clave de idempotencia (`n:<n.º de venta>` o `h:<hash>:<ocurrencia>`)
    number: str
    first_row: int
    sale_date: date
    customer_name: str
    customer_key: str
    payment_method: str
    sales_channel: str
    notes: str
    lines: tuple[SaleLine, ...]

    @property
    def total(self) -> Decimal:
        return sum((line.subtotal for line in self.lines), Decimal('0.00'))

    @property
    def rows(self) -> tuple[int, ...]:
        return tuple(line.row for line in self.lines)


@dataclass
class ParsedSales:
    groups: list[SaleGroup] = field(default_factory=list)
    problems: list[RowProblem] = field(default_factory=list)
    rows_total: int = 0
    lines_total: int = 0
    invalid_sales: int = 0


@dataclass
class _Row:
    row: int
    number: str
    values: dict[str, object]
    problems: list[RowProblem]
    key: str = ''


def _cell(headers_index: dict[str, int], row: list[str], column: str | None) -> str:
    if column is None:
        return ''
    index = headers_index[column]
    return clean_text(row[index]) if index < len(row) else ''


def _hash_key(values: dict[str, object], seen: dict[str, int]) -> str:
    payload = json.dumps([str(values['date']), values['product_key'], values['quantity'], str(values['unit_price']),
                          values['customer_key']], sort_keys=True)  # sin valores por defecto: no cambian la clave
    digest = hashlib.sha256(payload.encode('utf-8')).hexdigest()
    seen[digest] = seen.get(digest, 0) + 1
    return f'h:{digest}:{seen[digest]}'


def parse_sales(headers: list[str], rows: list[list[str]], mapping: dict[str, str | None], options: ImportOptions,
                today: date) -> ParsedSales:
    index = {header: i for i, header in enumerate(headers)}
    result = ParsedSales()
    parsed: list[_Row] = []
    seen_hashes: dict[str, int] = {}
    for position, raw in enumerate(rows, start=1):
        if not any(clean_text(c) for c in raw):
            continue
        result.rows_total += 1
        get = lambda f: _cell(index, raw, mapping.get(f))  # noqa: E731
        number = clean_text(get('sale_number'), NAME_MAX)
        number_key = normalize_name(number)
        base_key = f'n:{number_key}' if number_key else f'row:{position}'
        problems: list[RowProblem] = []
        values: dict[str, object] = {}

        def check(field_name: str, action, key: str = '', _p=position, _bk=base_key) -> None:
            try:
                values[key or field_name] = action()
            except ValueProblem as exc:
                problems.append(RowProblem(_p, _bk, field_name, exc.code, exc.message))

        def sale_date() -> date:
            value = parse_date(get('sale_date'), options.date_format)
            if value > today:
                raise ValueProblem('future_date', 'La fecha de la venta no puede ser futura.')
            return value

        def product() -> str:
            name = get('product_name')
            if not name:
                raise ValueProblem('required', 'El producto es obligatorio.')
            return clean_text(name, NAME_MAX)

        def optional(parser, field_name: str, default: str) -> str:
            raw_value = get(field_name)
            return parser(raw_value) if raw_value else default

        check('sale_date', sale_date, 'date')
        check('product_name', product, 'product_name')
        check('quantity', lambda: parse_quantity(get('quantity')), 'quantity')
        check('unit_price', lambda: parse_money_value(get('unit_price'), 'El precio unitario'), 'unit_price')
        check('payment_method', lambda: optional(
            parse_payment_method, 'payment_method', options.default_payment_method), 'method')
        check('sales_channel', lambda: optional(
            parse_sales_channel, 'sales_channel', options.default_sales_channel), 'channel')
        cost_raw = get('unit_cost')
        if cost_raw:
            check('unit_cost', lambda: parse_money_value(cost_raw, 'El costo unitario'), 'unit_cost')
        else:
            values['unit_cost'] = None
        values['supplier_name'] = clean_text(get('supplier_name'), NAME_MAX)
        values['customer_name'] = clean_text(get('customer_name'), NAME_MAX)
        values['customer_key'] = normalize_name(values['customer_name'])
        values['product_key'] = normalize_name(values.get('product_name', ''))
        values['notes'] = clean_text(get('notes'), NOTES_MAX)
        row = _Row(position, number, values, problems)
        if number_key:
            row.key = base_key
        elif not problems:
            row.key = _hash_key(values, seen_hashes)
        else:
            row.key = base_key
        parsed.append(row)

    by_key: dict[str, list[_Row]] = {}
    for row in parsed:
        by_key.setdefault(row.key, []).append(row)
    for key, members in by_key.items():
        _check_consistency(key, members)
        problems = [p for member in members for p in member.problems]
        result.problems.extend(problems)
        result.lines_total += len(members)
        if problems:
            result.invalid_sales += 1
            continue
        first = members[0]
        result.groups.append(SaleGroup(
            key=key, number=first.number, first_row=first.row, sale_date=first.values['date'],
            customer_name=str(first.values['customer_name']), customer_key=str(first.values['customer_key']),
            payment_method=str(first.values['method']), sales_channel=str(first.values['channel']),
            notes=str(first.values['notes']),
            lines=tuple(SaleLine(
                row=m.row, product_name=str(m.values['product_name']), product_key=str(m.values['product_key']),
                quantity=int(m.values['quantity']), unit_price=m.values['unit_price'],
                unit_cost=m.values['unit_cost'], supplier_name=str(m.values['supplier_name'])) for m in members)))
    result.problems.sort(key=lambda p: (p.row, p.field))
    result.groups.sort(key=lambda g: (g.sale_date, g.first_row))
    return result


_CONSISTENT = (('date', 'sale_date', 'la fecha'), ('customer_key', 'customer_name', 'el cliente'),
               ('method', 'payment_method', 'el método de pago'), ('channel', 'sales_channel', 'el canal'))


def _check_consistency(key: str, members: list[_Row]) -> None:
    """Las líneas de una misma venta deben coincidir en fecha, cliente, método de pago y canal."""
    first = members[0]
    if len(members) == 1 or first.problems:
        return
    for other in members[1:]:
        for value_key, field_name, label in _CONSISTENT:
            if value_key in other.values and value_key in first.values and other.values[value_key] != first.values[
                    value_key]:
                other.problems.append(RowProblem(
                    other.row, key, field_name, 'sale_inconsistent',
                    f'Las líneas de una misma venta deben tener {label} igual (fila {first.row}).'))
