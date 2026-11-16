"""Diagnóstico de solo lectura de la transición del libro a partida doble (CONT-07, Etapa 1).

No escribe nada. Inventaría cuentas y entradas por empresa, concilia contra los pagos de origen y clasifica cada
entrada como convertible (con regla explícita), histórica (anterior al corte) o pendiente (con motivo).
"""
import json
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError

from modules.accounting.application.transition_diagnosis import DiagnoseTransition
from modules.accounting.domain.transition import TransitionMapping, TransitionMappingError, parse_transition_mapping
from modules.accounting.infrastructure.adapters import (
    DjangoTransitionReader,
    ReceivablesPaymentSource,
    SalesPaymentSource,
)


def _no_duplicate_keys(pairs):
    keys = [key for key, _ in pairs]
    duplicated = sorted({key for key in keys if keys.count(key) > 1})
    if duplicated:
        raise ValueError(f'clave repetida: {", ".join(duplicated)}')
    return dict(pairs)


def render(report: dict) -> str:
    lines = [f'Empresa {report["company_id"]} — corte: {report["cutoff_date"] or "SIN CORTE"}']
    if report['blocked_without_cutoff']:
        lines.append('  BLOQUEADA: tiene entradas y no tiene fecha de corte; nada se puede convertir.')
    a, e = report['accounts'], report['entries']
    lines.append(f'  Cuentas: {a["total"]} (activas {a["active"]}, con tipo {a["with_kind"]}, sin tipo {a["without_kind"]}, '
                 f'con movimientos {a["with_entries"]}) · apertura total {a["opening_total"]}')
    lines.append(f'  Entradas: {e["total"]} · {e["amount"]} · regularizadas {e["regularized"]} · '
                 f'sin clasificación {e["without_classification"]}')
    for shape, row in e['by_shape'].items():
        lines.append(f'    {shape}: {row["count"]} · {row["amount"]}')
    for state, row in report['states'].items():
        lines.append(f'  {state}: {row["count"]} · {row["amount"]}')
    for reason, count in report['reasons'].items():
        lines.append(f'    motivo {reason}: {count}')
    for key, row in report['source_without_entry'].items():
        lines.append(f'  Pagos de origen sin entrada {key}: {row["count"]} · {row["amount"]}')
    for opening in report['openings']:
        lines.append(f'  Apertura {opening["account_id"]}: {opening["amount"]} → {opening["state"]}'
                     f'{" (" + opening["reason"] + ")" if opening["reason"] else ""}')
    return '\n'.join(lines)


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--company', help='UUID de la empresa. Sin esta opción, diagnostica todas (una por una).')
        parser.add_argument('--mapping', help='JSON {money_accounts, counterparts, opening_equity} (solo con --company).')
        parser.add_argument('--json', action='store_true', help='Resultado en JSON (incluye el detalle de pendientes).')

    def handle(self, *args, **options):
        use_case = DiagnoseTransition(DjangoTransitionReader(),
                                      {'PRODUCT': SalesPaymentSource(), 'SERVICE': ReceivablesPaymentSource()})
        if options['mapping'] and not options['company']:
            raise CommandError('--mapping exige --company: las reglas son por empresa.')
        if options['company']:
            try:
                companies = [UUID(options['company'])]
            except ValueError:
                raise CommandError('--company debe ser un UUID.') from None
        else:
            companies = use_case.company_ids()
        reports = []
        for company_id in companies:
            mapping = self._mapping(options['mapping'], company_id)
            reports.append(use_case.diagnose(company_id, mapping))
        if options['json']:
            self.stdout.write(json.dumps({'companies': reports}, ensure_ascii=False, indent=2))
        else:
            self.stdout.write('\n\n'.join(render(r) for r in reports) or 'Sin empresas con datos de Contabilidad.')

    def _mapping(self, path: str | None, company_id: UUID) -> TransitionMapping:
        if not path:
            return TransitionMapping()
        try:
            with open(path, encoding='utf-8') as handle:
                raw = json.load(handle, object_pairs_hook=_no_duplicate_keys)
        except (OSError, ValueError) as exc:
            raise CommandError(f'--mapping: no se pudo leer el JSON ({exc}).') from exc
        account_ids = {a.id for a in DjangoTransitionReader().accounts(company_id)}
        try:
            return parse_transition_mapping(raw, account_ids)
        except TransitionMappingError as exc:
            raise CommandError('Mapeo inválido: ' + ' | '.join(exc.errors)) from exc
