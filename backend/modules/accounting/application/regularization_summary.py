"""Resumen serializable de una regularización (comando y API): cantidades e importes, nunca saldo ni utilidad."""
from decimal import Decimal
from uuid import UUID

from modules.accounting.domain.account import Account
from modules.accounting.domain.regularization import (
    CONFLICT,
    DESTINATION_DIFFERENCE,
    FAILED,
    INVALID,
    PENDING,
    Report,
)

DETAIL_STATUSES = (PENDING, CONFLICT, DESTINATION_DIFFERENCE, INVALID)


def _money(value: Decimal) -> str:
    return f'{value:.2f}'


def build_summary(report: Report, accounts: dict[UUID, Account], applied: bool) -> dict:
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
    return {'mode': 'apply' if applied else 'preview', 'total_payments': len(report.items), 'groups': groups,
            'absent_fields': report.absent_fields(), 'excluded_voided': 0,
            'excluded_voided_note': 'Ni Ventas ni Cobros tienen pagos anulados; ninguno se excluye.',
            'details': details}
