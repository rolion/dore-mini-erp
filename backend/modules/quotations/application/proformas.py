"""Casos de uso de Proformas: leen Servicios/Clientes por puertos, mutan el agregado y persisten."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from modules.quotations.domain.proforma import (
    DRAFT, PRESENTED, Proforma, ProformaLine, ProformaNotFound, ProformaStateError, ProformaValidationError,
    money,
)


class PriceEditNotAllowed(Exception):
    """El usuario no puede fijar un precio distinto del vigente del servicio."""


@dataclass(frozen=True)
class LineInput:
    quantity: Decimal | None
    id: UUID | None = None
    service_id: UUID | None = None
    unit_price: Decimal | None = None


@dataclass(frozen=True)
class ProformaInput:
    customer_id: UUID
    date: date
    valid_until: date | None
    notes: str
    lines: list[LineInput]


class ProformaService:
    def __init__(self, repository, services, customers, *, can_edit_price: bool, user_id: int | None = None):
        self.repository, self.services, self.customers = repository, services, customers
        self.can_edit_price, self.user_id = can_edit_price, user_id

    # --- lectura -----------------------------------------------------------------------------------------
    def get(self, proforma_id: UUID) -> Proforma:
        proforma = self.repository.get(proforma_id)
        if proforma is None:
            raise ProformaNotFound()
        return proforma

    def allowed_actions(self, proforma: Proforma) -> list[str]:
        if proforma.status == DRAFT:
            return ['edit', 'present']
        if proforma.status == PRESENTED and not self.repository.draft_exists(proforma.number):
            return ['new-version']
        return []

    def versions(self, proforma: Proforma) -> list[Proforma]:
        return self.repository.versions(proforma.number)

    # --- escritura ---------------------------------------------------------------------------------------
    def create(self, data: ProformaInput) -> Proforma:
        name = self._customer(data.customer_id, current=None)
        lines = self._lines(data.lines, existing={})
        proforma = Proforma.create(number='', customer_id=data.customer_id, customer_name=name, date=data.date,
                                   valid_until=data.valid_until, notes=data.notes, lines=lines,
                                   created_by=self.user_id)
        proforma.number = self.repository.next_number()  # al final: un rechazo no consume número
        self.repository.save(proforma)
        return proforma

    def update(self, proforma_id: UUID, data: ProformaInput) -> Proforma:
        proforma = self._locked(proforma_id)
        if proforma.status != DRAFT:
            raise ProformaStateError('Solo se puede editar una proforma en borrador.')
        name = self._customer(data.customer_id, current=proforma)
        lines = self._lines(data.lines, existing={line.id: line for line in proforma.lines})
        proforma.replace_content(customer_id=data.customer_id, customer_name=name, date=data.date,
                                 valid_until=data.valid_until, notes=data.notes, lines=lines)
        self.repository.save(proforma)
        return proforma

    def present(self, proforma_id: UUID) -> Proforma:
        proforma = self._locked(proforma_id)
        proforma.present()
        for previous in self.repository.presented_below(proforma.number, proforma.version):
            previous.supersede()
            self.repository.save(previous)
        self.repository.save(proforma)
        return proforma

    def new_version(self, proforma_id: UUID) -> Proforma:
        proforma = self._locked(proforma_id)
        if self.repository.draft_exists(proforma.number):
            raise ProformaStateError('Ya existe un borrador de este número; edítalo o preséntalo.')
        draft = proforma.new_version()
        self.repository.save(draft)
        return draft

    # --- apoyo -------------------------------------------------------------------------------------------
    def _locked(self, proforma_id: UUID) -> Proforma:
        proforma = self.repository.get(proforma_id, for_update=True)
        if proforma is None:
            raise ProformaNotFound()
        return proforma

    def _customer(self, customer_id: UUID, *, current: Proforma | None) -> str:
        customer = self.customers.get(customer_id)
        if customer is None:
            raise ProformaValidationError({'customer_id': ['El cliente no existe.']})
        if current is not None and current.customer_id == customer_id:
            return current.customer_name
        if not customer.active:
            raise ProformaValidationError({'customer_id': ['El cliente está inactivo.']})
        return customer.name

    def _lines(self, inputs: list[LineInput], *, existing: dict[UUID, ProformaLine]) -> list[ProformaLine]:
        result: list[ProformaLine] = []
        errors: list[dict] = []
        seen: set[UUID] = set()
        for item in inputs:
            if item.id is not None and item.id in seen:
                errors.append({'id': ['Línea repetida.']})
                continue
            if item.id is not None:
                seen.add(item.id)
            frozen = existing.get(item.id) if item.id else None
            if frozen is not None:  # línea ya congelada: no se relee el catálogo
                price = frozen.unit_price if item.unit_price is None else item.unit_price
                self._check_price(price, frozen.unit_price)
                result.append(ProformaLine(frozen.id, frozen.service_id, frozen.description, item.quantity, price,
                                           frozen.treatment_item_id, frozen.piece))
                errors.append({})
                continue
            service = self.services.for_new_use(item.service_id) if item.service_id else None
            if service is None:
                errors.append({'service_id': ['El servicio no existe o está inactivo.']})
                continue
            price = service.base_price if item.unit_price is None else item.unit_price
            self._check_price(price, service.base_price)
            result.append(ProformaLine(uuid4(), service.id, service.name, item.quantity, price))
            errors.append({})
        if any(errors):
            raise ProformaValidationError({'lines': errors})
        return result

    def _check_price(self, price: Decimal, reference: Decimal) -> None:
        if not self.can_edit_price and money(price) != money(reference):
            raise PriceEditNotAllowed()
