"""Catálogo clínico del odontograma (PB-ODO-002).

PROVISIONAL: lista inicial pendiente de validación por el odontólogo (ver PLAN-2026-11-26-registrar-diagnostico-
odontograma-inicial). Todo lo que depende del criterio clínico vive aquí; cambiarlo no toca la lógica del agregado.
Los hallazgos guardan el `code`, nunca la etiqueta, y cada evaluación guarda `CATALOG_VERSION`.
"""
from dataclasses import dataclass

CATALOG_VERSION = 1
PENDING_CLINICAL_VALIDATION = True

PERMANENT, TEMPORARY, MIXED = 'permanent', 'temporary', 'mixed'
DENTITIONS = ((PERMANENT, 'Permanente'), (TEMPORARY, 'Temporal'), (MIXED, 'Mixta'))

# FDI: permanentes 11-18, 21-28, 31-38, 41-48; temporales 51-55, 61-65, 71-75, 81-85.
PERMANENT_TEETH = tuple(quadrant * 10 + n for quadrant in (1, 2, 3, 4) for n in range(1, 9))
TEMPORARY_TEETH = tuple(quadrant * 10 + n for quadrant in (5, 6, 7, 8) for n in range(1, 6))

SURFACES = (
    ('M', 'Mesial'), ('D', 'Distal'), ('V', 'Vestibular'), ('O', 'Oclusal'), ('I', 'Incisal'),
    ('P', 'Palatina'), ('L', 'Lingual'),
)
SURFACE_ORDER = {code: index for index, (code, _) in enumerate(SURFACES)}

WHOLE, ON_SURFACES, EITHER = 'whole', 'surfaces', 'either'


@dataclass(frozen=True)
class Condition:
    code: str
    name: str
    abbr: str
    color: str
    scope: str
    requires_note: bool = False
    compatible: frozenset = frozenset()


CONDITIONS = (
    Condition('healthy', 'Sano', 'SAN', 'success', WHOLE),
    Condition('caries', 'Caries', 'CAR', 'danger', ON_SURFACES,
              compatible=frozenset({'filling', 'endodontics', 'fracture', 'other'})),
    Condition('filling', 'Obturación', 'OBT', 'info', ON_SURFACES,
              compatible=frozenset({'caries', 'endodontics', 'fracture', 'other'})),
    Condition('crown', 'Corona', 'COR', 'warning', WHOLE,
              compatible=frozenset({'endodontics', 'implant', 'fracture', 'other'})),
    Condition('missing', 'Ausente', 'AUS', 'secondary', WHOLE),
    Condition('endodontics', 'Endodoncia', 'END', 'primary', WHOLE,
              compatible=frozenset({'caries', 'filling', 'crown', 'fracture', 'other'})),
    Condition('implant', 'Implante', 'IMP', 'dark', WHOLE, compatible=frozenset({'crown', 'other'})),
    Condition('fracture', 'Fractura', 'FRA', 'danger-subtle', EITHER,
              compatible=frozenset({'caries', 'filling', 'crown', 'endodontics', 'other'})),
    Condition('other', 'Otro', 'OTR', 'light', EITHER, requires_note=True,
              compatible=frozenset({'caries', 'filling', 'crown', 'endodontics', 'implant', 'fracture'})),
)
BY_CODE = {condition.code: condition for condition in CONDITIONS}
# Pares caries/obturación no pueden compartir superficie.
SURFACE_EXCLUSIVE = frozenset({'caries', 'filling'})


def teeth_for(dentition: str) -> tuple[int, ...]:
    if dentition == PERMANENT:
        return PERMANENT_TEETH
    if dentition == TEMPORARY:
        return TEMPORARY_TEETH
    return PERMANENT_TEETH + TEMPORARY_TEETH


def is_temporary(piece: int) -> bool:
    return piece in TEMPORARY_TEETH


def is_anterior(piece: int) -> bool:
    return piece % 10 <= 3


def is_upper(piece: int) -> bool:
    return piece // 10 in (1, 2, 5, 6)


def tooth_type(piece: int) -> str:
    position = piece % 10
    if position <= 2:
        return 'incisor'
    if position == 3:
        return 'canine'
    if is_temporary(piece):
        return 'molar'
    return 'premolar' if position <= 5 else 'molar'


def valid_surfaces(piece: int) -> tuple[str, ...]:
    """Superficies que admite la pieza: M, D, V, I (anteriores) u O (posteriores) y P (superior) o L (inferior)."""
    return ('M', 'D', 'V', 'I' if is_anterior(piece) else 'O', 'P' if is_upper(piece) else 'L')


def compatible(first: str, second: str) -> bool:
    return second in BY_CODE[first].compatible and first in BY_CODE[second].compatible


def as_dict() -> dict:
    return {
        'catalog_version': CATALOG_VERSION,
        'pending_clinical_validation': PENDING_CLINICAL_VALIDATION,
        'dentitions': [{'code': code, 'name': name} for code, name in DENTITIONS],
        'surfaces': [{'code': code, 'name': name} for code, name in SURFACES],
        'conditions': [{'code': c.code, 'name': c.name, 'abbr': c.abbr, 'color': c.color, 'scope': c.scope,
                        'requires_note': c.requires_note} for c in CONDITIONS],
        'teeth': {'permanent': list(PERMANENT_TEETH), 'temporary': list(TEMPORARY_TEETH)},
    }
