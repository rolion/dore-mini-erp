"""Casos de uso de la importación de ventas: subir, previsualizar (sin escribir) y ejecutar por venta."""
import hashlib
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from itertools import groupby
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


def _failure_message(exc: Exception) -> str:
    if isinstance(exc, ImportValidationError):
        return ' · '.join(m for messages in exc.errors.values() for m in messages) or 'La importación no es válida.'
    return getattr(exc, 'message', None) or str(exc)


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


@dataclass
class PlannedLine:
    key: str
    name: str
    product: ProductRef | None
    quantity: int
    cost: Decimal
    price: Decimal
    category: str
    row: int


@dataclass
class DayPlan:
    """Compras que hacen falta un día: una por proveedor con el faltante de stock de todas las ventas del día."""
    purchases: dict[str, tuple[str, list[PlannedLine]]] = field(default_factory=dict)
    blocked: dict[str, ImportRejected] = field(default_factory=dict)  # producto → motivo por el que no se puede comprar
    blocked_rows: dict[str, int] = field(default_factory=dict)
    balances: dict[str, Decimal] = field(default_factory=dict)  # saldo proyectado por producto tras comprar
    units: int = 0


def plan_day(planner: '_Planner', groups: list[SaleGroup], products: dict[str, ProductRef | None],
             balances: dict[str, Decimal], warehouse_id: UUID | None) -> DayPlan:
    plan = DayPlan()
    if warehouse_id is None:
        return plan
    lines_by_key: dict[str, list[SaleLine]] = {}
    for group in groups:
        for line in group.lines:
            lines_by_key.setdefault(line.product_key, []).append(line)
    for key, lines in lines_by_key.items():
        product = products.get(key)
        if not planner.controls_stock(product):
            continue
        balance = balances.get(key)
        if balance is None:
            balance = planner.gateway.stock_balance(warehouse_id, product.id) if product is not None else Decimal('0')
        plan.balances[key] = balance
        short = planner.shortfall(balance, sum(line.quantity for line in lines))
        if short <= 0:
            continue
        first = lines[0]
        cost = planner.unit_cost([line.unit_cost for line in lines], product)
        if cost is None:
            plan.blocked[key] = ImportRejected(
                'cost_missing', f'Falta el costo unitario de «{first.product_name}» para crear la compra por el '
                'faltante de stock: agrega la columna de costo o registra una compra antes.', 'unit_cost')
            plan.blocked_rows[key] = first.row
            continue
        if product is not None and not product.can_buy:
            plan.blocked[key] = ImportRejected(
                'product_not_buyable', f'El producto «{product.name}» no está habilitado para compra.',
                'product_name')
            plan.blocked_rows[key] = first.row
            continue
        if product is None and not planner.options.infer_products:
            continue  # la venta falla por producto inexistente; no se compra nada
        supplier = next((line.supplier_name for line in lines if line.supplier_name), '') or DEFAULT_SUPPLIER
        plan.purchases.setdefault(normalize_name(supplier), (supplier, [])).__getitem__(1).append(
            PlannedLine(key, first.product_name, product, short, cost, first.unit_price, first.category, first.row))
        plan.balances[key] = balance + short
        plan.units += short
    return plan


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
        for _day, day_iter in groupby(groups, key=lambda g: g.sale_date):
            day_groups = list(day_iter)
            live = []
            for group in day_groups:
                if group.key in duplicates:
                    result.already_imported += 1
                else:
                    live.append(group)
            if not live:
                continue
            per_group: dict[str, tuple[list[RowProblem], dict, object]] = {}
            day_products: dict[str, ProductRef | None] = {}
            for group in live:
                problems: list[RowProblem] = []

                def problem(line_row: int, field_name: str, code: str, message: str, _g=group, _p=problems) -> None:
                    _p.append(RowProblem(line_row, _g.key, field_name, code, message))

                products = self._check_products(group, opts, problem)
                day_products.update({k: v for k, v in products.items() if k not in day_products or v is not None})
                customer = self._check_customer(group, opts, caps, problem)
                per_group[group.key] = (problems, products, customer)
            plan = plan_day(planner, live, day_products, balances, warehouse_id)
            result.purchases_to_create += len(plan.purchases)
            result.units_to_buy += plan.units
            balances.update(plan.balances)
            for group in live:
                problems, products, customer = per_group[group.key]

                def problem(line_row: int, field_name: str, code: str, message: str, _g=group, _p=problems) -> None:
                    _p.append(RowProblem(line_row, _g.key, field_name, code, message))

                for line in group.lines:
                    blocked = plan.blocked.get(line.product_key)
                    if blocked is not None:
                        problem(line.row, blocked.field or 'product_name', blocked.code, blocked.message)
                        break
                staged = self._simulate_stock(group, products, planner, warehouse_id, balances, allow_negative,
                                              problem)
                if warehouse_id is None and not warehouse_flagged and any(
                        planner.controls_stock(p) for p in products.values()):
                    warehouse_flagged = True
                    problem(group.first_row, 'warehouse_id', 'warehouse_required',
                            'Elige el almacén de salida: hay productos con control de stock.')
                posts = bool(opts.infer_accounting and caps.accounting and gateway.is_covered(group.sale_date))
                if posts and caps.costing and not caps.costing_valued and any(
                        planner.controls_stock(p) for p in products.values()):
                    problem(group.first_row, 'sale_date', 'costing_not_adopted',
                            'Para contabilizar el costo de ventas, adopta antes la valoración inicial de las '
                            'existencias en Costeo (o desmarca «Inferir movimientos contables»).')
                if problems:
                    result.with_errors += 1
                    result.problems.extend(problems)
                    continue
                balances.update(staged)
                result.to_create += 1
                for key, product in products.items():
                    if key not in seen_products:
                        seen_products.add(key)
                        result.existing_products += product is not None
                        result.new_products += product is None
                if group.customer_name and caps.customers and group.customer_key not in seen_customers:
                    seen_customers.add(group.customer_key)
                    result.existing_customers += customer is not None
                    result.new_customers += customer is None
                if opts.infer_accounting and caps.accounting and not posts:
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
        """Saldos proyectados tras la venta (las compras del día ya están en `balances`)."""
        staged: dict[str, Decimal] = {}
        if warehouse_id is None:
            return staged
        needs: dict[str, int] = {}
        for line in group.lines:
            needs[line.product_key] = needs.get(line.product_key, 0) + line.quantity
        for key, need in needs.items():
            product = products.get(key)
            if not planner.controls_stock(product):
                continue
            balance = balances.get(key)
            if balance is None:
                balance = (planner.gateway.stock_balance(warehouse_id, product.id) if product is not None
                           else Decimal('0'))
            if balance - need < 0 and not allow_negative and not planner.options.infer_inventory:
                first = next(line for line in group.lines if line.product_key == key)
                problem(first.row, 'quantity', 'insufficient_stock',
                        f'Stock insuficiente de «{first.product_name}»: hay {int(balance)} y se venden {need}.')
            staged[key] = balance - need
        return staged


class EnqueueSalesImport:
    """Valida lo mismo que la carga y deja la importación en cola; un worker la ejecuta en segundo plano."""

    def __init__(self, repository: ImportRepository, gateway: SalesImportGateway, clock: Clock):
        self.repository = repository
        self.gateway = gateway
        self.clock = clock

    def execute(self, run_id: UUID, mapping: object, options: object, idempotency_key: UUID | None) -> RunData:
        run = _load_run(self.repository, run_id)
        if run.status == 'COMPLETED':
            return run  # idempotente: devuelve el resultado ya guardado
        if run.status in ('QUEUED', 'RUNNING'):
            if idempotency_key is not None and run.idempotency_key == idempotency_key:
                return run  # reintento de la misma petición: no se encola otra vez
            raise ImportRuleViolation('import_running', 'La importación ya está en curso.')
        _validate_run(run, self.gateway, mapping, options)
        self.repository.enqueue(run_id, idempotency_key, self.clock.now())
        return _load_run(self.repository, run_id)


def _validate_run(run: RunData, gateway: SalesImportGateway, mapping: object, options: object):
    """Revalida mapeo, opciones, firma de la vista previa, módulos y almacén (al encolar y al ejecutar)."""
    clean_mapping = validate_mapping(mapping, run.headers)
    opts = parse_options(options)
    if not run.preview_signature:
        raise ImportRuleViolation('preview_required', 'Previsualiza la importación antes de cargarla.')
    if signature(clean_mapping, opts.as_dict()) != run.preview_signature:
        raise ImportRuleViolation('preview_stale',
                                  'El mapeo u opciones cambiaron desde la vista previa: vuelve a previsualizar.')
    caps = gateway.capabilities()
    _check_capabilities(opts, caps)
    return clean_mapping, opts, caps, _resolve_warehouse(opts, caps)


class ExecuteSalesImport:
    """Carga cada venta en su propia transacción (INV-04), en orden cronológico e idempotente (INV-05).

    `run_claimed` es lo que ejecuta el worker sobre una corrida ya reclamada; `execute` reclama y carga en el
    mismo proceso (pruebas y operación manual)."""

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
        clean_mapping, opts, caps, warehouse_id = _validate_run(run, self.gateway, mapping, options)
        self.repository.claim(run_id, idempotency_key, self.clock.now())
        self._process(run, clean_mapping, opts, caps, warehouse_id)
        return _load_run(self.repository, run_id)

    def run_claimed(self, run_id: UUID) -> RunData:
        """Ejecuta una corrida que el worker ya pasó a `RUNNING`; nunca deja una excepción sin dueño: ante un
        fallo la corrida termina `FAILED` con su código y mensaje."""
        run = _load_run(self.repository, run_id)
        try:
            clean_mapping, opts, caps, warehouse_id = _validate_run(run, self.gateway, run.mapping, run.options)
        except (ImportValidationError, ImportRuleViolation) as exc:
            self.repository.fail(run_id, getattr(exc, 'code', 'validation_failed'), _failure_message(exc),
                                 self.clock.now())
            return _load_run(self.repository, run_id)
        try:
            self._process(run, clean_mapping, opts, caps, warehouse_id)
        except Exception:
            logger.exception('Error inesperado en la importación %s', run_id)
            self.repository.fail(run_id, 'unexpected_error',
                                 'Ocurrió un error inesperado y la importación se detuvo. Lo ya cargado se conserva: '
                                 'vuelve a intentarla y no se duplicará.', self.clock.now())
        return _load_run(self.repository, run_id)

    def _process(self, run: RunData, clean_mapping: dict, opts: ImportOptions, caps: Capabilities,
                 warehouse_id: UUID | None) -> None:
        run_id = run.id
        parsed = parse_sales(run.headers, run.rows, clean_mapping, opts, self.clock.today())
        counts = {'created': 0, 'skipped': 0, 'failed': 0, 'without_posting': 0}
        total = len(parsed.groups)
        done = 0
        self.repository.heartbeat(run_id, self.clock.now(), processed=0, total=total)
        try:
            self._report_invalid(run_id, parsed, counts)
            duplicates = self.repository.existing_keys([g.key for g in parsed.groups])
            planner = _Planner(self.gateway, opts, caps)
            for _day, day_iter in groupby(parsed.groups, key=lambda g: g.sale_date):
                day_groups = list(day_iter)
                day = self._prepare_day([g for g in day_groups if g.key not in duplicates], opts, planner,
                                        warehouse_id)
                for group in day_groups:
                    if group.key in duplicates:
                        self._duplicate(run_id, group, counts)
                    else:
                        self._load_sale(run_id, group, opts, planner, warehouse_id, counts, day)
                    done += 1
                    self.repository.heartbeat(run_id, self.clock.now(), processed=done, total=total)
        except Exception:
            self.repository.finish(run_id, 'FAILED', counts, self.clock.now())
            raise
        self.repository.finish(run_id, 'COMPLETED', counts, self.clock.now())

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

    def _fail(self, run_id: UUID, group: SaleGroup, code: str, message: str, counts: dict,
              day: '_DayContext') -> None:
        self.gateway.reset_cache()
        self.repository.add_result(run_id, group.first_row, group.key, STATUS_FAILED, code, message, None,
                                   day.take_refs())
        counts['failed'] += 1

    def _load_sale(self, run_id: UUID, group: SaleGroup, opts: ImportOptions, planner: _Planner,
                   warehouse_id: UUID | None, counts: dict, day: '_DayContext') -> None:
        gateway = self.gateway
        refs: dict[str, object] = {'purchase_ids': [], 'product_ids': [], 'customer_id': None}
        try:
            with gateway.atomic():
                outcome = self._build_sale(run_id, group, opts, planner, warehouse_id, refs, day)
                # Misma transacción que la venta: la clave única impide duplicarla (reintentos y cargas simultáneas).
                self.repository.record_sale(group.key, outcome.order_id, run_id)
        except DuplicateSale:
            self.gateway.reset_cache()
            self._duplicate(run_id, group, counts)
            return
        except ImportRejected as exc:
            self._fail(run_id, group, exc.code, exc.message, counts, day)
            return
        except Exception:
            logger.exception('Error inesperado al importar la venta %s', group.key)
            self._fail(run_id, group, 'unexpected_error',
                       'Ocurrió un error inesperado al cargar esta venta; no se guardó nada de ella.', counts, day)
            return
        without = outcome.without_posting and opts.infer_accounting and planner.caps.accounting
        status = STATUS_WITHOUT_POSTING if without else STATUS_CREATED
        message = ('Cargada sin asiento: la fecha no tiene cobertura contable.' if without else '')
        day_refs = day.take_refs()
        refs['purchase_ids'] = [*day_refs.get('purchase_ids', []), *refs['purchase_ids']]
        refs['product_ids'] = [*day_refs.get('product_ids', []), *refs['product_ids']]
        self.repository.add_result(run_id, group.first_row, group.key, status, '', message, outcome.order_id, refs)
        counts['created'] += 1
        if without:
            counts['without_posting'] += 1

    def _build_sale(self, run_id: UUID, group: SaleGroup, opts: ImportOptions, planner: _Planner,
                    warehouse_id: UUID | None, refs: dict, day: '_DayContext'):
        gateway, caps = self.gateway, planner.caps
        for line in group.lines:
            if line.product_key in day.blocked:
                raise day.blocked[line.product_key]
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
                                                 can_buy=opts.infer_inventory, category=line.category)
                refs['product_ids'].append(str(product.id))
            products[line.product_key] = product
        return gateway.deliver_sale(
            group.sale_date, group.sales_channel, customer_id,
            [SaleLineInput(products[line.product_key].id, line.quantity, line.unit_price) for line in group.lines],
            group.payment_method, warehouse_id, opts.infer_accounting and caps.accounting,
            _sale_note(group, run_id), group.discount)

    def _prepare_day(self, groups: list[SaleGroup], opts: ImportOptions, planner: _Planner,
                     warehouse_id: UUID | None) -> '_DayContext':
        """Una compra recibida y pagada por proveedor con el faltante de stock de todas las ventas del día.

        Cada compra corre en su propia transacción (con los productos y el proveedor que haga falta crear): si una
        se rechaza, solo se bloquean las ventas con esos productos."""
        day = _DayContext()
        if not groups or not (opts.infer_inventory and planner.caps.purchases and warehouse_id is not None):
            return day
        products: dict[str, ProductRef | None] = {}
        for group in groups:
            for line in group.lines:
                if products.get(line.product_key) is None:
                    products[line.product_key] = self.gateway.find_product(line.product_key)
        plan = plan_day(planner, groups, products, {}, warehouse_id)
        day.blocked.update(plan.blocked)
        for supplier_name, lines in plan.purchases.values():
            try:
                with self.gateway.atomic():
                    created = self._buy(supplier_name, lines, groups[0].sale_date, opts, planner, warehouse_id)
            except ImportRejected as exc:
                self.gateway.reset_cache()
                for line in lines:
                    day.blocked[line.key] = exc
                continue
            day.refs['purchase_ids'].append(str(created[0]))
            day.refs['product_ids'].extend(created[1])
        return day

    def _buy(self, supplier_name: str, lines: list[PlannedLine], on, opts: ImportOptions, planner: _Planner,
             warehouse_id: UUID | None) -> tuple[UUID, list[str]]:
        gateway = self.gateway
        created_products: list[str] = []
        items: list[tuple[UUID, int, Decimal]] = []
        for line in lines:
            product = gateway.find_product(line.key)
            if product is None:
                product = gateway.create_product(line.name, line.price, planner.controls_stock(None),
                                                 can_buy=opts.infer_inventory, category=line.category)
                created_products.append(str(product.id))
            items.append((product.id, line.quantity, line.cost))
        supplier_id = gateway.find_supplier(normalize_name(supplier_name)) or gateway.create_supplier(supplier_name)
        purchase_id = gateway.receive_purchase(supplier_id, on, items, warehouse_id,
                                               opts.infer_accounting and planner.caps.accounting,
                                               opts.default_payment_method)
        return purchase_id, created_products


@dataclass
class _DayContext:
    """Lo creado a nivel de día (compras y productos) y los productos que no se pudieron comprar."""
    refs: dict[str, list[str]] = field(default_factory=lambda: {'purchase_ids': [], 'product_ids': []})
    blocked: dict[str, ImportRejected] = field(default_factory=dict)

    def take_refs(self) -> dict[str, list[str]]:
        """Lo creado a nivel de día se asigna al primer resultado del día (una sola vez)."""
        taken, self.refs = self.refs, {'purchase_ids': [], 'product_ids': []}
        return taken


def _sale_note(group: SaleGroup, run_id: UUID) -> str:
    base = f'Importada (archivo {str(run_id)[:8]})'
    if group.number:
        base += f' · venta {group.number}'
    return (base + (f' · {group.notes}' if group.notes else ''))[:2000]
