from rest_framework import serializers

from .purchase_serializers import DecimalInputField, quantity


class ReceiptLineInputSerializer(serializers.Serializer):
    """Valida forma y tipos; las reglas (pendiente, fracciones, cero) las aplica el dominio."""

    item_id = serializers.UUIDField()
    quantity = DecimalInputField()


class ReceiptInputSerializer(serializers.Serializer):
    receipt_id = serializers.UUIDField()
    receipt_date = serializers.DateField(required=False, allow_null=True)
    warehouse_id = serializers.UUIDField(required=False, allow_null=True)
    lines = ReceiptLineInputSerializer(many=True, required=False)


def _unit(abbreviation) -> dict:
    return {'abbreviation': abbreviation}


def receipt_summary(receipt) -> dict:
    return {
        'id': receipt.id,
        'reference': receipt.reference,
        'receipt_date': receipt.receipt_date.isoformat(),
        'status': receipt.status.value,
        'user_name': receipt.user_name,
        'lines_count': len(receipt.lines),
    }


def receipt_representation(detail) -> dict:
    receipt, purchase = detail.receipt, detail.purchase
    movements = None
    if detail.movements is not None:
        movements = [{
            'id': m.id,
            'product': {'id': m.product_id, 'name': m.product_name},
            'warehouse': {'id': m.warehouse_id, 'name': m.warehouse_name},
            'quantity': quantity(m.quantity),
            'unit': _unit(m.unit_abbreviation),
        } for m in detail.movements]
    return {
        'id': receipt.id,
        'reference': receipt.reference,
        'purchase': {'id': purchase.id, 'reference': purchase.reference},
        'receipt_date': receipt.receipt_date.isoformat(),
        'status': receipt.status.value,
        'user_name': receipt.user_name,
        'created_at': receipt.created_at,
        'warehouse': ({'id': receipt.warehouse_id, 'name': detail.warehouse_name}
                      if receipt.warehouse_id is not None else None),
        'lines': [{
            'item_id': line.purchase_item_id,
            'product': {'id': line.product_id, 'name': line.product_name},
            'unit': _unit(line.unit_abbreviation),
            'quantity': quantity(line.quantity),
        } for line in receipt.lines],
        'movements': movements,
    }


def reception_form_representation(form) -> dict:
    return {
        'inventory_enabled': form.inventory_enabled,
        'warehouses': [{'id': w.id, 'name': w.name, 'is_default': w.is_default} for w in form.warehouses],
        'warehouse_id': form.warehouse_id,
        'lines': [{
            'item_id': line.item_id,
            'product': {'id': line.product_id, 'name': line.product_name},
            'unit': _unit(line.unit_abbreviation),
            'allows_fractions': line.allows_fractions,
            'tracks_stock': line.tracks_stock,
            'ordered': quantity(line.ordered),
            'received': quantity(line.received),
            'pending': quantity(line.pending),
        } for line in form.lines],
    }
