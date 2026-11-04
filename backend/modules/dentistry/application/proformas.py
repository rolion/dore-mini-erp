"""Casos de uso de proformas odontológicas: comprueban al paciente, leen Servicios por puerto y persisten."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from modules.dentistry.domain.proforma import (
    DRAFT, PRESENTED, DentalProforma, DentalProformaLine, DentalProformaNotFound, DentalProformaStateError,
    DentalProformaValidationError, money,
)


class PriceEditNotAllowed(Exception):
    """El usuario no puede fijar un precio distinto del vigente del servicio."""


@dataclass(frozen=True)
class LineInput:
    quantity: Decimal | None
    id: UUID | None = None
    service_id: UUID | None = None
    unit_price: Decimal | None = None
    dental_piece: str | None = None  # None: no se envió (se conserva la pieza guardada)


@dataclass(frozen=True)
class DentalProformaInput:
    date: date
    valid_until: date | None
    notes: str
    lines: list[LineInput]


class DentalProformaService:
    def __init__(self, repository, services, patients, *, can_edit_price: bool, user_id: int | None = None):
        self.repository, self.services, self.patients = repository, services, patients
        self.can_edit_price, self.user_id = can_edit_price, user_id

    # --- lectura -----------------------------------------------------------------------------------------
    def get(self, proforma_id: UUID) -> DentalProforma:
        proforma = self.repository.get(proforma_id)
        if proforma is None:
            raise DentalProformaNotFound()
        return proforma

    def allowed_actions(self, proforma: DentalProforma) -> list[str]:
        if proforma.status == DRAFT:
            return ['edit', 'present']
        if proforma.status == PRESENTED and not self.repository.draft_exists(proforma.number):
            return ['new-version']
        return []

    def versions(self, proforma: DentalProforma) -> list[DentalProforma]:
        return self.repository.versions(proforma.number)

    # --- escritura ---------------------------------------------------------------------------------------
    def create(self, customer_id: UUID, data: DentalProformaInput) -> DentalProforma:
        name = self.patients.require_active(customer_id)
        lines = self._lines(data.lines, existing={})
        proforma = DentalProforma.create(number='', customer_id=customer_id, patient_name=name, date=data.date,
                                         valid_until=data.valid_until, notes=data.notes, lines=lines,
                                         created_by=self.user_id)
        proforma.number = self.repository.next_number()  # al final: un rechazo no consume número
        self.repository.save(proforma)
        return proforma

    def update(self, proforma_id: UUID, data: DentalProformaInput) -> DentalProforma:
        proforma = self._locked(proforma_id)
        if proforma.status != DRAFT:
            raise DentalProformaStateError('Solo se puede editar una proforma en borrador.')
        name = self.patients.require_active(proforma.customer_id)
        lines = self._lines(data.lines, existing={line.id: line for line in proforma.lines})
        proforma.replace_content(patient_name=name, date=data.date, valid_until=data.valid_until,
                                 notes=data.notes, lines=lines)
        self.repository.save(proforma)
        return proforma

    def present(self, proforma_id: UUID) -> DentalProforma:
        proforma = self._locked(proforma_id)
        self.patients.require_active(proforma.customer_id)
        proforma.present()
        for previous in self.repository.presented_below(proforma.number, proforma.version):
            previous.supersede()
            self.repository.save(previous)
        self.repository.save(proforma)
        return proforma

    def new_version(self, proforma_id: UUID) -> DentalProforma:
        proforma = self._locked(proforma_id)
        self.patients.require_active(proforma.customer_id)
        if self.repository.draft_exists(proforma.number):
            raise DentalProformaStateError('Ya existe un borrador de este número; edítalo o preséntalo.')
        draft = proforma.new_version()
        self.repository.save(draft)
        return draft

    # --- apoyo -------------------------------------------------------------------------------------------
    def _locked(self, proforma_id: UUID) -> DentalProforma:
        proforma = self.repository.get(proforma_id, for_update=True)
        if proforma is None:
            raise DentalProformaNotFound()
        return proforma

    def _lines(self, inputs: list[LineInput], *, existing: dict[UUID, DentalProformaLine]) -> list[DentalProformaLine]:
        result: list[DentalProformaLine] = []
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
                piece = frozen.dental_piece if item.dental_piece is None else item.dental_piece
                result.append(DentalProformaLine(frozen.id, frozen.service_id, frozen.description, item.quantity,
                                                 price, piece))
                errors.append({})
                continue
            service = self.services.for_new_use(item.service_id) if item.service_id else None
            if service is None:
                errors.append({'service_id': ['El servicio no existe o está inactivo.']})
                continue
            price = service.base_price if item.unit_price is None else item.unit_price
            self._check_price(price, service.base_price)
            result.append(DentalProformaLine(uuid4(), service.id, service.name, item.quantity, price,
                                             item.dental_piece or ''))
            errors.append({})
        if any(errors):
            raise DentalProformaValidationError({'lines': errors})
        return result

    def _check_price(self, price: Decimal, reference: Decimal) -> None:
        if not self.can_edit_price and money(price) != money(reference):
            raise PriceEditNotAllowed()
