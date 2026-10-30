from modules.modularity.application.use_cases import ModuleView


def _links(pairs) -> list[dict]:
    return [{'key': m.key, 'name': m.name, 'enabled': enabled} for m, enabled in pairs]


def serialize_module(view: ModuleView) -> dict:
    module = view.definition
    return {
        'key': module.key,
        'name': module.name,
        'description': module.description,
        'is_base': module.is_base,
        'enabled': view.enabled,
        'requires': _links(view.requires),
        'optional': _links(view.optional),
        'missing_requires': view.missing_requires,
        'capabilities': [{'key': k, 'label': label, 'available': ok} for k, label, ok in view.capabilities],
        'missing_capabilities': view.missing_capabilities,
        'adopted_at': view.adopted_at.isoformat() if view.adopted_at else None,
        'disable_blockers': [
            {'code': b.code, 'message': b.message, 'resolution': b.resolution} for b in view.blockers
        ],
    }


def serialize_settings(module: str, values) -> dict:
    return {
        'module': module,
        'settings': [
            {
                'key': item.definition.key,
                'label': item.definition.label,
                'description': item.definition.description,
                'kind': item.definition.kind,
                'value': item.value,
                'default': item.definition.default,
                'choices': [{'value': v, 'label': label} for v, label in item.definition.choices],
                'minimum': None if item.definition.minimum is None else str(item.definition.minimum),
                'maximum': None if item.definition.maximum is None else str(item.definition.maximum),
            }
            for item in values
        ],
    }


def serialize_change(row) -> dict:
    return {
        'id': str(row.id),
        'changed_at': row.changed_at.isoformat(),
        'changed_by': row.changed_by_name,
        'setting_key': row.setting_key,
        'setting_label': row.setting_label,
        'old_value': row.old_value,
        'new_value': row.new_value,
    }
