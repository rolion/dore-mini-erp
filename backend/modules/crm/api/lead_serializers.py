from rest_framework import serializers

from modules.crm.application.lead_services import Conversion
from modules.crm.application.ports import CustomerContact
from modules.crm.domain.lead import Lead

_TIMESTAMP = serializers.DateTimeField()


class LeadInputSerializer(serializers.Serializer):
    """Forma y tipos; las reglas (nombre obligatorio, largos, correo) son del dominio."""
    name = serializers.CharField(allow_blank=True, trim_whitespace=False)
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True, trim_whitespace=False)
    email = serializers.CharField(required=False, allow_blank=True, allow_null=True, trim_whitespace=False)


class ConvertInputSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField(required=False, allow_null=True)


def timestamp(value) -> str | None:
    return _TIMESTAMP.to_representation(value) if value else None


def lead_data(lead: Lead) -> dict:
    return {
        'id': str(lead.id), 'name': lead.name, 'phone': lead.phone, 'normalized_phone': lead.normalized_phone,
        'email': lead.email,
        'converted_customer_id': str(lead.converted_customer_id) if lead.converted_customer_id else None,
        'created_at': timestamp(lead.created_at),
    }


def contact_data(contact: CustomerContact | Lead | None) -> dict | None:
    if contact is None:
        return None
    return {'id': str(contact.id), 'name': contact.name, 'phone': contact.phone}


def conversion_data(conversion: Conversion) -> dict:
    return {'lead': lead_data(conversion.lead), 'customer': contact_data(conversion.customer),
            'created': conversion.created}
