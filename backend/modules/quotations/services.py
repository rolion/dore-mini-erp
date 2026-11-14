"""Fachada pública de Cotizaciones: lectura de compromisos cobrables para Cobros (PB-COB-001).

Devuelve DTO inmutables (`shared.domain.commitment`), nunca entidades ni modelos; todo filtra por empresa.
"""
from collections.abc import Iterable
from uuid import UUID

from modules.quotations.domain.proforma import Proforma
from modules.quotations.infrastructure.django.models import ProformaLineModel, ProformaModel
from modules.quotations.infrastructure.django.repositories import DjangoProformaRepository
from shared.domain.commitment import CommitmentSnapshot, VersionData, build_snapshots

KIND = 'quotation'


def _version(proforma: Proforma) -> VersionData:
    lines = tuple((l.id, l.origin_line_id, l.description, l.piece, l.subtotal, l.decision, l.collected)
                  for l in proforma.lines)
    return VersionData(proforma.number, proforma.version, proforma.status, proforma.customer_id,
                       proforma.customer_name, proforma.date, lines, proforma.id)


def get_commitments(company_id: UUID, numbers: Iterable[str]) -> dict[str, CommitmentSnapshot]:
    """Instantáneas de varias proformas (por número) en pocas consultas; los números ajenos no aparecen."""
    numbers = list(set(numbers))
    if not numbers:
        return {}
    versions = DjangoProformaRepository(company_id).versions_of(numbers)
    return build_snapshots(KIND, [_version(p) for p in versions])


def get_commitment(company_id: UUID, number: str) -> CommitmentSnapshot | None:
    return get_commitments(company_id, [number]).get(number)


def lock_commitment(company_id: UUID, number: str) -> CommitmentSnapshot | None:
    """Como `get_commitment`, pero bloquea las cabeceras de las versiones (usar dentro de una transacción).

    Serializa el cobro frente a una rectificación o un versionado de la misma proforma.
    """
    locked = list(ProformaModel.objects.select_for_update().filter(
        company_id=company_id, number=number).values_list('id', flat=True))
    return get_commitment(company_id, number) if locked else None


def mark_lines_collected(company_id: UUID, line_ids: Iterable[UUID]) -> None:
    """Marca las líneas (de la versión vigente) como cobradas: dejan de poder rectificarse a rechazadas."""
    pending = list(line_ids)
    while pending:  # también las copias en versiones posteriores (p. ej. un borrador ya creado)
        ProformaLineModel.objects.filter(proforma__company_id=company_id, pk__in=pending).update(collected=True)
        pending = list(ProformaLineModel.objects.filter(
            proforma__company_id=company_id, origin_line_id__in=pending, collected=False).values_list('id', flat=True))
