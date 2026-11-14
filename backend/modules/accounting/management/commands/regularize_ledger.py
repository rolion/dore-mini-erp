"""Regulariza en el libro de entradas los pagos históricos de pedidos y proformas (PB-ACC-004).

Sin `--apply` solo previsualiza (no escribe). Con `--apply` crea únicamente los faltantes elegibles y mapeados.
"""
import json
from datetime import date
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from modules.accounting.application.regularization_summary import build_summary
from modules.accounting.application.regularize import RegularizationInProgress, RegularizeLedger
from modules.accounting.domain.regularization import (
    FAILED,
    HistoricalMapping,
    RegularizationInputError,
    parse_mapping,
)
from modules.accounting.infrastructure.adapters import (
    DjangoRegularizationLedger,
    ReceivablesPaymentSource,
    SalesPaymentSource,
)
from modules.accounting.infrastructure.django.repositories import DjangoAccountRepository

EXIT_WITH_ERRORS = 2
ORIGIN_LABELS = {'PRODUCT': 'Productos (pedidos)', 'SERVICE': 'Servicios (proformas)'}
STATUS_LABELS = {
    'missing': 'Faltantes (se crearían)', 'created': 'Creadas', 'existing': 'Existentes',
    'pending': 'Pendientes (sin mapeo)', 'conflict': 'Conflictos (entrada con otros datos)',
    'destination_difference': 'Diferencias de destino', 'invalid': 'No válidos', 'failed': 'Con error',
}


def _date(value: str | None, flag: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise CommandError(f'{flag}: fecha no válida «{value}» (use AAAA-MM-DD).') from None


def render(summary: dict) -> str:
    lines = [f'Regularización del libro — modo: {"APLICAR" if summary["mode"] == "apply" else "PREVISUALIZACIÓN (no se escribió nada)"}',
             f'Pagos revisados: {summary["total_payments"]}', '']
    for status in ('missing', 'created', 'existing', 'pending', 'conflict', 'destination_difference', 'invalid', 'failed'):
        rows = [g for g in summary['groups'] if g['status'] == status]
        if not rows:
            continue
        lines.append(f'{STATUS_LABELS[status]}: {sum(g["count"] for g in rows)} pagos')
        for g in rows:
            account = g['account'] or '— sin cuenta —'
            lines.append(f'  {ORIGIN_LABELS[g["origin"]]} · {account} · {g["currency"]}: {g["count"]} · {g["amount"]}')
    if summary['absent_fields']:
        lines += ['', 'Campos históricos ausentes en los faltantes (no se inventan): ' + ', '.join(
            f'{name}={count}' for name, count in sorted(summary['absent_fields'].items()))]
    lines += ['', summary['excluded_voided_note']]
    if summary['details']:
        lines += ['', 'Detalle de casos que requieren revisión (no se modifican):']
        for d in summary['details']:
            extra = d['error'] or d['reason'] or ', '.join(d['fields'])
            lines.append(f'  [{d["status"]}{"/" + d["outcome"] if d["outcome"] else ""}] {d["origin"]} {d["payment_id"]} '
                         f'{d["payment_date"]} {d["method"]} {d["amount"]} doc={d["document_ref"] or "—"}: {extra}')
    lines += ['', 'Los importes son entradas registradas, no saldo bancario ni utilidad.']
    return '\n'.join(lines)


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--company', required=True, help='UUID de la empresa.')
        parser.add_argument('--from', dest='date_from', help='Fecha efectiva desde (AAAA-MM-DD).')
        parser.add_argument('--to', dest='date_to', help='Fecha efectiva hasta (AAAA-MM-DD).')
        parser.add_argument('--mapping', help='JSON {método: [{"account_id", "from", "to"}]} (explícito, sin cuenta por defecto).')
        parser.add_argument('--apply', action='store_true', help='Crea los faltantes. Sin esta opción solo previsualiza.')
        parser.add_argument('--executed-by', dest='executed_by', help='Quién regulariza (obligatorio con --apply).')
        parser.add_argument('--json', action='store_true', help='Resumen en JSON.')

    def handle(self, *args, **options):
        try:
            company_id = UUID(options['company'])
        except ValueError:
            raise CommandError('--company debe ser un UUID.') from None
        date_from, date_to = _date(options['date_from'], '--from'), _date(options['date_to'], '--to')
        apply = options['apply']
        executed_by = (options['executed_by'] or '').strip()
        if apply and not executed_by:
            raise CommandError('--apply exige --executed-by con quien ejecuta la regularización.')
        if apply and not options['mapping']:
            raise CommandError('--apply exige --mapping: no se asigna ninguna cuenta por defecto.')
        accounts = DjangoAccountRepository(company_id).by_id()
        mapping = self._mapping(options['mapping'], accounts)
        use_case = RegularizeLedger(
            {'PRODUCT': SalesPaymentSource(), 'SERVICE': ReceivablesPaymentSource()}, DjangoRegularizationLedger())
        try:
            if apply:
                report = use_case.apply(company_id, date_from, date_to, mapping, executed_by, timezone.now())
            else:
                report = use_case.plan(company_id, date_from, date_to, mapping)
        except RegularizationInProgress as exc:
            raise CommandError(str(exc)) from exc
        except RegularizationInputError as exc:
            raise CommandError('; '.join(exc.errors)) from exc
        summary = build_summary(report, accounts, apply)
        self.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2) if options['json'] else render(summary))
        if any(item.outcome == FAILED for item in report.items):
            raise SystemExit(EXIT_WITH_ERRORS)

    def _mapping(self, path: str | None, accounts: dict) -> HistoricalMapping:
        if not path:
            return HistoricalMapping({})
        try:
            with open(path, encoding='utf-8') as handle:
                raw = json.load(handle)
        except (OSError, ValueError) as exc:
            raise CommandError(f'--mapping: no se pudo leer el JSON ({exc}).') from exc
        try:
            return parse_mapping(raw, accounts)
        except RegularizationInputError as exc:
            raise CommandError('Mapeo inválido: ' + ' | '.join(exc.errors)) from exc
