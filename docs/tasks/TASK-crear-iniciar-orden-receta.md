# TASK-crear-iniciar-orden-receta: Crear e iniciar una orden de producción desde una receta

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-crear-iniciar-orden-receta (base: `produccion`)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/131
**Fuente:** https://trello.com/c/oASF4BMf/3-dore-prod-003-crear-e-iniciar-una-orden-desde-una-receta

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-26 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta DORE-PROD-003 | delivery-start |
| 2026-11-26 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | Veredicto NEEDS_ARCHITECTURE, diseño SI | delivery-start |
| 2026-11-26 | PLANNING → ENGINEERING | Specification READY, PR abierto contra `produccion` | delivery-start |
| 2026-11-26 | ENGINEERING → REVIEW | Implementación completa del plan v1 | delivery-build |
| 2026-11-26 | REVIEW → PUBLISH | Quality Gate PASS (3 Low: REV-03 resuelto, REV-01 y REV-02 abiertos) | delivery-publish |

## Investigación

### Requerimiento
Fuente: tarjeta Trello DORE-PROD-003 (lista «Por hacer — orden de implementación», tablero «produccion dore»). Insumo, no Specification aprobada. Aclaración del usuario: «usa la rama de produccion» (la base del PR es `origin/produccion`, no `main`).

- **Historia:** como operario de DORE, seleccionar una receta y cuántas veces la voy a preparar para saber cuánto producir y qué ingredientes necesito.
- En Producción › Órdenes de producción, **Nueva orden** permite elegir una receta activa, el almacén y el número de preparaciones. La orden guarda los datos previstos de la receta y pasa de **Borrador** a **En preparación**.
- Ejemplo: receta que rinde 24 cuñapés, 5 preparaciones → 120 unidades previstas e ingredientes × 5.
- Se valida receta activa y preparaciones = entero positivo.
- La orden conserva ingredientes, cantidades y rendimiento previstos aunque después se edite la receta.
- Guardar el borrador o iniciar **no modifica existencias**. Al iniciar se registra fecha y hora.
- Dependencia: DORE-PROD-001 (recetas), ya integrada en `produccion` (PR #127).
- Sin checklists ni comentarios.

### Hechos encontrados
- Módulo `production` existe en `produccion` con solo recetas: dominio `backend/modules/production/domain/recipe.py:50-115` (`Recipe`, `RecipeIngredient`, `activate/deactivate`), casos de uso `application/recipes.py:38-118` (`RecipeBook`, puerto `ProductCatalog`), API `api/views.py:98-134` (`required_modules = ('production',)`, paginación 20/100), modelos `infrastructure/django/models.py:7-41` (UUID sin FK a otros módulos, `company_id` solo en la raíz).
- El ADR de recetas ya fija que las órdenes **copiarán** la receta al crearse: `docs/adr/ADR-gestionar-recetas-produccion-modulo-production.md` decisión 6.
- No existe orden de producción en backend ni frontend (sin coincidencias de `order`/`ProductionOrder` en `backend/modules/production/`).
- El menú Producción solo tiene «Recetas»: `frontend/panel_admin/src/assets/data/routes.json:339-363`; ruta lazy en `frontend/panel_admin/src/app/app.routes.ts:210-215`; claves i18n `MENUITEMS.PRODUCTION.*`.
- Almacenes: fachada de Inventario `backend/modules/inventory/services.py:190-193` (`list_active_warehouses`) y `:196-200` (`get_warehouse_names`); API `api/warehouses/` en `backend/config/urls.py:23`. Hoy `production` solo puede depender de `catalog`: `backend/modules/sales/tests/test_boundaries.py:23` (`'production': {'catalog'}`) y `backend/modules/modularity/tests/test_domain.py:31`.
- Módulo `production` declara `requires=('catalog',)` en `backend/modules/modularity/domain/modules.py:38`; `inventory` es módulo opcional (`:33`).
- Referencia de numeración correlativa por empresa: `backend/modules/purchases/infrastructure/django/models.py:170-179` (contador con `last_number`); de formulario con líneas y cantidades calculadas: `features/purchases/pages/purchase-form`; de detalle con acciones de ciclo de vida: `features/purchases/pages/purchase-detail`; de lista con estados: `features/purchases/pages/purchase-list` (design-system §5).
- Guardas: `backend/modules/accounts/test_guards.py:6-10` (`CHILD_MODELS`: la tabla hija de ingredientes de la orden debe registrarse igual que `production.RecipeIngredientModel`).

### Hipótesis / supuestos no confirmados
**Aprobados por el usuario en el chat (2026-11-26): supuestos 1-6.**

Se adoptan por defecto (la tarjeta no los define; ninguno cambia contrato ni dinero):
1. **Editar un borrador** solo cambia almacén y preparaciones; la receta y su copia no se cambian (para otra receta se crea otra orden). Los ingredientes previstos se recalculan = cantidad por preparación × preparaciones.
2. La receta se valida **activa solo al crear**; al iniciar no se vuelve a exigir (la orden ya tiene su copia). El almacén sí debe estar activo al crear/editar e iniciar.
3. Cancelar/eliminar borradores, completar y registrar consumos reales quedan para tarjetas posteriores (solo se pide Borrador → En preparación).
4. Número de orden correlativo por empresa (`OP-0001`), asignado al guardar el borrador, para identificarla en lista y detalle; sin período fiscal.
5. `production` pasa a requerir `inventory` (por el almacén).
6. Permisos: usuario autenticado de la empresa con módulo habilitado (igual que recetas); la tarjeta no pide roles.

### Módulos y dependencias relacionadas
Producción (recetas), Catálogo (nombres/unidades por la fachada ya usada), Inventario (almacenes, solo lectura por `services`), Modularidad (registro del módulo), frontend `features/production`.

### Implementaciones similares existentes
`purchases` (borrador → confirmación con número), recetas (agregado + repositorio + API), `stock-opening`/`purchase-form` (formulario con líneas).

### Comportamiento actual
Se pueden definir recetas pero no producir; no hay órdenes ni menú «Órdenes de producción».

### Restricciones
`CLAUDE.md`: `company_id` desde el usuario, dominio sin Django, `Decimal` (nunca `float`), migración nueva, i18n es/en/pt sin texto hardcodeado, Reactive Forms, fachadas entre módulos.

### Riesgos identificados
- Nueva dependencia `production → inventory` (guardas de límites y `requires`): empresas con Producción habilitada sin Inventario quedarían con la API de órdenes sin almacenes. Mitigación en el ADR.
- Numeración concurrente: contador bloqueado con `select_for_update`.
- Las órdenes se parecen a las compras; no copiar su complejidad fiscal.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — nuevo agregado y tablas, nueva dependencia entre bounded contexts (Producción → Inventario), cambio de `requires` del módulo y contrato API nuevo.

### Diseño requerido
**SI** — pantallas nuevas (lista, alta, detalle de orden) y entrada nueva del menú.

## Diseño
Ver `docs/design/DDR-crear-iniciar-orden-receta-pantallas-ordenes.md`.

## Arquitectura
Ver `docs/adr/ADR-crear-iniciar-orden-receta-agregado-orden-produccion.md`.

## Plan
Ver `docs/plans/PLAN-2026-11-26-crear-iniciar-orden-receta.md` (v1, COMPLETO). Specification readiness: READY.

## Implementación
Plan v1 implementado sin cambios de Specification.

**Backend** (`backend/modules/production/`): `domain/production_order.py` (agregado, INV-01, 03-05, 07), `application/orders.py` (casos de uso con puertos `WarehouseDirectory`/`RecipeSource`; INV-02, INV-06), `infrastructure/django/{models,order_repository}.py` + migración `0002_production_orders` (INV-08, contador bloqueado con `select_for_update`), adaptador `InventoryWarehouses` sobre `inventory.services` (INV-09: sin movimientos), API `api/order_*.py` en `api/production-orders/` (API-01..05). Módulo `production` ahora `requires=('catalog','inventory')`; actualizados `test_boundaries`, `modularity/tests/test_domain.py`, `test_guards.py` y `ddd.md`.
**Frontend** (`features/production/`): modelos con aritmética decimal por enteros escalados, `orders-api.service`, páginas `order-list`, `order-form`, `order-detail`, ruta `production/orders`, ítem de menú, i18n es/en/pt. Referencias seguidas: `purchase-list`, `purchase-form`, `purchase-detail` y las pantallas de recetas; sin componentes compartidos nuevos.
**Pruebas:** `test_order_domain.py` y `test_order_api.py` cubren AC-01..AC-10, EDGE-01, 03, 04; specs de servicio, lista, formulario, detalle y menú (AC-11, AC-12).

**Desviaciones:** la lista devuelve cada orden con la misma forma que el detalle (el plan lo dejaba implícito). El almacén se revalida al iniciar solo si la orden es borrador. Un `PUT`/`start` en estado inválido responde 409.
**Deuda técnica:** ninguna nueva; las recetas activas del formulario se buscan con `page_size=20` y búsqueda por texto.

## Review
**PASS** (subagente aislado). Backend: suite completa 2577 OK; 413 OK en production/modularity/accounts/boundaries/inventory; `makemigrations --check` limpio; ruff/flake8 sin avisos nuevos; bandit sin hallazgos. Frontend: lint, `i18n:check` (2609 claves, 0 faltantes), 1911/1911 pruebas y build OK. Hallazgos Low: [REV-01](../reviews/REV-2026-11-26-crear-iniciar-orden-receta-01.md) (EDGE-01 sin prueba concurrente), [REV-02](../reviews/REV-2026-11-26-crear-iniciar-orden-receta-02.md) (aserciones débiles AC-04/AC-05), [REV-03](../reviews/REV-2026-11-26-crear-iniciar-orden-receta-03.md) (nota de ddd.md; resuelto). Revisión visual en navegador: **no verificada**.

## Publicación
PR #131 listo para aprobación humana (base `produccion`, no se mergea). Cambio con impacto arquitectónico (ADR: nueva dependencia Producción → Inventario, cambio de `requires`, migración).
