"""Adaptadores de los puertos de Purchases sobre las fachadas públicas de otros módulos.

Es el único lugar de Purchases que conoce a Catalog e Inventory, y solo por su `services.py`.
"""
from collections.abc import Iterable
from contextlib import contextmanager, nullcontext
from uuid import UUID

from datetime import date
from decimal import Decimal

from django.utils import timezone

from modules.accounting import services as accounting_services
from modules.catalog import services as catalog_services
from modules.costing import services as costing_services
from modules.inventory import services as inventory_services
from modules.purchases.application.ports import (
    Actor,
    ClassificationInfo,
    PaymentPreview,
    PaymentPreviewLine,
    PostedEntry,
    PostedPaymentEntry,
    ProductInfo,
    StockEntryMovement,
    StockProductInfo,
    StockWarehouse,
)
from modules.purchases.domain.exceptions import PostingRejected, PurchaseValidationError, StockShortage
from shared import module_gate

INVENTORY_MODULE = 'inventory'
COSTING_MODULE = 'costing'
ACCOUNTING_MODULE = 'accounting'
PURCHASE_RECOGNITION = 'PURCHASE_RECOGNITION'
PURCHASE_PAYMENT = 'PURCHASE_PAYMENT'
PURCHASE_ADVANCE = 'PURCHASE_ADVANCE'


class ProductCatalogAdapter:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def get_products(self, product_ids: Iterable[UUID]) -> dict[UUID, ProductInfo]:
        products = catalog_services.get_products_for_purchase(self.company_id, product_ids)
        return {
            pid: ProductInfo(id=p.id, name=p.name, active=p.active, can_buy=p.can_buy,
                             unit_abbreviation=p.unit_abbreviation, allows_fractions=p.allows_fractions)
            for pid, p in products.items()
        }


class StockEntryAdapter:
    """Entradas de inventario al recibir, sobre la fachada de Inventario; es una integración opcional."""

    SOURCE_TYPE = 'purchase_receipt'

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

    def register_entries(self, warehouse_id: UUID, lines: list[tuple[UUID, Decimal]], receipt_id: UUID,
                         reference: str, actor: Actor, unit_costs: dict[UUID, Decimal] | None = None) -> None:
        with self._serialized():
            for product_id, quantity in lines:
                try:
                    inventory_services.record_movement(
                        self.company_id, product_id=product_id, warehouse_id=warehouse_id, kind='in',
                        quantity=quantity, user_id=actor.user_id, user_name=actor.user_name, reference=reference,
                        source_type=self.SOURCE_TYPE, source_id=str(receipt_id), source_line=str(product_id))
                except inventory_services.MovementValidationError as exc:
                    # Solo el almacén es atribuible a la persona; lo demás se informa sin campo.
                    raise PurchaseValidationError({
                        'warehouse_id' if key == 'warehouse_id' else 'non_field_errors': messages
                        for key, messages in exc.errors.items()}) from exc
                except inventory_services.MovementConflict as exc:
                    raise PurchaseValidationError({'non_field_errors': [str(exc)]}) from exc
            self._cost_entries(lines, receipt_id, unit_costs)

    def _serialized(self):
        """Con Costeo, el bloqueo de la empresa se toma antes que el del almacén (REV-01)."""
        if module_gate.is_enabled(self.company_id, COSTING_MODULE):
            return inventory_services.lock_company_stock(self.company_id)
        return nullcontext()

    def _cost_entries(self, lines: list[tuple[UUID, Decimal]], receipt_id: UUID,
                      unit_costs: dict[UUID, Decimal] | None) -> None:
        """Traslada el precio acordado al costo promedio (INV-01). Sin Costeo adoptado no hace nada ni asienta."""
        if not unit_costs or not module_gate.is_enabled(self.company_id, COSTING_MODULE):
            return
        costing_services.cost_receipt(
            self.company_id, source_type=self.SOURCE_TYPE, source_id=str(receipt_id),
            lines=[(pid, qty, unit_costs[pid]) for pid, qty in lines if pid in unit_costs])

    def reverse_entries(self, receipt_id: UUID, reason: str, actor: Actor) -> None:
        try:
            with self._serialized():
                inventory_services.reverse_source_movements(
                    self.company_id, self.SOURCE_TYPE, str(receipt_id), user_id=actor.user_id,
                    user_name=actor.user_name, reason=reason)
                if module_gate.is_enabled(self.company_id, COSTING_MODULE):
                    costing_services.reverse_receipt_cost(
                        self.company_id, source_type=self.SOURCE_TYPE, source_id=str(receipt_id))
        except inventory_services.InsufficientStock as exc:
            raise StockShortage(exc.warehouse_id, [(s.product_id, s.requested, s.available)
                                                   for s in exc.shortages]) from exc
        except inventory_services.MovementValidationError as exc:
            raise PurchaseValidationError({'non_field_errors': [m for ms in exc.errors.values() for m in ms]}) from exc
        except inventory_services.MovementConflict as exc:
            raise PurchaseValidationError({'non_field_errors': [str(exc)]}) from exc

    def movements_for(self, receipt_id: UUID) -> list[StockEntryMovement]:
        return [StockEntryMovement(m.id, m.product_id, m.product_name, m.unit_abbreviation, m.warehouse_id,
                                   m.warehouse_name, m.quantity, m.reference, m.status, m.reversed_by_id,
                                   m.reversed_by_reference)
                for m in inventory_services.list_movements_for_source(
                    self.company_id, self.SOURCE_TYPE, str(receipt_id))]


class AccountingClassifications:
    """Clasificaciones y cobertura de Contabilidad, solo por su fachada `services`."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def validate_expense_classification(self, classification_id: UUID) -> ClassificationInfo:
        try:
            ref = accounting_services.validate_classification(self.company_id, classification_id, 'EXPENSE')
        except accounting_services.AccountValidationError as exc:
            raise PurchaseValidationError(exc.errors) from exc
        return ClassificationInfo(ref.classification_id, ref.name, ref.direction, True)

    def describe(self, classification_ids: Iterable[UUID]) -> dict[UUID, ClassificationInfo]:
        found = accounting_services.describe_classifications(self.company_id, classification_ids)
        return {k: ClassificationInfo(v.classification_id, v.name, v.direction, v.is_active) for k, v in found.items()}

    def is_covered(self, on: date) -> bool:
        return accounting_services.coverage_status(self.company_id, on).covered


class PurchasePostingAdapter:
    """Contabiliza la recepción de mercadería en Contabilidad (solo por su fachada), si está habilitada."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id
        self._available: bool | None = None

    def is_available(self) -> bool:
        if self._available is None:
            self._available = module_gate.is_enabled(self.company_id, ACCOUNTING_MODULE)
        return self._available

    def covers(self, on: date) -> bool:
        return self.is_available() and accounting_services.coverage_status(self.company_id, on).covered

    def recognize_receipt(self, purchase, receipt, amount: Decimal, actor: Actor,
                          advance_applied: Decimal = Decimal('0')) -> None:
        if not self.is_available():
            return
        with _posting_errors():
            accounting_services.post_automatic_entry(
                self.company_id, PURCHASE_RECOGNITION, receipt.id, receipt.receipt_date,
                f'Compra {purchase.reference} - recepcion {receipt.reference}', amount,
                advance_applied=advance_applied if advance_applied > 0 else None,
                created_by=actor.user_id, created_by_name=actor.user_name)

    def record_payment(self, purchase, payment, debt: Decimal, advance: Decimal, actor: Actor) -> None:
        if not self.is_available():
            return
        method = payment.payment_method.value
        for event, amount, label in ((PURCHASE_PAYMENT, debt, 'Pago'), (PURCHASE_ADVANCE, advance, 'Anticipo')):
            if amount <= 0:
                continue
            with _posting_errors():
                accounting_services.post_automatic_entry(
                    self.company_id, event, payment.id, payment.payment_date,
                    f'{label} {payment.reference} de la compra {purchase.reference}', amount, method=method,
                    created_by=actor.user_id, created_by_name=actor.user_name)

    def preview_payment(self, purchase, amount: Decimal, method: str, on: date, debt: Decimal,
                        advance: Decimal) -> PaymentPreview:
        if not self.covers(on):
            return PaymentPreview(False, debt, advance)
        lines: list[PaymentPreviewLine] = []
        issues: list[dict] = []
        for event, part in ((PURCHASE_PAYMENT, debt), (PURCHASE_ADVANCE, advance)):
            if part <= 0:
                continue
            preview = accounting_services.preview_automatic_entry(self.company_id, event, on, part, method=method)
            lines += [PaymentPreviewLine(line.side, line.role, line.account_name, line.amount)
                      for line in preview.lines]
            issues += [{'code': i.code, 'role': i.role, 'subject': i.subject, 'message': i.message,
                        'params': i.params} for i in preview.issues]
        return PaymentPreview(True, debt, advance, tuple(lines), tuple(issues))

    def payment_entries(self, payment_ids: Iterable[UUID]) -> dict[UUID, list[PostedPaymentEntry]]:
        ids = list(payment_ids)
        found: dict[UUID, list[PostedPaymentEntry]] = {}
        if not ids or not self.is_available():
            return found
        for event, kind in ((PURCHASE_PAYMENT, 'debt'), (PURCHASE_ADVANCE, 'advance')):
            for payment_id, entry in accounting_services.automatic_entries_for(self.company_id, event, ids).items():
                found.setdefault(payment_id, []).append(
                    PostedPaymentEntry(entry.id, kind, entry.accounting_date, entry.total))
        return found

    def reverse_receipt(self, purchase, receipt, reason: str, actor: Actor) -> None:
        # Aunque Contabilidad esté deshabilitada hoy, un asiento ya publicado se revierte con la recepción.
        with _posting_errors():
            accounting_services.reverse_automatic_entry(
                self.company_id, PURCHASE_RECOGNITION, receipt.id, timezone.localdate(),
                f'Recepcion {receipt.reference} de la compra {purchase.reference} revertida: {reason}',
                created_by=actor.user_id, created_by_name=actor.user_name)

    def recognized_totals(self, receipt_ids: Iterable[UUID]) -> dict[UUID, Decimal]:
        found = {}
        for receipt_id in receipt_ids:
            entry = accounting_services.find_automatic_entry(self.company_id, PURCHASE_RECOGNITION, receipt_id)
            if entry is not None:
                found[receipt_id] = entry.total
        return found

    def entry_for(self, receipt_id: UUID) -> PostedEntry | None:
        entry = accounting_services.find_automatic_entry(self.company_id, PURCHASE_RECOGNITION, receipt_id)
        return None if entry is None else PostedEntry(entry.id, entry.accounting_date, entry.total)


@contextmanager
def _posting_errors():
    """Traduce los rechazos del motor y de la configuración a errores de Compras (409 accionables)."""
    try:
        yield
    except accounting_services.PostingConfigurationMissing as exc:
        issues = [{'code': i.code, 'role': i.role, 'subject': i.subject, 'message': i.message, 'params': i.params}
                  for i in exc.issues]
        raise PostingRejected('posting_configuration_missing', '; '.join(i['message'] for i in issues),
                              {'issues': issues}) from exc
    except (accounting_services.FiscalPeriodClosed, accounting_services.DateOutsideFiscalPeriod) as exc:
        raise PostingRejected('fiscal_period_unavailable', str(exc)) from exc
    except accounting_services.JournalValidationError as exc:
        message = next((m[0] for m in exc.errors.values() if m), 'datos no validos.')
        raise PostingRejected('ledger_rejected', 'Contabilidad rechazo el asiento: ' + message) from exc
    except accounting_services.JournalConflict as exc:
        raise PostingRejected('ledger_conflict', str(exc)) from exc
