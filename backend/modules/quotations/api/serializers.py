from rest_framework import serializers

from modules.quotations.application.proformas import LineInput, ProformaInput
from modules.quotations.domain.proforma import CURRENCY


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


def line_data(line) -> dict:
    return {'id': str(line.id), 'service_id': str(line.service_id), 'description': line.description,
            'quantity': f'{line.quantity:.2f}', 'unit_price': f'{line.unit_price:.2f}',
            'subtotal': f'{line.subtotal:.2f}', 'treatment_item_id': (
                str(line.treatment_item_id) if line.treatment_item_id else None), 'piece': line.piece}


def summary_data(proforma) -> dict:
    return {'id': str(proforma.id), 'number': proforma.number, 'version': proforma.version,
            'status': proforma.status, 'customer_id': str(proforma.customer_id),
            'customer_name': proforma.customer_name, 'date': proforma.date.isoformat(),
            'valid_until': proforma.valid_until.isoformat() if proforma.valid_until else None,
            'currency': CURRENCY, 'total': f'{proforma.total:.2f}'}


def detail_data(proforma, *, allowed_actions, can_edit_price, versions) -> dict:
    return {**summary_data(proforma), 'notes': proforma.notes, 'lines': [line_data(l) for l in proforma.lines],
            'allowed_actions': allowed_actions, 'can_edit_price': can_edit_price,
            'versions': [summary_data(v) for v in versions]}
