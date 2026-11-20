"""Casos de uso de la importación de ventas: subir, previsualizar (sin escribir) y ejecutar por venta."""
import hashlib
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from modules.data_import.domain.errors import ImportNotFound, ImportRuleViolation, ImportValidationError, RowProblem
from modules.data_import.domain.fields import ImportOptions, parse_options, suggest_mapping, validate_mapping
from modules.data_import.domain.normalize import normalize_name
from modules.data_import.domain.sales_rows import SaleGroup, SaleLine, parse_sales
from shared.import_errors import ImportRejected

from .ports import (
    Capabilities,
    Clock,
    DuplicateSale,
    ImportRepository,
    ProductRef,
    RunData,
    SaleLineInput,
    SalesImportGateway,
)

logger = logging.getLogger(__name__)

DEFAULT_SUPPLIER = 'Importación'
MAX_PROBLEMS = 200
STATUS_CREATED = 'CREATED'
STATUS_DUPLICATE = 'SKIPPED_DUPLICATE'
STATUS_FAILED = 'FAILED'
STATUS_WITHOUT_POSTING = 'CREATED_WITHOUT_POSTING'


def signature(mapping: dict, options: dict) -> str:
    """Huella del mapeo y las opciones: la ejecución exige que coincida con la de la vista previa."""
    return hashlib.sha256(json.dumps([mapping, options], sort_keys=True, default=str).encode()).hexdigest()


def _check_capabilities(options: ImportOptions, caps: Capabilities) -> None:
    errors: dict[str, list[str]] = {}
    if options.infer_customers and not caps.customers:
        errors['options.infer_customers'] = ['Habilita el módulo Clientes para inferir clientes.']
    if options.infer_inventory and not (caps.inventory and caps.purchases):
        errors['options.infer_inventory'] = ['Habilita los módulos Inventario y Compras para inferir inventario.']
    if options.infer_accounting and not caps.accounting:
        errors['options.infer_accounting'] = ['Habilita el módulo Contabilidad para inferir movimientos contables.']
    if errors:
        raise ImportValidationError(errors)


def _resolve_warehouse(options: ImportOptions, caps: Capabilities) -> UUID | None:
    """Almacén de salida/entrada: el elegido (válido), o el único activo / el predeterminado."""
    if not caps.inventory:
        return None
    if options.warehouse_id:
        for warehouse in caps.warehouses:
            if str(warehouse.id) == options.warehouse_id:
                return warehouse.id
        raise ImportValidationError({'options.warehouse_id': ['El almacén no existe o está inactivo.']})
    if len(caps.warehouses) == 1:
        return caps.warehouses[0].id
    return next((w.id for w in caps.warehouses if w.is_default), None)


@dataclass
class UploadResult:
    run: RunData
    suggested_mapping: dict
    capabilities: Capabilities


class UploadSalesFile:
    def __init__(self, repository: ImportRepository, gateway: SalesImportGateway,
                 parser: Callable[[str, bytes], object]):
        self.repository = repository
        self.gateway = gateway
        self.parser = parser

    def execute(self, filename: str, content: bytes, user_id: UUID | None, user_name: str) -> UploadResult:
        parsed = self.parser(filename, content)
        run = self.repository.create_run(filename, hashlib.sha256(content).hexdigest(), parsed.headers, parsed.rows,
                                         user_id, user_name)
        return UploadResult(run, suggest_mapping(parsed.headers), self.gateway.capabilities())


@dataclass
class PreviewResult:
    sales_total: int = 0
    lines_total: int = 0
    to_create: int = 0
    already_imported: int = 0
    with_errors: int = 0
    new_products: int = 0
    existing_products: int = 0
    new_customers: int = 0
    existing_customers: int = 0
    purchases_to_create: int = 0
    units_to_buy: int = 0
    without_posting: int = 0
    problems: list[RowProblem] = field(default_factory=list)
    problems_total: int = 0

    def as_dict(self) -> dict[str, object]:
        data = {k: v for k, v in self.__dict__.items() if k != 'problems'}
        data['problems'] = [p.as_dict() for p in self.problems[:MAX_PROBLEMS]]
        return data


def _load_run(repository: ImportRepository, run_id: UUID) -> RunData:
    run = repository.get_run(run_id)
    if run is None:
        raise ImportNotFound(run_id)
    return run


class _Planner:
    """Reglas compartidas por la vista previa (solo lectura) y la ejecución: qué hace falta para cada venta."""

    def __init__(self, gateway: SalesImportGateway, options: ImportOptions, caps: Capabilities):
        self.gateway = gateway
        self.options = options
        self.caps = caps

    def controls_stock(self, product: ProductRef | None) -> bool:
        if not self.caps.inventory:
            return False
        if product is None:  # producto que se crearía
            return self.options.infer_products and self.options.infer_inventory
        return product.tracks_stock

    def shortfall(self, balance: Decimal, need: int) -> int:
        return max(0, need - int(balance)) if self.options.infer_inventory and self.caps.purchases else 0

    def unit_cost(self, line_costs: list[Decimal | None], product: ProductRef | None) -> Decimal | None:
        explicit = next((c for c in line_costs if c is not None), None)
        if explicit is not None:
            return explicit
        return self.gateway.average_cost(product.id) if product is not None else None


class PreviewSalesImport:
    """Valida todo sin escribir en ningún módulo (AC-06); el servidor revalida al ejecutar."""

    def __init__(self, repository: ImportRepository, gateway: SalesImportGateway, clock: Clock):
        self.repository = repository
        self.gateway = gateway
        self.clock = clock

    def execute(self, run_id: UUID, mapping: object, options: object) -> PreviewResult:
        run = _load_run(self.repository, run_id)
        if run.status == 'RUNNING':
            raise ImportRuleViolation('import_running', 'La importación está en curso.')
        clean_mapping = validate_mapping(mapping, run.headers)
        opts = parse_options(options)
        caps = self.gateway.capabilities()
        _check_capabilities(opts, caps)
        warehouse_id = _resolve_warehouse(opts, caps)
        parsed = parse_sales(run.headers, run.rows, clean_mapping, opts, self.clock.today())
        result = PreviewResult(sales_total=len(parsed.groups) + parsed.invalid_sales, lines_total=parsed.lines_total,
                               with_errors=parsed.invalid_sales, problems=list(parsed.problems),
                               problems_total=len(parsed.problems))
        duplicates = self.repository.existing_keys([g.key for g in parsed.groups])
        planner = _Planner(self.gateway, opts, caps)
        self._simulate(parsed.groups, duplicates, planner, warehouse_id, result)
        result.problems.sort(key=lambda p: (p.row, p.field))
        result.problems_total = len(result.problems)
        self.repository.save_preview(run_id, clean_mapping, opts.as_dict(), signature(clean_mapping, opts.as_dict()))
        return result

    def _simulate(self, groups: list[SaleGroup], duplicates: set[str], planner: _Planner, warehouse_id: UUID | None,
                  result: PreviewResult) -> None:
        opts, caps, gateway = planner.options, planner.caps, planner.gateway
        balances: dict[str, Decimal] = {}  # saldo proyectado por producto, en orden cronológico
        seen_products: set[str] = set()
        seen_customers: set[str] = set()
        warehouse_flagged = False
        allow_negative = gateway.allow_negative_stock() if caps.inventory else True
        for group in groups:
            if group.key in duplicates:
                result.already_imported += 1
                continue
            problems: list[RowProblem] = []

            def problem(line_row: int, field_name: str, code: str, message: str, _g=group, _p=problems) -> None:
                _p.append(RowProblem(line_row, _g.key, field_name, code, message))

            products = self._check_products(group, opts, problem)
            customer = self._check_customer(group, opts, caps, problem)
            staged, purchases, units = self._simulate_stock(group, products, planner, warehouse_id, balances,
                                                            allow_negative, problem)
            if warehouse_id is None and not warehouse_flagged and any(
                    planner.controls_stock(p) for p in products.values()):
                warehouse_flagged = True
                problem(group.first_row, 'warehouse_id', 'warehouse_required',
                        'Elige el almacén de salida: hay productos con control de stock.')
            if problems:
                result.with_errors += 1
                result.problems.extend(problems)
                continue
            balances.update(staged)
            result.to_create += 1
            result.purchases_to_create += purchases
            result.units_to_buy += units
            for key, product in products.items():
                if key not in seen_products:
                    seen_products.add(key)
                    result.existing_products += product is not None
                    result.new_products += product is None
            if group.customer_name and caps.customers and group.customer_key not in seen_customers:
                seen_customers.add(group.customer_key)
                result.existing_customers += customer is not None
                result.new_customers += customer is None
            if opts.infer_accounting and caps.accounting and not gateway.is_covered(group.sale_date):
                result.without_posting += 1

    def _check_products(self, group: SaleGroup, opts: ImportOptions, problem) -> dict[str, ProductRef | None]:
        products: dict[str, ProductRef | None] = {}
        for line in group.lines:
            if line.product_key in products:
                continue
            product = self.gateway.find_product(line.product_key)
            products[line.product_key] = product
            if product is None:
                if not opts.infer_products:
                    problem(line.row, 'product_name', 'product_missing',
                            f'El producto «{line.product_name}» no existe. Marca «Inferir productos» o créalo.')
            elif not product.active or not product.can_sell:
                problem(line.row, 'product_name', 'product_not_sellable',
                        f'El producto «{product.name}» está inactivo o no se puede vender.')
        return products

    def _check_customer(self, group: SaleGroup, opts: ImportOptions, caps: Capabilities, problem):
        if not (group.customer_name and caps.customers):
            return None
        customer = self.gateway.find_customer(group.customer_key)
        if customer is None and not opts.infer_customers:
            problem(group.first_row, 'customer_name', 'customer_missing',
                    f'El cliente «{group.customer_name}» no existe. Marca «Inferir clientes» o créalo.')
        elif customer is not None and not customer.active:
            problem(group.first_row, 'customer_name', 'customer_inactive',
                    f'El cliente «{customer.name}» está inactivo.')
        return customer

    def _simulate_stock(self, group: SaleGroup, products: dict[str, ProductRef | None], planner: _Planner,
                        warehouse_id: UUID | None, balances: dict[str, Decimal], allow_negative: bool, problem):
        """Devuelve `(saldos proyectados, compras a crear, unidades a comprar)` de la venta."""
        staged: dict[str, Decimal] = {}
        if warehouse_id is None:
            return staged, 0, 0
        needs: dict[str, int] = {}
        for line in group.lines:
            needs[line.product_key] = needs.get(line.product_key, 0) + line.quantity
        suppliers: set[str] = set()
        units = 0
        for key, need in needs.items():
            product = products.get(key)
            if not planner.controls_stock(product):
                continue
            lines = [line for line in group.lines if line.product_key == key]
            balance = balances.get(key)
            if balance is None:
                balance = (planner.gateway.stock_balance(warehouse_id, product.id) if product is not None
                           else Decimal('0'))
            short = planner.shortfall(balance, need)
            if short > 0:
                cost = planner.unit_cost([line.unit_cost for line in lines], product)
                if cost is None:
                    problem(lines[0].row, 'unit_cost', 'cost_missing',
                            f'Falta el costo unitario de «{lines[0].product_name}» para crear la compra por el '
                            'faltante de stock: agrega la columna de costo o registra una compra antes.')
                elif product is not None and not product.can_buy:
                    problem(lines[0].row, 'product_name', 'product_not_buyable',
                            f'El producto «{product.name}» no está habilitado para compra.')
                suppliers.add(normalize_name(lines[0].supplier_name or DEFAULT_SUPPLIER))
                balance += short
                units += short
            elif balance - need < 0 and not allow_negative and not planner.options.infer_inventory:
                problem(lines[0].row, 'quantity', 'insufficient_stock',
                        f'Stock insuficiente de «{lines[0].product_name}»: hay {int(balance)} y se venden {need}.')
            staged[key] = balance - need
        return staged, len(suppliers), units


class ExecuteSalesImport:
    """Carga cada venta en su propia transacción (INV-04), en orden cronológico e idempotente (INV-05)."""

    def __init__(self, repository: ImportRepository, gateway: SalesImportGateway, clock: Clock):
        self.repository = repository
        self.gateway = gateway
        self.clock = clock

    def execute(self, run_id: UUID, mapping: object, options: object, idempotency_key: UUID | None) -> RunData:
        run = _load_run(self.repository, run_id)
        if run.status == 'COMPLETED':
            return run  # idempotente: devuelve el resultado ya guardado
        if run.status == 'RUNNING':
            raise ImportRuleViolation('import_running', 'La importación ya está en curso.')
        clean_mapping = validate_mapping(mapping, run.headers)
        opts = parse_options(options)
        if not run.preview_signature:
            raise ImportRuleViolation('preview_required', 'Previsualiza la importación antes de cargarla.')
        if signature(clean_mapping, opts.as_dict()) != run.preview_signature:
            raise ImportRuleViolation('preview_stale',
                                      'El mapeo u opciones cambiaron desde la vista previa: vuelve a previsualizar.')
        caps = self.gateway.capabilities()
        _check_capabilities(opts, caps)
        warehouse_id = _resolve_warehouse(opts, caps)
        parsed = parse_sales(run.headers, run.rows, clean_mapping, opts, self.clock.today())
        self.repository.claim(run_id, idempotency_key, self.clock.now())
        counts = {'created': 0, 'skipped': 0, 'failed': 0, 'without_posting': 0}
        try:
            self._report_invalid(run_id, parsed, counts)
            duplicates = self.repository.existing_keys([g.key for g in parsed.groups])
            planner = _Planner(self.gateway, opts, caps)
            for group in parsed.groups:
                self.repository.heartbeat(run_id, self.clock.now())
                if group.key in duplicates:
                    self._duplicate(run_id, group, counts)
                    continue
                self._load_sale(run_id, group, opts, planner, warehouse_id, counts)
        except Exception:
            self.repository.finish(run_id, 'FAILED', counts, self.clock.now())
            raise
        self.repository.finish(run_id, 'COMPLETED', counts, self.clock.now())
        return _load_run(self.repository, run_id)

    def _report_invalid(self, run_id: UUID, parsed, counts: dict) -> None:
        by_sale: dict[str, list[RowProblem]] = {}
        for problem in parsed.problems:
            by_sale.setdefault(problem.sale_key, []).append(problem)
        for key, problems in by_sale.items():
            first = problems[0]
            self.repository.add_result(run_id, first.row, key, STATUS_FAILED, first.code,
                                       ' · '.join(p.message for p in problems[:3]), None, {})
            counts['failed'] += 1

    def _duplicate(self, run_id: UUID, group: SaleGroup, counts: dict) -> None:
        self.repository.add_result(run_id, group.first_row, group.key, STATUS_DUPLICATE, 'already_imported',
                                   'Esta venta ya fue importada antes.', None, {})
        counts['skipped'] += 1

    def _fail(self, run_id: UUID, group: SaleGroup, code: str, message: str, counts: dict) -> None:
        self.gateway.reset_cache()
        self.repository.add_result(run_id, group.first_row, group.key, STATUS_FAILED, code, message, None, {})
        counts['failed'] += 1

    def _load_sale(self, run_id: UUID, group: SaleGroup, opts: ImportOptions, planner: _Planner,
                   warehouse_id: UUID | None, counts: dict) -> None:
        gateway = self.gateway
        refs: dict[str, object] = {'purchase_ids': [], 'product_ids': [], 'customer_id': None}
        try:
            with gateway.atomic():
                outcome = self._build_sale(run_id, group, opts, planner, warehouse_id, refs)
        except DuplicateSale:
            self.gateway.reset_cache()
            self._duplicate(run_id, group, counts)
            return
        except ImportRejected as exc:
            self._fail(run_id, group, exc.code, exc.message, counts)
            return
        except Exception:
            logger.exception('Error inesperado al importar la venta %s', group.key)
            self._fail(run_id, group, 'unexpected_error',
                       'Ocurrió un error inesperado al cargar esta venta; no se guardó nada de ella.', counts)
            return
        without = outcome.without_posting and opts.infer_accounting and planner.caps.accounting
        status = STATUS_WITHOUT_POSTING if without else STATUS_CREATED
        message = ('Cargada sin asiento: la fecha no tiene cobertura contable.' if without else '')
        self.repository.add_result(run_id, group.first_row, group.key, status, '', message, outcome.order_id, refs)
        counts['created'] += 1
        if without:
            counts['without_posting'] += 1

    def _build_sale(self, run_id: UUID, group: SaleGroup, opts: ImportOptions, planner: _Planner,
                    warehouse_id: UUID | None, refs: dict):
        gateway, caps = self.gateway, planner.caps
        customer_id = None
        if group.customer_name and caps.customers:
            customer = gateway.find_customer(group.customer_key)
            if customer is None:
                if not opts.infer_customers:
                    raise ImportRejected('customer_missing', f'El cliente «{group.customer_name}» no existe.',
                                         'customer_name')
                customer = gateway.create_customer(group.customer_name)
            elif not customer.active:
                raise ImportRejected('customer_inactive', f'El cliente «{customer.name}» está inactivo.',
                                     'customer_name')
            customer_id = customer.id
            refs['customer_id'] = str(customer.id)
        products: dict[str, ProductRef] = {}
        for line in group.lines:
            if line.product_key in products:
                continue
            product = gateway.find_product(line.product_key)
            if product is None:
                if not opts.infer_products:
                    raise ImportRejected('product_missing', f'El producto «{line.product_name}» no existe.',
                                         'product_name')
                tracks = planner.controls_stock(None)
                product = gateway.create_product(line.product_name, line.unit_price, tracks,
                                                 can_buy=opts.infer_inventory)
                refs['product_ids'].append(str(product.id))
            products[line.product_key] = product
        self._infer_purchases(group, products, opts, planner, warehouse_id, refs)
        return gateway.deliver_sale(
            group.sale_date, group.sales_channel, customer_id,
            [SaleLineInput(products[line.product_key].id, line.quantity, line.unit_price) for line in group.lines],
            group.payment_method, warehouse_id, opts.infer_accounting and caps.accounting,
            _sale_note(group, run_id))

    def _infer_purchases(self, group: SaleGroup, products: dict[str, ProductRef], opts: ImportOptions,
                         planner: _Planner, warehouse_id: UUID | None, refs: dict) -> None:
        if not (opts.infer_inventory and planner.caps.purchases and warehouse_id is not None):
            return
        needs: dict[str, int] = {}
        for line in group.lines:
            needs[line.product_key] = needs.get(line.product_key, 0) + line.quantity
        by_supplier: dict[str, tuple[str, list[tuple[UUID, int, Decimal]]]] = {}
        for key, need in needs.items():
            product = products[key]
            if not planner.controls_stock(product):
                continue
            short = planner.shortfall(self.gateway.stock_balance(warehouse_id, product.id), need)
            if short <= 0:
                continue
            lines: list[SaleLine] = [line for line in group.lines if line.product_key == key]
            cost = planner.unit_cost([line.unit_cost for line in lines], product)
            if cost is None:
                raise ImportRejected(
                    'cost_missing', f'Falta el costo unitario de «{product.name}» para crear la compra por el '
                    'faltante de stock.', 'unit_cost')
            if not product.can_buy:
                raise ImportRejected('product_not_buyable', f'El producto «{product.name}» no está habilitado para '
                                     'compra.', 'product_name')
            supplier_name = lines[0].supplier_name or DEFAULT_SUPPLIER
            by_supplier.setdefault(normalize_name(supplier_name), (supplier_name, []))[1].append(
                (product.id, short, cost))
        for _, (supplier_name, lines) in by_supplier.items():
            supplier_id = self.gateway.find_supplier(normalize_name(supplier_name)) or self.gateway.create_supplier(
                supplier_name)
            purchase_id = self.gateway.receive_purchase(supplier_id, group.sale_date, lines, warehouse_id,
                                                        opts.infer_accounting and planner.caps.accounting)
            refs['purchase_ids'].append(str(purchase_id))


def _sale_note(group: SaleGroup, run_id: UUID) -> str:
    base = f'Importada (archivo {str(run_id)[:8]})'
    if group.number:
        base += f' · venta {group.number}'
    return (base + (f' · {group.notes}' if group.notes else ''))[:2000]
