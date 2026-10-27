from rest_framework.exceptions import PermissionDenied

from modules.accounts.api.permissions import CompanyAdminPermission
from shared import module_gate
from shared.tenancy import company_id_from

MODULE_DISABLED = 'Módulo no habilitado'


class ModuleDisabled(PermissionDenied):
    """403 con `{detail, code: 'module_disabled', module}` para que el cliente muestre la pantalla de acceso."""

    default_code = 'module_disabled'

    def __init__(self, module: str):
        super().__init__(detail={'detail': MODULE_DISABLED, 'code': 'module_disabled', 'module': module})


class CompanyModulePermission(CompanyAdminPermission):
    """Permiso por defecto de la API: el de siempre y, además, que los módulos de la vista estén habilitados.

    Cada vista declara `required_modules` (tupla; `()` si no depende de un módulo). Sin el atributo se rechaza.
    La empresa sale del usuario autenticado y la configuración se lee en cada petición, así que un cambio de
    módulos rige desde la petición siguiente.
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        required = getattr(view, 'required_modules', None)
        if required is None:
            return False
        enabled = module_gate.enabled_keys(company_id_from(request))
        for key in required:
            if key not in enabled:
                raise ModuleDisabled(key)
        return True
