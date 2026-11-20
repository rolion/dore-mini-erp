"""Adaptadores de los puertos de Sales sobre las fachadas públicas de otros módulos y el reloj de Django.

Es el único lugar de Sales que conoce a Catalog, Customers y Modularity, y solo por sus `services.py`.
"""
import logging
from collections.abc import Iterable
from contextlib import contextmanager, nullcontext
from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from modules.accounting import services as accounting_services
from modules.catalog import services as catalog_services
from modules.costing import services as costing_services
from modules.customers import services as customer_services
from modules.inventory import services as inventory_services
from modules.modularity import services as modularity_services
from modules.sales.application.ports import (
    AT_CONFIRM,
    AT_DELIVERY,
    Actor,
    CustomerInfo,
    ProductInfo,
    StockOutputMovement,
    StockOutputRecord,
    StockProductInfo,
    StockWarehouse,
)
from modules.sales.domain.exceptions import (
    InsufficientStockForDelivery,
    OrderRuleViolation,
    OrderValidationError,
    ShortLine,
)
from modules.sales.domain.enums import OrderStatus
from modules.sales.domain.order import MAX_DISCOUNT_PERCENT
from shared import module_gate

CUSTOMERS_MODULE = 'customers'
INVENTORY_MODULE = 'inventory'
ACCOUNTING_MODULE = 'accounting'
COSTING_MODULE = 'costing'
INVENTORY_SALE_COST = 'INVENTORY_SALE_COST'  # evento del catálogo de Contabilidad (CONT-12 / INV-01)
PAYMENT_CURRENCY = 'BOB'
SALE_RECOGNITION = 'SALE_RECOGNITION'  # eventos del catálogo de Contabilidad (CONT-12 / VEN-01)
SALE_ADVANCE = 'SALE_ADVANCE'
SALE_DELIVERY = 'SALE_DELIVERY'
SALE_PAYMENT = 'SALE_PAYMENT'

logger = logging.getLogger(__name__)


class ProductCatalogAdapter:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def get_product_for_sale(self, product_id: UUID) -> ProductInfo | None:
        product = catalog_services.get_product_for_sale(self.company_id, product_id)
        if product is None:
            return None
        return ProductInfo(id=product.id, name=product.name, sale_price=product.sale_price, active=product.active,
                           can_sell=product.can_sell)


class CustomerDirectoryAdapter:
    def __init__(self, company_id: UUID):
        self.company_id = company_id
        self._available: bool | None = None

    def is_available(self) -> bool:
        """Clientes es una integración opcional: con el módulo deshabilitado Ventas funciona sin clientes."""
        if self._available is None:  # una consulta por adaptador (por petición)
            self._available = module_gate.is_enabled(self.company_id, CUSTOMERS_MODULE)
        return self._available

    def get_customer_for_sale(self, customer_id: UUID) -> CustomerInfo | None:
        if not self.is_available():
            return None
        customer = customer_services.get_customer_for_sale(self.company_id, customer_id)
        if customer is None:
            return None
        return CustomerInfo(id=customer.id, name=customer.name, active=customer.active)

    def get_customer_names(self, customer_ids: Iterable[UUID]) -> dict[UUID, str]:
        if not self.is_available():
            return {}
        return customer_services.get_customer_names(self.company_id, customer_ids)


class SalesSettingsAdapter:
    """Configuración de Ventas de la empresa; si no se puede leer, rige el valor inicial (regla previa)."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def max_discount_percent(self) -> Decimal:
        try:
            # Savepoint: un error de BD no debe dejar abortada la transacción de la petición.
            with transaction.atomic():
                return modularity_services.get_sales_settings(self.company_id).max_discount_percent
        except Exception:
            logger.exception('No se pudo leer la configuración de Ventas; se usa el valor inicial.')
            return MAX_DISCOUNT_PERCENT


class StockOutputAdapter:
    """Salidas de inventario al entregar, sobre la fachada de Inventario; es una integración opcional."""

    SOURCE_TYPE = 'sales_order'

    def __init__(self, company_id: UUID):
        self.company_id = company_id
        self._available: bool | None = None

    def is_available(self) -> bool:
        if self._available is None:  # una consulta por adaptador (por petición)
            self._available = module_gate.is_enabled(self.company_id, INVENTORY_MODULE)
        return self._available

    def controlled_products(self, product_ids: Iterable[UUID]) -> dict[UUID, StockProductInfo]:
        found = inventory_services.get_stock_products(self.company_id, product_ids)
        return {pid: StockProductInfo(p.id, p.name, p.unit_abbreviation) for pid, p in found.items()}

    def active_warehouses(self) -> list[StockWarehouse]:
        return [StockWarehouse(w.id, w.name, w.is_default)
                for w in inventory_services.list_active_warehouses(self.company_id)]

    def allow_negative_stock(self) -> bool:
        return inventory_services.allow_negative_stock(self.company_id)

    def balances(self, warehouse_id: UUID, product_ids: Iterable[UUID]) -> dict[UUID, Decimal]:
        return inventory_services.get_balances(self.company_id, warehouse_id, product_ids)

    def register_outputs(self, warehouse_id: UUID, lines: list[tuple[UUID, Decimal]], order_id: UUID,
                         reference: str, actor: Actor) -> None:
        try:
            with self._serialized():
                inventory_services.record_outputs(
                    self.company_id, warehouse_id=warehouse_id, lines=lines, source_type=self.SOURCE_TYPE,
                    source_id=str(order_id), user_id=actor.user_id, user_name=actor.user_name, reference=reference)
        except inventory_services.InsufficientStock as exc:
            raise self._insufficient(exc) from exc
        except inventory_services.MovementValidationError as exc:
            raise OrderValidationError(self._field_errors(exc.errors)) from exc
        except inventory_services.MovementConflict as exc:
            raise OrderRuleViolation(exc.code, str(exc)) from exc

    def _serialized(self):
        """Con Costeo, el bloqueo de la empresa se toma antes que el del almacén (mismo orden que el costo, REV-01)."""
        if module_gate.is_enabled(self.company_id, COSTING_MODULE):
            return inventory_services.lock_company_stock(self.company_id)
        return nullcontext()

    def output_for(self, order_id: UUID) -> StockOutputRecord | None:
        if not self.is_available():
            return None
        movements = inventory_services.list_movements_for_source(self.company_id, self.SOURCE_TYPE, str(order_id))
        if not movements:
            return None
        first = movements[0]
        return StockOutputRecord(
            reference=first.reference, warehouse_id=first.warehouse_id, warehouse_name=first.warehouse_name,
            occurred_at=first.occurred_at, user_name=first.user_name,
            movements=[StockOutputMovement(m.id, m.product_id, m.product_name, m.unit_abbreviation, m.quantity)
                       for m in movements])

    @staticmethod
    def _field_errors(errors: dict[str, list[str]]) -> dict[str, list[str]]:
        # Un dato de la salida (almacén) se muestra en su campo; lo demás no es atribuible a la persona.
        return {'warehouse_id' if key == 'warehouse_id' else 'non_field_errors': messages
                for key, messages in errors.items()}

    def _insufficient(self, exc) -> InsufficientStockForDelivery:
        products = inventory_services.get_stock_products(self.company_id, [s.product_id for s in exc.shortages])
        warehouse = next((w for w in self.active_warehouses() if w.id == exc.warehouse_id), None)
        lines = [ShortLine(
            product_id=s.product_id, product_name=products[s.product_id].name if s.product_id in products else '',
            unit=products[s.product_id].unit_abbreviation if s.product_id in products else None,
            requested=s.requested, available=s.available) for s in exc.shortages]
        return InsufficientStockForDelivery(
            str(exc), exc.warehouse_id, warehouse.name if warehouse else '', lines)


class SalesPostingAdapter:
    """Contabiliza Ventas en Contabilidad (solo por su fachada `services`), si el módulo está habilitado.

    Anticipos antes de entregar, reconocimiento al entregar y cobros contra Cuentas por cobrar; los cobros sin cobertura
    de partida doble siguen en el libro anterior (origen `PRODUCT`). Cada cobro sigue exactamente un camino.
    """

    def __init__(self, company_id: UUID):
        self.company_id = company_id
        self._available: bool | None = None

    def _enabled(self) -> bool:
        if self._available is None:
            self._available = module_gate.is_enabled(self.company_id, ACCOUNTING_MODULE)
        return self._available

    def _covers(self, on: date) -> bool:
        return accounting_services.coverage_status(self.company_id, on).covered

    def posts_on(self, on: date) -> bool:
        """¿Contabilidad está habilitada y cubre esa fecha (se generarían asientos)?"""
        return self._enabled() and self._covers(on)

    def recognition_state(self, order_id: UUID) -> str | None:
        if not self._enabled():
            return None
        if accounting_services.find_automatic_entry(self.company_id, SALE_RECOGNITION, order_id) is not None:
            return AT_CONFIRM
        if accounting_services.find_automatic_entry(self.company_id, SALE_DELIVERY, order_id) is not None:
            return AT_DELIVERY
        return None

    def locks_total(self, order) -> bool:
        if not self._enabled():
            return False
        if self.recognition_state(order.id) == AT_CONFIRM:
            return True
        return order.status is not OrderStatus.NEW and self._covers(timezone.localdate())

    def _posted(self, event: str, order) -> set[UUID]:
        return accounting_services.automatic_entry_origins(self.company_id, event, [p.id for p in order.payments])

    def has_posted_payments(self, order) -> bool:
        if not self._enabled() or not order.payments:
            return False
        return bool(self._posted(SALE_ADVANCE, order) | self._posted(SALE_PAYMENT, order))

    def record_payment(self, order, payment, actor: Actor, today: date) -> None:
        if not self._enabled():
            return
        if self.recognition_state(order.id) is not None:
            self._post_payment(SALE_PAYMENT, order, payment, actor)  # Debe método / Haber Cuentas por cobrar
            return
        if order.status is OrderStatus.NEW:
            if self._covers(today):
                raise OrderRuleViolation(
                    'order_not_confirmed', 'Confirma el pedido antes de registrar su cobro.')
        elif order.status in (OrderStatus.IN_PREPARATION, OrderStatus.READY) and self._covers(today):
            self._post_payment(SALE_ADVANCE, order, payment, actor)  # Debe método / Haber Anticipos de clientes
            return
        self._record_in_legacy_ledger(order.id, payment, actor)

    def _post_payment(self, event: str, order, payment, actor: Actor) -> None:
        with _posting_errors():
            posted = accounting_services.post_automatic_entry(
                self.company_id, event, payment.id, payment.payment_date, f'Cobro del pedido {order.code}',
                payment.amount, method=payment.payment_method.value, created_by=actor.user_id,
                created_by_name=actor.user_name)
        if not posted.posted:
            raise OrderRuleViolation(
                'payment_date_not_covered',
                'La fecha del cobro no tiene cobertura contable; usa una fecha posterior al corte de Contabilidad.')

    def recognize_delivery(self, order, actor: Actor) -> None:
        if not self._enabled() or order.total <= 0:
            return
        if self.recognition_state(order.id) == AT_CONFIRM:
            return  # reconocido con la lógica anterior: no se reconoce otra vez
        delivered_on = order.delivered_date
        advances = self._posted(SALE_ADVANCE, order)
        if not self._covers(delivered_on):
            if advances:
                raise OrderRuleViolation(
                    'delivery_date_not_covered',
                    'El pedido tiene anticipos contabilizados y la fecha de entrega no tiene cobertura contable; '
                    'usa una fecha de entrega posterior al corte de Contabilidad.')
            return
        if any(payment.id not in advances for payment in order.payments):
            raise OrderRuleViolation(
                'order_has_unposted_payments',
                'El pedido tiene cobros registrados sin asiento contable (hechos antes de la cobertura de '
                'Contabilidad) y no puede entregarse hasta definir su tratamiento.')
        applied = sum((payment.amount for payment in order.payments), Decimal('0'))
        with _posting_errors():
            accounting_services.post_automatic_entry(
                self.company_id, SALE_DELIVERY, order.id, delivered_on, f'Entrega del pedido {order.code}', order.total,
                advance_applied=applied, created_by=actor.user_id, created_by_name=actor.user_name)

    def reverse_recognition(self, order, reason: str, actor: Actor, today: date) -> None:
        if not self._enabled():
            return
        with _posting_errors():
            accounting_services.reverse_automatic_entry(
                self.company_id, SALE_RECOGNITION, order.id, today, f'Pedido {order.code} cancelado: {reason}',
                created_by=actor.user_id, created_by_name=actor.user_name)

    def _record_in_legacy_ledger(self, order_id: UUID, payment, actor: Actor) -> None:
        """Cobro de un pedido confirmado antes de la cobertura: libro anterior, como antes de VEN-01."""
        method = payment.payment_method.value
        account = accounting_services.resolve_account(self.company_id, method)
        if account is None:
            raise OrderRuleViolation(
                'payment_method_without_account',
                'El método de pago no tiene una cuenta destino activa. Configúrala en Contabilidad → Cuentas y '
                'Métodos de pago e inténtalo de nuevo.')
        try:
            accounting_services.record_entry(self.company_id, accounting_services.EntryInput(
                account_id=account.account_id, currency=PAYMENT_CURRENCY, amount=payment.amount,
                payment_date=payment.payment_date, method=method, origin_kind='PRODUCT', origin_id=payment.id,
                origin_document_ref=str(order_id), recorded_by=actor.user_id, recorded_by_name=actor.user_name))
        except accounting_services.EntryValidationError as exc:
            raise OrderRuleViolation(
                'ledger_rejected', 'Contabilidad rechazó la entrada del cobro: ' + _first_message(exc.errors)) from exc
        except accounting_services.EntryConflict as exc:
            raise OrderRuleViolation('ledger_conflict', str(exc)) from exc


class DeliveryCostingAdapter:
    """Costo de ventas al entregar (INV-01), sobre las fachadas de Costeo y Contabilidad.

    Con cobertura contable: valoriza al costo promedio y asienta `INVENTORY_SALE_COST` por el total, o rechaza la
    entrega (nunca inventa un costo). Sin cobertura: registra el costo si Costeo lo tiene y sigue sin asiento.
    """

    SOURCE_TYPE = StockOutputAdapter.SOURCE_TYPE

    def __init__(self, company_id: UUID, post_accounting: bool = True):
        self.company_id = company_id
        self.post_accounting = post_accounting  # False (importación sin contabilidad): registra el costo, sin asiento

    def cost_delivery(self, order, lines: list[tuple[UUID, Decimal]], actor: Actor) -> None:
        covered = self.post_accounting and module_gate.is_enabled(
            self.company_id, ACCOUNTING_MODULE) and accounting_services.coverage_status(
            self.company_id, order.delivered_date).covered
        if not module_gate.is_enabled(self.company_id, COSTING_MODULE):
            if covered:
                raise OrderRuleViolation('inventory_cost_unavailable', _COSTING_OFF)
            return
        try:
            costed = costing_services.cost_outputs(
                self.company_id, source_type=self.SOURCE_TYPE, source_id=str(order.id), lines=lines,
                occurred_at=self._occurred_at(order.delivered_date))
        except costing_services.CostUnavailable as exc:
            if not covered:
                return
            raise OrderRuleViolation('inventory_cost_unavailable', self._unavailable_message(exc),
                                     {'product_ids': [str(pid) for pid in exc.product_ids]}) from exc
        if not covered or costed.total <= 0:
            return  # sin cobertura no hay asiento; un costo total cero (declarado) no genera movimiento
        with _posting_errors():
            accounting_services.post_automatic_entry(
                self.company_id, INVENTORY_SALE_COST, order.id, order.delivered_date,
                f'Costo de ventas del pedido {order.code}', costed.total, created_by=actor.user_id,
                created_by_name=actor.user_name)

    @staticmethod
    def _occurred_at(delivered_on: date) -> datetime:
        """Momento del evento de costo: ahora si se entrega hoy; si no, el inicio del día de entrega (REV-03)."""
        if delivered_on == timezone.localdate():
            return timezone.now()
        return timezone.make_aware(datetime.combine(delivered_on, time.min))

    def _unavailable_message(self, exc) -> str:
        if exc.reason == costing_services.CostUnavailable.NOT_ADOPTED:
            return _COSTING_NOT_ADOPTED
        names = inventory_services.get_product_names(self.company_id, exc.product_ids)
        listed = ', '.join(names[pid][0] for pid in exc.product_ids if pid in names) or 'algunos productos'
        return ('No se puede contabilizar el costo de ventas: no hay costo promedio para ' + listed
                + '. Registra una compra recibida de esos productos o revisa la valoración inicial en Costeo.')


_COSTING_OFF = ('No se puede contabilizar el costo de ventas: habilita Costeo y adopta la valoración inicial de '
                'las existencias.')
_COSTING_NOT_ADOPTED = ('No se puede contabilizar el costo de ventas: adopta la valoración inicial de las '
                        'existencias en Costeo.')


@contextmanager
def _posting_errors():
    """Traduce los rechazos del motor y de la configuración a errores de Ventas (409 accionables)."""
    try:
        yield
    except accounting_services.PostingConfigurationMissing as exc:
        issues = [{'code': i.code, 'role': i.role, 'subject': i.subject, 'message': i.message, 'params': i.params}
                  for i in exc.issues]
        raise OrderRuleViolation('posting_configuration_missing', '; '.join(i['message'] for i in issues),
                                 {'issues': issues}) from exc
    except (accounting_services.FiscalPeriodClosed, accounting_services.DateOutsideFiscalPeriod) as exc:
        raise OrderRuleViolation('fiscal_period_unavailable', str(exc)) from exc
    except accounting_services.JournalValidationError as exc:
        raise OrderRuleViolation(
            'ledger_rejected', 'Contabilidad rechazó el asiento: ' + _first_message(exc.errors)) from exc
    except accounting_services.JournalConflict as exc:
        raise OrderRuleViolation('ledger_conflict', str(exc)) from exc


def _first_message(errors: dict[str, list[str]]) -> str:
    return next((messages[0] for messages in errors.values() if messages), 'datos no válidos.')


class SystemClock:
    """"Hoy" según la zona horaria configurada (`TIME_ZONE`), no la del navegador."""

    def today(self) -> date:
        return timezone.localdate()

    def now(self) -> datetime:
        return timezone.now()
