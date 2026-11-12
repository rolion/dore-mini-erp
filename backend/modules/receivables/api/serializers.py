from rest_framework import serializers

from modules.receivables.application.collections import CommitmentView, PaymentInput
from modules.receivables.domain.obligation import MAX_REFERENCE, Payment

CURRENCY = 'BOB'


class AllocationInputSerializer(serializers.Serializer):
    line_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class PaymentInputSerializer(serializers.Serializer):
    """Forma y tipos; las reglas de negocio las valida el agregado."""
    idempotency_key = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    payment_method = serializers.CharField(max_length=20)
    payment_date = serializers.DateField(required=False, allow_null=True, default=None)
    reference = serializers.CharField(required=False, allow_blank=True, default='', max_length=MAX_REFERENCE)
    allocations = AllocationInputSerializer(many=True, max_length=200)

    def to_input(self) -> PaymentInput:
        data = self.validated_data
        return PaymentInput(data['idempotency_key'], data['amount'], data['payment_method'], data['payment_date'],
                            data['reference'], tuple((a['line_id'], a['amount']) for a in data['allocations']))


def _money(value) -> str:
    return f'{value:.2f}'


def payment_data(payment: Payment) -> dict:
    return {'id': str(payment.id), 'receipt_number': payment.receipt_number, 'amount': _money(payment.amount),
            'payment_method': payment.payment_method.value, 'payment_date': payment.payment_date.isoformat(),
            'reference': payment.reference, 'recorded_by_name': payment.recorded_by_name,
            'created_at': payment.created_at.isoformat() if payment.created_at else None,
            'allocations': [{'description': a.description, 'amount': _money(a.amount)}
                            for a in payment.allocations]}


def totals_data(statement) -> dict:
    return {'proposed': _money(statement.proposed), 'accepted': _money(statement.accepted),
            'pending': _money(statement.pending), 'rejected': _money(statement.rejected),
            'paid': _money(statement.paid), 'balance': _money(statement.balance)}


def summary_data(view: CommitmentView) -> dict:
    snapshot, obligation, statement = view.snapshot, view.obligation, view.statement
    payments = obligation.payments if obligation else []
    return {'kind': snapshot.kind, 'number': snapshot.number, 'version': snapshot.version,
            'customer_id': str(snapshot.customer_id), 'customer_name': snapshot.customer_name,
            'accepted': _money(statement.accepted), 'paid': _money(statement.paid),
            'balance': _money(statement.balance), 'payment_status': statement.payment_status,
            'created_at': obligation.created_at.isoformat() if obligation and obligation.created_at else None,
            'last_payment_date': max((p.payment_date for p in payments), default=None) and
            max(p.payment_date for p in payments).isoformat()}


def detail_data(view: CommitmentView) -> dict:
    snapshot, obligation, statement = view.snapshot, view.obligation, view.statement
    can_pay = snapshot.collectible and statement.balance > 0
    return {'kind': snapshot.kind, 'number': snapshot.number, 'version': snapshot.version,
            'status': snapshot.status,
            'proforma_id': str(snapshot.proforma_id) if snapshot.proforma_id else None, 'customer_id': str(snapshot.customer_id),
            'customer_name': snapshot.customer_name, 'date': snapshot.date.isoformat(), 'currency': CURRENCY,
            'payment_status': statement.payment_status, 'totals': totals_data(statement),
            'lines': [{'line_id': str(l.line_id), 'description': l.description, 'piece': l.piece,
                       'decision': l.decision, 'proposed': _money(l.proposed), 'accepted': _money(l.accepted),
                       'paid': _money(l.paid), 'balance': _money(l.balance), 'collectible': l.collectible}
                      for l in statement.lines],
            'payments': [payment_data(p) for p in (obligation.payments if obligation else [])],
            'allowed_actions': ['register_payment'] if can_pay else []}
