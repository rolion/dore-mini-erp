"""Agregado Evaluation (odontograma) de PB-ODO-002. Sin dependencias de Django."""
from dataclasses import dataclass, field, replace
from datetime import date
from uuid import UUID, uuid4

from . import odontogram_catalog as catalog

DRAFT, CONFIRMED = 'draft', 'confirmed'
MAX_DIAGNOSIS, MAX_NOTES, MAX_REASON = 500, 1000, 500


class EvaluationValidationError(Exception):
    def __init__(self, errors: dict):
        super().__init__(errors)
        self.errors = errors


class EvaluationNotFound(Exception):
    pass


class EvaluationStateError(Exception):
    pass


@dataclass(frozen=True)
class Finding:
    piece: int
    condition: str
    surfaces: tuple[str, ...] = ()
    diagnosis: str = ''
    notes: str = ''
    id: UUID | None = None


@dataclass(frozen=True)
class GeneralFinding:
    diagnosis: str
    notes: str = ''
    id: UUID | None = None


def _text(value, limit: int) -> str | None:
    if value is None:
        return ''
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if len(value) <= limit else None


def _clean_finding(raw: dict, dentition: str, label: str, errors: list[str]) -> Finding | None:
    piece, code = raw.get('piece'), raw.get('condition')
    start = len(errors)
    if not isinstance(piece, int) or isinstance(piece, bool) or piece not in catalog.teeth_for(dentition):
        errors.append(f'{label}: la pieza {piece} no es válida para la dentición {dentition}.')
        return None
    label = f'Pieza {piece}'
    condition = catalog.BY_CODE.get(code)
    if condition is None:
        errors.append(f'{label}: la condición {code!r} no existe en el catálogo.')
        return None
    surfaces = raw.get('surfaces') or []
    if not isinstance(surfaces, (list, tuple)) or len(set(surfaces)) != len(surfaces):
        errors.append(f'{label}: las superficies deben ser una lista sin repetidos.')
    else:
        allowed = catalog.valid_surfaces(piece)
        invalid = [s for s in surfaces if s not in allowed]
        if invalid:
            errors.append(f'{label}: superficie no válida para esta pieza ({", ".join(map(str, invalid))}); '
                          f'admite {", ".join(allowed)}.')
        elif condition.scope == catalog.WHOLE and surfaces:
            errors.append(f'{label}: {condition.name} se registra en la pieza completa, sin superficies.')
        elif condition.scope == catalog.ON_SURFACES and not surfaces:
            errors.append(f'{label}: {condition.name} requiere al menos una superficie.')
    diagnosis, notes = _text(raw.get('diagnosis'), MAX_DIAGNOSIS), _text(raw.get('notes'), MAX_NOTES)
    if diagnosis is None:
        errors.append(f'{label}: el diagnóstico debe ser texto de hasta {MAX_DIAGNOSIS} caracteres.')
    if notes is None:
        errors.append(f'{label}: las notas deben ser texto de hasta {MAX_NOTES} caracteres.')
    elif condition.requires_note and not notes:
        errors.append(f'{label}: {condition.name} exige una nota.')
    if len(errors) > start:
        return None
    ordered = tuple(sorted(surfaces, key=catalog.SURFACE_ORDER.__getitem__))
    return Finding(piece, condition.code, ordered, diagnosis, notes)


def _check_piece_rules(findings: list[Finding], errors: list[str]) -> None:
    by_piece: dict[int, list[Finding]] = {}
    for finding in findings:
        by_piece.setdefault(finding.piece, []).append(finding)
    for piece, items in by_piece.items():
        codes = [item.condition for item in items]
        if len(set(codes)) != len(codes):
            errors.append(f'Pieza {piece}: hay una condición repetida.')
            continue
        for i, first in enumerate(items):
            for second in items[i + 1:]:
                if not catalog.compatible(first.condition, second.condition):
                    errors.append(f'Pieza {piece}: {catalog.BY_CODE[first.condition].name} no puede coexistir '
                                  f'con {catalog.BY_CODE[second.condition].name}.')
                elif (first.condition in catalog.SURFACE_EXCLUSIVE and second.condition in catalog.SURFACE_EXCLUSIVE
                      and set(first.surfaces) & set(second.surfaces)):
                    errors.append(f'Pieza {piece}: caries y obturación no pueden compartir superficie.')


def clean_content(dentition, clinical_date, findings, general_findings, today: date):
    """Valida y normaliza el contenido de una evaluación; lanza EvaluationValidationError con errores por campo."""
    errors: dict[str, list[str]] = {}
    if dentition not in (code for code, _ in catalog.DENTITIONS):
        errors['dentition'] = ['Elige dentición permanente, temporal o mixta.']
    if not isinstance(clinical_date, date):
        errors['clinical_date'] = ['La fecha clínica es obligatoria.']
    elif clinical_date > today:
        errors['clinical_date'] = ['La fecha clínica no puede ser futura.']
    finding_errors: list[str] = []
    cleaned: list[Finding] = []
    if 'dentition' not in errors:
        for index, raw in enumerate(findings or [], start=1):
            finding = _clean_finding(raw, dentition, f'Hallazgo {index}', finding_errors)
            if finding is not None:
                cleaned.append(finding)
        if not finding_errors:
            _check_piece_rules(cleaned, finding_errors)
    if finding_errors:
        errors['findings'] = finding_errors
    general_errors: list[str] = []
    general: list[GeneralFinding] = []
    for index, raw in enumerate(general_findings or [], start=1):
        diagnosis, notes = _text(raw.get('diagnosis'), MAX_DIAGNOSIS), _text(raw.get('notes'), MAX_NOTES)
        if not diagnosis:
            general_errors.append(f'Hallazgo general {index}: el diagnóstico es obligatorio (hasta {MAX_DIAGNOSIS}).')
        elif notes is None:
            general_errors.append(f'Hallazgo general {index}: las notas admiten hasta {MAX_NOTES} caracteres.')
        else:
            general.append(GeneralFinding(diagnosis, notes))
    if general_errors:
        errors['general_findings'] = general_errors
    if errors:
        raise EvaluationValidationError(errors)
    return cleaned, general


@dataclass
class Evaluation:
    customer_id: UUID
    dentition: str
    clinical_date: date
    sequence: int = 0
    status: str = DRAFT
    professional_id: UUID | None = None
    findings: list[Finding] = field(default_factory=list)
    general_findings: list[GeneralFinding] = field(default_factory=list)
    amends_id: UUID | None = None
    amendment_reason: str = ''
    catalog_version: int = catalog.CATALOG_VERSION
    id: UUID = field(default_factory=uuid4)

    @classmethod
    def create(cls, customer_id, dentition, clinical_date, professional_id, findings, general_findings,
               today: date) -> 'Evaluation':
        cleaned, general = clean_content(dentition, clinical_date, findings, general_findings, today)
        return cls(customer_id, dentition, clinical_date, professional_id=professional_id,
                   findings=cleaned, general_findings=general)

    def ensure_draft(self) -> None:
        if self.status != DRAFT:
            raise EvaluationStateError('La evaluación confirmada no se puede modificar; corrígela con una enmienda.')

    def replace_content(self, dentition, clinical_date, professional_id, findings, general_findings,
                        today: date) -> None:
        self.ensure_draft()
        cleaned, general = clean_content(dentition, clinical_date, findings, general_findings, today)
        self.dentition, self.clinical_date, self.professional_id = dentition, clinical_date, professional_id
        self.findings, self.general_findings = cleaned, general

    def ensure_discardable(self) -> None:
        self.ensure_draft()

    def confirm(self) -> None:
        self.ensure_draft()
        if not self.findings and not self.general_findings:
            raise EvaluationValidationError({'findings': ['Registra al menos un hallazgo antes de confirmar.']})
        self.status = CONFIRMED

    def amend(self, reason) -> 'Evaluation':
        """Nueva evaluación en borrador que corrige a esta (confirmada); esta queda intacta."""
        if self.status != CONFIRMED:
            raise EvaluationStateError('Solo se corrige una evaluación confirmada.')
        text = reason.strip() if isinstance(reason, str) else ''
        if not text or len(text) > MAX_REASON:
            raise EvaluationValidationError({'reason': [f'Indica el motivo de la corrección (hasta {MAX_REASON}).']})
        return Evaluation(
            self.customer_id, self.dentition, self.clinical_date, professional_id=self.professional_id,
            findings=[replace(f, id=None) for f in self.findings],
            general_findings=[replace(g, id=None) for g in self.general_findings],
            amends_id=self.id, amendment_reason=text)
