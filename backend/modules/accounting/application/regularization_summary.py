"""Resumen serializable de una regularización (comando y API): cantidades e importes, nunca saldo ni utilidad."""
from datetime import date
from decimal import Decimal
from uuid import UUID

from modules.accounting.domain.account import Account
from modules.accounting.domain.catalog import METHOD_CODES
from modules.accounting.domain.regularization import (
    CONFLICT,
    DESTINATION_DIFFERENCE,
    FAILED,
    HistoricalMapping,
    INVALID,
    PENDING,
    Report,
)

DETAIL_STATUSES = (PENDING, CONFLICT, DESTINATION_DIFFERENCE, INVALID)


def _money(value: Decimal) -> str:
    return f'{value:.2f}'


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _coverage(mapping: HistoricalMapping, accounts: dict[UUID, Account]) -> list[dict]:
    """Reglas que se aplicaron, por método (AC-08): qué cuenta y en qué rango de fecha."""
    return [
        {'method': method,
         'rules': [{'account_id': str(rule.account_id),
                    'account': accounts[rule.account_id].name if rule.account_id in accounts else None,
                    'from': _iso(rule.date_from), 'to': _iso(rule.date_to)} for rule in rules]}
        for method, rules in sorted(mapping.rules.items())
    ]


def build_summary(report: Report, accounts: dict[UUID, Account], applied: bool, date_from: date | None = None,
                  date_to: date | None = None, mapping: HistoricalMapping | None = None,
                  accounting_enabled: bool = True) -> dict:
    mapping = mapping or HistoricalMapping({})
    groups = [
        {'status': status, 'origin': origin, 'account_id': account_id or None,
         'account': accounts[UUID(account_id)].name if account_id and UUID(account_id) in accounts else None,
         'currency': currency, 'count': group.count, 'amount': _money(group.amount)}
        for (status, origin, account_id, currency), group in sorted(report.groups().items())
    ]
    details = [
        {'status': item.status, 'outcome': item.outcome, 'origin': item.payment.origin_kind,
         'payment_id': str(item.payment.id), 'document_ref': item.payment.document_ref,
         'payment_date': item.payment.payment_date.isoformat(), 'method': item.payment.method,
         'amount': _money(item.payment.amount), 'currency': item.currency, 'reason': item.reason, 'fields': list(item.fields),
         'error': item.error}
        for item in report.items if item.status in DETAIL_STATUSES or item.outcome == FAILED
    ]
    return {'mode': 'apply' if applied else 'preview', 'total_payments': len(report.items),
            'period': {'date_from': _iso(date_from), 'date_to': _iso(date_to)},
            'mapping_coverage': _coverage(mapping, accounts),
            'unmapped_methods': [code for code in METHOD_CODES if code not in mapping.rules],
            'accounting_enabled': accounting_enabled, 'groups': groups,
            'absent_fields': report.absent_fields(), 'excluded_voided': 0,
            'excluded_voided_note': 'Ni Ventas ni Cobros tienen pagos anulados; ninguno se excluye.',
            'details': details}
