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
    }
