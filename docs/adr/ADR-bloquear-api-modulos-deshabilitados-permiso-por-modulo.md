# ADR-bloquear-api-modulos-deshabilitados-permiso-por-modulo: Permiso por módulo en la API de negocio

**Estado:** Propuesto
**Task relacionado:** TASK-bloquear-api-modulos-deshabilitados
**Fecha:** 2026-10-27

## Contexto
PB-MOD-001 guarda qué módulos tiene cada empresa pero solo oculta menú y rutas Angular. Hay que rechazar en el backend las consultas y escrituras de un módulo deshabilitado, con la empresa tomada de la sesión, sin que los módulos de negocio importen `accounts` ni `modularity` (`docs/architecture/ddd.md:844`).

## Decisión
1. **Permiso central.** Un permiso por defecto nuevo, `config/permissions.py: CompanyModulePermission`, que extiende `CompanyAdminPermission`. Orden: autenticación / empresa activa / rol (respuestas actuales) y después el módulo.
2. **Cada vista declara su módulo** con `required_modules = ('sales',)` (tupla; `()` = sin módulo, p. ej. las vistas de `modularity`). **Fail-closed:** una vista sin ese atributo se rechaza. Rutas con dos módulos (`reports/top-customers/` → `reporting` y `customers`) los listan ambos.
3. **Puerto neutro `shared/module_gate.py`:** `register(provider)`, `enabled_keys(company_id)`, `is_enabled(company_id, key)`. `modularity` registra su implementación en `AppConfig.ready()`; el permiso y los adaptadores de integración lo consultan. Así nadie importa `modularity` y el contrato queda en `shared`.
4. **Sin caché entre peticiones:** cada petición lee la configuración (con una caché por petición), de modo que un cambio de módulos rige desde la petición siguiente.
5. **Rechazo:** `403` con `{detail: 'Módulo no habilitado', code: 'module_disabled', module: '<key>'}` mediante `ModuleDisabled(PermissionDenied)`. Los 401/403 actuales no cambian.
6. **Integraciones opcionales** (decisión del usuario): con Clientes deshabilitado, el adaptador de Clientes de Ventas y el de Reporting consultan `module_gate`; Ventas rechaza asignar o filtrar por cliente (400 en `customer_id`), expone `customer: null` en pedidos y Reporting omite nombres. No hay error 500 ni bloqueo del flujo principal.
7. **Guarda automática:** `test_guards.py` falla si una ruta `api/` no pública no declara `required_modules`, si la clave no existe en el catálogo o si una vista de negocio no usa el permiso por defecto.

## Alternativas consideradas
- **Middleware por prefijo de URL:** concentra la regla pero es implícito y frágil ante rutas nuevas.
- **Permiso por vista sin permiso por defecto:** más repetición y rompe la guarda de permisos actual.
- **Importar `modularity` desde los módulos de negocio:** viola la regla de límites.
- **404 en vez de 403:** impide mostrar un mensaje claro (descartado por el usuario).

## Estrategia de rollback / mitigación
Sin migración ni datos nuevos: revertir el cambio restaura el comportamiento anterior. Mitigación de riesgo: la guarda de tests y el valor fail-closed; si el permiso fallara en producción se vuelve al permiso previo con un solo cambio en `DEFAULT_PERMISSION_CLASSES`.

## Consecuencias
Una o dos consultas extra por petición (menos con la caché por petición). Toda vista nueva debe declarar su módulo. Los límites DDD se conservan: `shared` como puerto, `modularity` como implementación.
