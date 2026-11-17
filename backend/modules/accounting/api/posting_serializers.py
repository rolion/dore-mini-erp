"""Serialización de la configuración de asientos automáticos (CONT-12)."""
from rest_framework import serializers

from modules.accounting.domain.posting import MODULE_LABELS


class PostingAccountInputSerializer(serializers.Serializer):
    account_id = serializers.UUIDField(allow_null=True)


def _account(info) -> dict | None:
    return ({'id': str(info.id), 'code': info.code, 'name': info.name, 'is_active': info.is_active}
            if info else None)


def serialize_role_row(row) -> dict:
    return {'role': row.role, 'label': row.label, 'account_class': row.account_class,
            'account': _account(row.account), 'issue': row.issue,
            'shared_with': [{'module': m, 'label': MODULE_LABELS[m]} for m in row.shared_with]}


def serialize_method_row(row) -> dict:
    return {'code': row.code, 'label': row.label, 'is_active': row.is_active, 'account': _account(row.account),
            'issue': row.issue}


def serialize_category_row(row) -> dict:
    return {'classification_id': str(row.classification_id), 'name': row.name, 'is_active': row.is_active,
            'account': _account(row.account), 'issue': row.issue}


def serialize_event(event) -> dict:
    return {
        'code': event.code, 'label': event.label,
        'preview': [{'side': line.side, 'role': line.role, 'label': line.label, 'account': _account(line.account),
                     'status': line.status} for line in event.preview],
        'issues': [{'code': i.code, 'role': i.role, 'subject': i.subject, 'module': i.module, 'message': i.message}
                   for i in event.issues],
    }


def serialize_posting_config(ref) -> dict:
    view = ref.config
    return {
        'module': view.module, 'module_label': MODULE_LABELS[view.module], 'accounting_enabled': ref.accounting_enabled,
        'ready': view.ready, 'events': [serialize_event(e) for e in view.events],
        'roles': [serialize_role_row(r) for r in view.roles],
        'methods': [serialize_method_row(m) for m in view.methods],
        'categories': [serialize_category_row(c) for c in view.categories],
    }
