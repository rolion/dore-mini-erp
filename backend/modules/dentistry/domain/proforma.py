"""Proforma odontológica (puro: sin Django). Dinero siempre en `Decimal`, a dos decimales.

Es una copia adaptada de la proforma genérica de Cotizaciones (ADR del task): añade la pieza dental por línea
y pertenece a un paciente. Las decisiones del paciente (PB-COT-002) siguen la misma regla que en Cotizaciones.
"""
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID, uuid4

CURRENCY = 'BOB'
DRAFT, PRESENTED, SUPERSEDED = 'draft', 'presented', 'superseded'
STATUSES = (DRAFT, PRESENTED, SUPERSEDED)
MAX_LINES = 200
MAX_QUANTITY = Decimal('9999.99')
MAX_PRICE = Decimal('9999999999.99')
MAX_NOTES = 2000
MAX_PIECE = 20
_CENTS = Decimal('0.01')

# --- decisiones del paciente (PB-COT-002) ---------------------------------------------------------------------
PENDING, ACCEPTED, REJECTED = 'pending', 'accepted', 'rejected'
PARTIALLY_ACCEPTED = 'partially_accepted'
KIND_DECISION, KIND_RECTIFICATION, KIND_CARRIED = 'decision', 'rectification', 'carried'
LINE_ORIGINAL, LINE_CARRIED, LINE_REPLACEMENT, LINE_ADDITIONAL = 'original', 'carried', 'replacement', 'additional'
MEDIA = ('in_person', 'phone', 'message', 'email', 'signed_document', 'other')
MAX_NAME, MAX_REFERENCE, MAX_REASON = 120, 200, 500


class DentalProformaValidationError(Exception):
    def __init__(self, errors: dict):
        self.errors = errors
        super().__init__(errors)


class DentalProformaNotFound(Exception):
    pass


class DentalProformaStateError(Exception):
    """Operación no permitida para el estado actual (se traduce a 409)."""


def money(value: Decimal) -> Decimal:
    return value.quantize(_CENTS, rounding=ROUND_HALF_UP)


def _has_cents_only(value: Decimal) -> bool:
    return value.is_finite() and value == value.quantize(_CENTS)


def clean_piece(value) -> str:
    """Pieza dental: texto libre opcional, recortado, de una línea y de hasta 20 caracteres."""
    if value is None:
        return ''
    if not isinstance(value, str):
        raise ValueError('not text')
    text = value.strip()
    if len(text) > MAX_PIECE or '\n' in text or '\r' in text:
        raise ValueError('invalid piece')
    return text


def line_errors(quantity: Decimal | None, unit_price: Decimal | None, piece=None) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    if quantity is None or not _has_cents_only(quantity) or quantity <= 0 or quantity > MAX_QUANTITY:
        errors['quantity'] = ['Ingresa una cantidad mayor que cero (máximo 9999.99, dos decimales).']
    if unit_price is None or not _has_cents_only(unit_price) or unit_price < 0 or unit_price > MAX_PRICE:
        errors['unit_price'] = ['Ingresa un precio igual o mayor que cero con dos decimales.']
    try:
        clean_piece(piece)
    except ValueError:
        errors['dental_piece'] = [f'La pieza dental debe ser texto de una línea de hasta {MAX_PIECE} caracteres.']
    return errors


@dataclass(frozen=True)
class Decision:
    """Registro inmutable del libro de decisiones de una línea (nunca se edita ni se borra)."""
    id: UUID
    kind: str
    decision: str
    decided_at: datetime
    recorded_by: int | None = None
    recorded_by_name: str = ''
    accepted_by_name: str = ''
    medium: str = ''
    reference: str = ''
    reason: str = ''
    batch_key: UUID | None = None
    source_decision_id: UUID | None = None  # solo en `carried`: registro de la versión anterior


@dataclass(frozen=True)
class DentalProformaLine:
    """Línea con nombre y precio congelados al incorporar el servicio, y pieza dental opcional."""
    id: UUID
    service_id: UUID
    description: str
    quantity: Decimal
    unit_price: Decimal
    dental_piece: str = ''
    origin_line_id: UUID | None = None  # línea de la versión anterior de la que viene
    line_kind: str = LINE_ORIGINAL
    decisions: tuple[Decision, ...] = ()
    collected: bool = False  # PB-COB-001: la línea tiene cobros; no se puede rectificar a rechazada

    @property
    def subtotal(self) -> Decimal:
        return money(self.quantity * self.unit_price)

    @property
    def current_decision(self) -> Decision | None:
        return self.decisions[-1] if self.decisions else None

    @property
    def decision(self) -> str:
        current = self.current_decision
        return current.decision if current else PENDING


def clean_decision_fields(decision, accepted_by_name, medium, reference, reason, *, require_reason=False):
    """Valida y recorta los datos de una decisión; devuelve (campos limpios, errores por campo)."""
    errors: dict[str, list[str]] = {}
    name, medium = (accepted_by_name or '').strip(), (medium or '').strip()
    reference, reason = (reference or '').strip(), (reason or '').strip()
    if decision not in (ACCEPTED, REJECTED):
        errors['decision'] = ['La decisión debe ser aceptada o rechazada.']
    if len(name) > MAX_NAME:
        errors['accepted_by_name'] = [f'Máximo {MAX_NAME} caracteres.']
    if medium and medium not in MEDIA:
        errors['medium'] = ['Elige un medio de aceptación válido.']
    if decision == ACCEPTED:
        if not name:
            errors.setdefault('accepted_by_name', ['Indica quién acepta.'])
        if not medium:
            errors.setdefault('medium', ['Indica el medio de aceptación.'])
    if len(reference) > MAX_REFERENCE:
        errors['reference'] = [f'Máximo {MAX_REFERENCE} caracteres.']
    if len(reason) > MAX_REASON:
        errors['reason'] = [f'Máximo {MAX_REASON} caracteres.']
    if require_reason and not reason:
        errors.setdefault('reason', ['Indica el motivo de la rectificación.'])
    return {'accepted_by_name': name, 'medium': medium, 'reference': reference, 'reason': reason}, errors


def _carry(source: Decision | None) -> tuple[Decision, ...]:
    """Copia la decisión vigente de la línea de origen como registro `carried` de la versión nueva."""
    if source is None:
        return ()
    return (Decision(uuid4(), KIND_CARRIED, source.decision, source.decided_at, source.recorded_by,
                     source.recorded_by_name, source.accepted_by_name, source.medium, source.reference,
                     source.reason, None, source.id),)


@dataclass
class DentalProforma:
    id: UUID
    number: str
    version: int
    status: str
    customer_id: UUID
    patient_name: str
    date: date
    valid_until: date | None = None
    notes: str = ''
    lines: list[DentalProformaLine] = field(default_factory=list)
    created_by: int | None = None

    currency = CURRENCY

    @property
    def total(self) -> Decimal:
        return money(sum((line.subtotal for line in self.lines), Decimal('0')))

    @property
    def totals(self) -> dict[str, Decimal]:
        zero = Decimal('0')
        by_state = {state: money(sum((l.subtotal for l in self.lines if l.decision == state), zero))
                    for state in (ACCEPTED, REJECTED, PENDING)}
        return {'proposed': self.total, 'accepted': by_state[ACCEPTED], 'pending': by_state[PENDING],
                'rejected': by_state[REJECTED]}

    @property
    def acceptance_status(self) -> str:
        states = [line.decision for line in self.lines]
        if states and all(state == ACCEPTED for state in states):
            return ACCEPTED
        if states and all(state == REJECTED for state in states):
            return REJECTED
        return PARTIALLY_ACCEPTED if ACCEPTED in states else PENDING

    def decision_history(self) -> list[tuple[DentalProformaLine, Decision]]:
        rows = [(line, record) for line in self.lines for record in line.decisions]
        return sorted(rows, key=lambda row: row[1].decided_at)

    @classmethod
    def create(cls, *, number: str, customer_id: UUID, patient_name: str, date: date,
               valid_until: date | None = None, notes: str = '', lines=(), created_by: int | None = None):
        proforma = cls(uuid4(), number, 1, DRAFT, customer_id, patient_name, date, created_by=created_by)
        proforma.replace_content(patient_name=patient_name, date=date, valid_until=valid_until, notes=notes,
                                 lines=lines)
        return proforma

    def replace_content(self, *, patient_name: str, date: date, valid_until: date | None, notes: str, lines,
                        origins: dict | None = None) -> None:
        if self.status != DRAFT:
            raise DentalProformaStateError('Solo se puede editar una proforma en borrador.')
        lines = list(lines)
        errors: dict = {}
        if valid_until is not None and valid_until < date:
            errors['valid_until'] = ['La vigencia no puede ser anterior a la fecha.']
        if len(notes) > MAX_NOTES:
            errors['notes'] = [f'Máximo {MAX_NOTES} caracteres.']
        if len(lines) > MAX_LINES:
            errors['lines'] = [f'Máximo {MAX_LINES} líneas.']
        else:
            per_line = [line_errors(line.quantity, line.unit_price, line.dental_piece) for line in lines]
            if any(per_line):
                errors['lines'] = per_line
        if errors:
            raise DentalProformaValidationError(errors)
        lines = self._classify([replace(line, dental_piece=clean_piece(line.dental_piece)) for line in lines],
                               origins or {})
        self.patient_name, self.date, self.valid_until, self.notes = patient_name, date, valid_until, notes
        self.lines = lines

    def _classify(self, lines: list[DentalProformaLine], origins: dict) -> list[DentalProformaLine]:
        """INV-07: recalcula el tipo de cada línea frente a la versión anterior y bloquea las aceptadas heredadas."""
        new_by_id = {line.id: line for line in lines}
        for current in self.lines:
            if current.origin_line_id and current.decision == ACCEPTED:
                kept = new_by_id.get(current.id)
                if kept is None or (kept.quantity, kept.unit_price) != (current.quantity, current.unit_price):
                    raise DentalProformaStateError(
                        'Una línea aceptada de la versión anterior no se puede editar ni quitar; rectifícala primero.')
        result = []
        for line in lines:
            if line.origin_line_id is None:
                kind = LINE_ORIGINAL if self.version == 1 else LINE_ADDITIONAL
                result.append(replace(line, line_kind=kind, decisions=()))
                continue
            origin = origins.get(line.origin_line_id)
            if origin is None:
                raise DentalProformaValidationError({'lines': [{'id': ['La línea de origen no existe.']}]})
            if (line.quantity, line.unit_price) != (origin.quantity, origin.unit_price):
                result.append(replace(line, line_kind=LINE_REPLACEMENT, decisions=()))
                continue
            source = origin.current_decision
            keep = bool(line.decisions) and source is not None and line.decisions[-1].source_decision_id == source.id
            result.append(replace(line, line_kind=LINE_CARRIED, decisions=line.decisions if keep else _carry(source)))
        return result

    def present(self) -> None:
        if self.status != DRAFT:
            raise DentalProformaStateError('Solo se puede presentar una proforma en borrador.')
        if not self.lines:
            raise DentalProformaValidationError({'lines': ['Agrega al menos una línea para presentar la proforma.']})
        self.status = PRESENTED

    def supersede(self) -> None:
        if self.status != PRESENTED:
            raise DentalProformaStateError('Solo una proforma presentada puede ser reemplazada.')
        self.status = SUPERSEDED

    def new_version(self) -> 'DentalProforma':
        """Borrador `version + 1` con las líneas ya congeladas (incluida la pieza dental) y su vínculo de origen."""
        if self.status != PRESENTED:
            raise DentalProformaStateError('Solo se puede crear una versión nueva desde una proforma presentada.')
        copied = [replace(line, id=uuid4(), origin_line_id=line.id, line_kind=LINE_CARRIED,
                          decisions=_carry(line.current_decision)) for line in self.lines]
        return DentalProforma(uuid4(), self.number, self.version + 1, DRAFT, self.customer_id, self.patient_name,
                              self.date, self.valid_until, self.notes, copied, self.created_by)

    # --- decisiones (INV-01..05) ----------------------------------------------------------------------------
    def decide(self, line_ids, decision: str, *, now: datetime, recorded_by: int | None = None,
               recorded_by_name: str = '', accepted_by_name: str = '', medium: str = '', reference: str = '',
               reason: str = '', batch_key: UUID | None = None) -> None:
        if self.status != PRESENTED:
            raise DentalProformaStateError('Solo se pueden registrar decisiones en una proforma presentada vigente.')
        ids = list(line_ids)
        by_id = {line.id: line for line in self.lines}
        fields, errors = clean_decision_fields(decision, accepted_by_name, medium, reference, reason)
        if not ids:
            errors['line_ids'] = ['Selecciona al menos una línea.']
        elif len(set(ids)) != len(ids):
            errors['line_ids'] = ['Hay líneas repetidas.']
        elif any(line_id not in by_id for line_id in ids):
            errors['line_ids'] = ['Alguna línea no pertenece a la proforma.']
        if errors:
            raise DentalProformaValidationError(errors)
        if any(by_id[line_id].decision != PENDING for line_id in ids):
            raise DentalProformaStateError('Alguna línea ya tiene una decisión; usa una rectificación.')
        chosen = set(ids)
        self.lines = [
            replace(line, decisions=line.decisions + (Decision(
                uuid4(), KIND_DECISION, decision, now, recorded_by, recorded_by_name, batch_key=batch_key,
                **fields),)) if line.id in chosen else line
            for line in self.lines]

    def rectify(self, line_id: UUID, decision: str, *, now: datetime, recorded_by: int | None = None,
                recorded_by_name: str = '', accepted_by_name: str = '', medium: str = '', reference: str = '',
                reason: str = '', batch_key: UUID | None = None) -> None:
        if self.status != PRESENTED:
            raise DentalProformaStateError('Solo se puede rectificar en la proforma presentada vigente.')
        line = next((l for l in self.lines if l.id == line_id), None)
        fields, errors = clean_decision_fields(decision, accepted_by_name, medium, reference, reason,
                                               require_reason=True)
        if line is None:
            errors['line_id'] = ['La línea no pertenece a la proforma.']
        if errors:
            raise DentalProformaValidationError(errors)
        if line.collected:
            raise DentalProformaStateError('La línea tiene cobros registrados: no se puede rectificar.')
        if line.decision == PENDING:
            raise DentalProformaStateError('La línea aún no tiene una decisión que rectificar.')
        if line.decision == decision:
            raise DentalProformaStateError('La línea ya tiene esa decisión.')
        record = Decision(uuid4(), KIND_RECTIFICATION, decision, now, recorded_by, recorded_by_name,
                          batch_key=batch_key, **fields)
        self.lines = [replace(l, decisions=l.decisions + (record,)) if l.id == line_id else l for l in self.lines]
