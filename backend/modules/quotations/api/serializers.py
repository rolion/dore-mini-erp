from rest_framework import serializers

from modules.quotations.application.proformas import DecisionInput, LineInput, ProformaInput
from modules.quotations.domain.proforma import ACCEPTED, CURRENCY, MAX_NAME, MAX_REASON, MAX_REFERENCE, PRESENTED


class LineInputSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False)
    service_id = serializers.UUIDField(required=False)
    quantity = serializers.DecimalField(max_digits=8, decimal_places=2)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    # `description`, `subtotal` y `total` enviados por el navegador se ignoran: el servidor los calcula.


class ProformaInputSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField()
    date = serializers.DateField()
    valid_until = serializers.DateField(required=False, allow_null=True, default=None)
    notes = serializers.CharField(required=False, allow_blank=True, default='', max_length=2000)
    lines = LineInputSerializer(many=True, max_length=500)

    def to_input(self) -> ProformaInput:
        data = self.validated_data
        lines = [LineInput(quantity=l['quantity'], id=l.get('id'), service_id=l.get('service_id'),
                           unit_price=l.get('unit_price')) for l in data['lines']]
        return ProformaInput(data['customer_id'], data['date'], data['valid_until'], data['notes'], lines)


class DecisionInputSerializer(serializers.Serializer):
    """Forma y tipos; las reglas de negocio las valida el agregado."""
    idempotency_key = serializers.UUIDField()
    decision = serializers.CharField(max_length=10)
    line_ids = serializers.ListField(child=serializers.UUIDField(), required=False, default=list, max_length=200)
    accepted_by_name = serializers.CharField(required=False, allow_blank=True, default='', max_length=MAX_NAME)
    medium = serializers.CharField(required=False, allow_blank=True, default='', max_length=20)
    reference = serializers.CharField(required=False, allow_blank=True, default='', max_length=MAX_REFERENCE)
    reason = serializers.CharField(required=False, allow_blank=True, default='', max_length=MAX_REASON)

    def to_input(self, line_ids=None) -> DecisionInput:
        data = self.validated_data
        return DecisionInput(data['idempotency_key'], data['decision'],
                             list(line_ids) if line_ids is not None else data['line_ids'],
                             data['accepted_by_name'], data['medium'], data['reference'], data['reason'])


def decision_data(record) -> dict:
    return {'id': str(record.id), 'kind': record.kind, 'decision': record.decision,
            'decided_at': record.decided_at.isoformat(), 'recorded_by_name': record.recorded_by_name,
            'accepted_by_name': record.accepted_by_name, 'medium': record.medium, 'reference': record.reference,
            'reason': record.reason}


def line_data(line, *, proforma_status=PRESENTED) -> dict:
    current = line.current_decision
    return {'id': str(line.id), 'service_id': str(line.service_id), 'description': line.description,
            'quantity': f'{line.quantity:.2f}', 'unit_price': f'{line.unit_price:.2f}',
            'subtotal': f'{line.subtotal:.2f}', 'treatment_item_id': (
                str(line.treatment_item_id) if line.treatment_item_id else None), 'piece': line.piece,
            'line_kind': line.line_kind, 'origin_line_id': str(line.origin_line_id) if line.origin_line_id else None,
            'decision': line.decision, 'decided_at': current.decided_at.isoformat() if current else None,
            'decision_detail': decision_data(current) if current else None,
            'authorized': line.decision == ACCEPTED and proforma_status == PRESENTED}


def totals_data(proforma) -> dict:
    return {key: f'{value:.2f}' for key, value in proforma.totals.items()}


def summary_data(proforma) -> dict:
    return {'id': str(proforma.id), 'number': proforma.number, 'version': proforma.version,
            'status': proforma.status, 'customer_id': str(proforma.customer_id),
            'customer_name': proforma.customer_name, 'date': proforma.date.isoformat(),
            'valid_until': proforma.valid_until.isoformat() if proforma.valid_until else None,
            'currency': CURRENCY, 'total': f'{proforma.total:.2f}',
            'accepted_total': f"{proforma.totals['accepted']:.2f}", 'acceptance_status': proforma.acceptance_status}


def detail_data(proforma, *, allowed_actions, can_edit_price, versions, decision_actions=()) -> dict:
    previous = next((v for v in versions if v.version == proforma.version - 1), None)
    history = [{**decision_data(record), 'line_id': str(line.id), 'line_description': line.description}
               for line, record in proforma.decision_history()]
    return {**summary_data(proforma), 'notes': proforma.notes,
            'lines': [line_data(l, proforma_status=proforma.status) for l in proforma.lines],
            'allowed_actions': allowed_actions, 'can_edit_price': can_edit_price,
            'versions': [summary_data(v) for v in versions],
            'decision_actions': list(decision_actions), 'totals': totals_data(proforma),
            'decision_history': history, 'previous_version_id': str(previous.id) if previous else None}


def printable_data(proforma) -> dict:
    """Solo datos comerciales: sin referencia/evidencia, motivos, usuarios, ids internos ni historial."""
    return {'number': proforma.number, 'version': proforma.version, 'status': proforma.status,
            'customer_name': proforma.customer_name, 'date': proforma.date.isoformat(),
            'valid_until': proforma.valid_until.isoformat() if proforma.valid_until else None,
            'currency': CURRENCY, 'notes': proforma.notes, 'acceptance_status': proforma.acceptance_status,
            'totals': {k: f'{v:.2f}' for k, v in proforma.totals.items() if k != 'rejected'},
            'lines': [{'description': l.description, 'piece': l.piece, 'quantity': f'{l.quantity:.2f}',
                       'unit_price': f'{l.unit_price:.2f}', 'subtotal': f'{l.subtotal:.2f}',
                       'decision': l.decision,
                       'decided_at': l.current_decision.decided_at.date().isoformat() if l.current_decision else None}
                      for l in proforma.lines]}
