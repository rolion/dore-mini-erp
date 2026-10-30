# ADR-habilitar-produccion-y-costeo-capacidades-y-bloqueos: Módulos Producción y Costeo, capacidades y bloqueos de desactivación

**Estado:** Propuesto
**Task relacionado:** TASK-habilitar-produccion-y-costeo
**Fecha:** 2026-10-30

## Contexto
PB-MOD-001 resuelve dependencias entre módulos (`requires`). PB-MOD-005 agrega Producción y Costeo, que necesitan tres cosas que el modelo actual no tiene: (a) una **capacidad** que no es un módulo (valoración de Inventario, PB-VAL-001/002, aún inexistente), (b) **bloqueos de desactivación por datos** (órdenes abiertas, costos sin cerrar) cuyos datos viven en módulos que `modularity` no puede importar, y (c) una **fecha de adopción** de Costeo con valoración de las existencias de ese momento. Ni Producción, ni Costeo ni la valoración existen todavía; la solución debe quedar lista para que los registren sin tocar `modularity`.

## Decisión
1. **Catálogo** (`domain/modules.py`): agregar `production` («Producción»; `requires=('catalog','inventory')`, `optional=('purchases',)`) y `costing` («Costeo»; `requires=('production',)`, `requires_capabilities=('inventory.valuation',)`, `records_adoption=True`). Compras es solo opcional de Producción. No entran en `DEFAULT_ENABLED_KEYS`. `ModuleDefinition` gana `requires_capabilities: tuple[str, ...] = ()` y `records_adoption: bool = False`; un catálogo de capacidades en dominio: `CAPABILITIES = {'inventory.valuation': 'Valoración de Inventario'}`.
2. **Puerto neutro `shared/module_extensions.py`** (mismo estilo que `shared/module_gate.py`; fail-closed y sin importar módulos de negocio):
   - `register_capability(key, provider)` / `capability_available(company_id, key) -> bool`. Sin proveedor registrado → **no disponible**. Lo registrará Inventario cuando exista la valoración; lo consultan también los módulos que muestren costos (Costeo no debe mostrar costos sin la capacidad).
   - `register_disable_guard(module_key, provider)` / `disable_blockers(company_id, module_key) -> list[Blocker]`, con `Blocker(code, message, resolution)`. Lo registran Producción (órdenes abiertas) y Costeo (costos sin cerrar) en su `AppConfig.ready`.
   - `register_enable_hook(module_key, hook)` / `run_enable_hooks(company_id, module_key, adopted_at)`. Costeo/Inventario lo usarán para valorar las existencias actuales a la fecha de adopción. Si el gancho falla, la habilitación se revierte (corre dentro de la misma transacción).
   `modularity` lo consume solo mediante un puerto del caso de uso (`ModuleExtensions`) con adaptador en `infrastructure/django/`; `shared` no conoce a `modularity`.
3. **Reglas**:
   - Habilitar: primero `requires` (como hoy → `DependencyError(kind='missing')`); luego capacidades requeridas → `DependencyError(kind='capabilities')` con las etiquetas faltantes. Sin ninguna de las dos no se ejecuta el gancho ni se guarda nada.
   - Deshabilitar: se reúnen los dependientes habilitados (`requires`, como hoy) y los bloqueos de las guardas del módulo; si hay alguno → 409 con ambos listados. Deshabilitar **no** toca otros módulos ni borra datos de negocio: solo elimina la fila del módulo (el historial de módulos queda en `modularity_setting_change`). Idempotencia: deshabilitar un módulo ya deshabilitado no consulta guardas.
   - Inventario con Producción activo y Producción con Costeo activo ya quedan cubiertos por `requires`/dependientes; se agregan pruebas explícitas.
4. **Fecha de adopción** = `enabled_at` de la fila del módulo (`records_adoption`). Como deshabilitar borra la fila, una rehabilitación fija una **fecha nueva**; las anteriores quedan en el historial. Nada recalcula lotes anteriores: solo se pasa la fecha al gancho. **Sin migración**.
5. **Contrato API** (aditivo, retrocompatible) en `GET /api/modules/` y en la respuesta de enable/disable:
   - `capabilities: [{key, label, available}]` y `missing_capabilities: [label]` (también para módulos habilitados, para avisar que Costeo no debe mostrar costos si la capacidad desaparece).
   - `adopted_at: ISO-8601 | null` (solo módulos con `records_adoption` habilitados).
   - `disable_blockers: [{code, message, resolution}]` (módulos no base habilitados; vacío si nada bloquea).
   - `POST …/enable/` → `409 {detail, missing:[nombres]}` (sin cambios) o `{detail, missing_capabilities:[etiquetas]}`; `POST …/disable/` → `409 {detail, dependents?:[nombres], blockers?:[{code,message,resolution}]}`. Códigos 404/400 sin cambios. La empresa sigue saliendo de la sesión.
6. **Resto del sistema**: las vistas de Producción/Costeo futuras declararán `required_modules = ('production',)` / `('costing',)` (la guarda automática de `test_guards.py` ya valida claves contra el catálogo); la configuración (`/api/settings/production|costing/`) funciona sin ajustes (lista vacía) y su historial registra habilitar/deshabilitar. El frontend agrega los grupos de menú y pantallas descritos en el DDR.

## Alternativas consideradas
- **Tratar «Valoración de Inventario» como un módulo o submódulo habilitable**: la historia lo define como *capacidad* de Inventario, no una opción de la empresa; añadiría un interruptor que el admin no pidió. Descartada.
- **Que `modularity` consulte directamente tablas/servicios de Producción y Costeo para los bloqueos**: viola el límite (módulos de negocio no se importan; `modularity` no importa negocio). Descartada.
- **Mantener solo `requires` (sin capacidades) y marcar Inventario como «incompleto»**: no impediría habilitar Costeo sin valoración. Descartada.
- **Columna `adopted_at` propia**: redundante con `enabled_at` y exige migración sin beneficio. Descartada.
- **Valorar existencias dentro de `modularity`**: mezcla responsabilidades; la valoración pertenece a Inventario/Costeo.

## Estrategia de rollback / mitigación
Sin migración ni datos nuevos: revertir el cambio restaura el catálogo anterior. Las filas `production`/`costing` que hubieran quedado guardadas se ignoran por `effective_enabled` al no estar en el catálogo. Fail-closed: sin proveedor registrado la capacidad no está disponible (no se habilita Costeo) y sin guardas registradas no hay bloqueo por datos (riesgo conocido hasta que Producción/Costeo registren las suyas; mitigado por una prueba que fallará cuando existan modelos de órdenes sin guarda registrada, a cargo de sus historias).

## Consecuencias
- Costeo no se puede habilitar en ninguna empresa hasta que PB-VAL registre la capacidad (comportamiento pedido).
- La protección contra la carrera «crear orden vs. desactivar Producción» debe cerrarse en Producción (bloqueo en su transacción); `modularity` solo consulta y explica.
- Cada módulo con datos que impidan desactivar debe registrar su guarda; agregar un módulo = entrada de catálogo + (si aplica) capacidad/guarda/gancho.
- `GET /api/modules/` hace una consulta de guardas por módulo habilitado; son pocas y baratas, sin caché entre peticiones.
