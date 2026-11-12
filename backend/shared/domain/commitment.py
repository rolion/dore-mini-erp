"""Compromiso cobrable: lectura inmutable de una proforma por otros módulos (sin Django).

Las fuentes (`quotations`, `dentistry`) construyen estos DTO desde su fachada `services`; Cobros solo los consume.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

ACCEPTED = 'accepted'
PRESENTED = 'presented'


@dataclass(frozen=True)
class CommitmentLine:
    line_id: UUID  # id de la línea en la versión vigente
    lineage_id: UUID  # id de la línea en la primera versión: clave estable entre versiones
    description: str
    piece: str
    amount: Decimal
    decision: str  # pending | accepted | rejected
    collected: bool = False


@dataclass(frozen=True)
class CommitmentSnapshot:
    kind: str
    number: str
    version: int
    status: str
    customer_id: UUID
    customer_name: str
    date: date
    lines: tuple[CommitmentLine, ...]
    proforma_id: UUID | None = None  # id de la versión vigente de la proforma (para volver a ella)

    @property
    def collectible(self) -> bool:
        return self.status == PRESENTED


@dataclass(frozen=True)
class VersionData:
    """Una versión de proforma ya reducida a lo que Cobros necesita.

    `lines`: tuplas (id, id de origen, descripción, pieza, importe, decisión, cobrada).
    """
    number: str
    version: int
    status: str
    customer_id: UUID
    customer_name: str
    date: date
    lines: tuple[tuple[UUID, UUID | None, str, str, Decimal, str, bool], ...]
    proforma_id: UUID | None = None


def build_snapshots(kind: str, versions: list[VersionData]) -> dict[str, CommitmentSnapshot]:
    """Una instantánea por número: la versión presentada vigente, o la más reciente si no hay ninguna."""
    by_number: dict[str, list[VersionData]] = {}
    for version in versions:
        by_number.setdefault(version.number, []).append(version)
    result: dict[str, CommitmentSnapshot] = {}
    for number, group in by_number.items():
        origin_of = {line[0]: line[1] for version in group for line in version.lines}

        def root(line_id: UUID, origin_of=origin_of) -> UUID:
            seen = set()
            while origin_of.get(line_id) is not None and line_id not in seen:
                seen.add(line_id)
                line_id = origin_of[line_id]
            return line_id

        presented = [v for v in group if v.status == PRESENTED]
        chosen = max(presented or group, key=lambda v: v.version)
        lines = tuple(CommitmentLine(line_id, root(line_id), description, piece, amount, decision, collected)
                      for line_id, _origin, description, piece, amount, decision, collected in chosen.lines)
        result[number] = CommitmentSnapshot(kind, number, chosen.version, chosen.status, chosen.customer_id,
                                            chosen.customer_name, chosen.date, lines, chosen.proforma_id)
    return result
