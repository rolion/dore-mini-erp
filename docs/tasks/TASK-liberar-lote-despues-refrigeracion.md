# TASK-liberar-lote-despues-refrigeracion: Liberar el lote después de refrigeración

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-liberar-lote-despues-refrigeracion (base: `produccion`)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/139 (base `produccion`)
**Fuente:** https://trello.com/c/y04uzI4Y/5-dore-prod-005-liberar-el-lote-despu%C3%A9s-de-refrigeraci%C3%B3n

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-27 | (nuevo) → INVESTIGATION | Task creado desde DORE-PROD-005 | delivery-start |
| 2026-11-27 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE: nueva dependencia Producción → Modularidad (ajuste) y nuevo tipo de ajuste | delivery-start |
| 2026-11-27 | PLANNING → ENGINEERING | Specification READY; PLAN v1 y PR abiertos | delivery-start |
| 2026-11-27 | ENGINEERING → REVIEW | Implementación completa; pruebas de API del backend pendientes de BD | delivery-build |
| 2026-11-27 | REVIEW → ENGINEERING → REVIEW | Quality Gate 1 FAIL (REV-01 High, REV-02 Medium); corregidos | delivery-publish / delivery-build |
| 2026-11-27 | REVIEW → PUBLISH | Quality Gate ciclo 2 PASS | delivery-publish |

## Investigación

### Requerimiento
Tarjeta DORE-PROD-005 (insumo, no Specification aprobada). Historia: como encargado de producción quiero ver cuándo puedo liberar un lote y confirmar su liberación para que el equipo use los cuñapés a granel en el empaque.
Comportamiento esperado de la tarjeta:
1. La orden muestra cuándo ingresó el lote a refrigeración, el tiempo transcurrido y la primera hora habilitada para liberar. El mínimo se configura para la operación de DORE (ejemplo: mínimo 12 h, ingreso 08:00 → liberable desde las 20:00).
2. El sistema impide liberar antes del mínimo, también desde el API. Cumplido el mínimo, el encargado confirma manualmente.
3. Liberar registra quién y cuándo y pasa la orden a **Listo para empacar**. Las 118 unidades ya ingresadas siguen siendo 118 físicas y pasan a estar disponibles para empacar.
4. Repetir la solicitud no genera una nueva entrada ni duplica el stock.
Dependencia: DORE-PROD-004 (ya integrado en `produccion`).
Aclaración del usuario: «usa la rama de produccion» → el trabajo parte de `origin/produccion` y el PR apunta a `produccion` (igual que PROD-004).

### Hechos encontrados
- `origin/produccion` (a59e154b) ya incluye PROD-004: `ProductionOrder` con estado `refrigerating`, `entered_at`, `lot_id`, `lot_code`, `actual_output` (`backend/modules/production/domain/production_order.py:11-15,134-140`).
- Inventario ya libera lotes: `inventory.services.release_lot(company_id, lot_id, user_id, user_name)` es idempotente, devuelve `(lote, cambió)` y **no aplica el tiempo mínimo** (esa regla es de Producción) (`backend/modules/inventory/services.py:353-362`). `StockLot.release` solo cambia estado/quién/cuándo; el disponible = físico si está liberado (`inventory/domain/lot.py:57-70`). Liberar no crea movimientos: el físico no cambia.
- El ADR de lotes deja explícito que «el mínimo de horas antes de liberar» vive en Producción/PROD-005 y que Inventario no expone endpoints de liberación (`docs/adr/ADR-lotes-disponibilidad-inventario-modelo-lotes.md`, decisiones 5 y 8).
- Ajustes por empresa: catálogo `SETTINGS_CATALOG` con tipos `choice`/`percent`/`boolean` (`backend/modules/modularity/domain/settings.py:20-60`); lectura por fachada `modularity/services.py` (`get_inventory_settings`, `:32-41`); Inventario la consume por un adaptador (`ModularityInventoryPolicy`). La UI de Ajustes distingue `percent`/`boolean`/`choice` (`frontend/panel_admin/src/app/features/settings/models/setting.ts:2`, `module-settings.component.ts:110-149`). No existe un tipo entero/horas ni ajustes de `production`.
- API de órdenes: `POST api/production-orders/<id>/refrigerate/` (`production/api/order_urls.py:10`, `order_views.py:147-158`), errores 409 con `code` (`order_views.py:19-42`); `Actor(user_id, user_name)` ya existe (`application/orders.py:29`). El caso de uso corre bajo `select_for_update` de la orden, lo que da idempotencia ante doble clic.
- Dependencias permitidas hoy: `production → {catalog, costing, inventory}` (`backend/modules/sales/tests/test_boundaries.py:23`).
- Frontend: `features/production/pages/order-detail` con acciones por estado y la sección «Producción registrada» (`order-detail.component.html:14-21,36,53`).

### Hipótesis / supuestos no confirmados
Ver «Supuestos» del PLAN (S1-S6); decisiones por defecto revertibles que no cambian la Specification.

### Módulos y dependencias relacionadas
Producción (agregado, caso de uso, API, UI), Inventario (`release_lot`, `get_lot`), Modularidad (nuevo ajuste `production.min_refrigeration_hours` y nuevo tipo `integer`).

### Implementaciones similares existentes
`ProductionOrders.refrigerate` (misma forma: bloqueo de la orden, puertos `StockGateway`, `Actor`, conflicto 409); ajuste `inventory.allow_negative_stock` leído por adaptador (`ModularityInventoryPolicy`).

### Comportamiento actual
Una orden En refrigeración no puede avanzar: no hay liberación, ni hora habilitada, ni estado «Listo para empacar»; el lote queda bloqueado para empaque indefinidamente.

### Restricciones
`Decimal` para cantidades; no editar migraciones aplicadas (migración aditiva); módulos solo por `services`; aislamiento por `company_id`; la hora habilitada y el bloqueo se calculan y validan en el backend (el frontend solo informa); sin texto hardcodeado (i18n es/en/pt); sin dependencias nuevas.

### Riesgos identificados
Orden y lote deben cambiar juntos (una transacción); doble clic/reintento; reloj del cliente (se usa solo el del servidor); cambio del mínimo con lotes ya en refrigeración (se evalúa con el valor vigente al liberar); nuevo tipo de ajuste afecta la pantalla de Ajustes de otros módulos (aditivo).

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — nueva dependencia entre módulos (Producción → Modularidad) y nuevo tipo de ajuste con impacto en contrato de Ajustes, además de una transición de estado con migración.

### Diseño requerido
**SI** — panel de liberación en el detalle de la orden, nuevo estado «Listo para empacar» y campo de ajuste de horas.

## Diseño
`docs/design/DDR-liberar-lote-despues-refrigeracion-panel-liberacion.md`.

## Arquitectura
`docs/adr/ADR-liberar-lote-despues-refrigeracion-minimo-y-liberacion.md`.

## Plan
`docs/plans/PLAN-2026-11-27-liberar-lote-despues-refrigeracion.md` (v1, COMPLETO, READY).

## Implementación
**Backend:** dominio `ProductionOrder.releasable_from/release`, estado `ready_to_pack` y `ReleaseTooEarly` (INV-01, INV-02, INV-05, INV-06; AC-02..AC-06); caso de uso `ProductionOrders.release` con puerto `ReleasePolicy` y `StockGateway.release_lot` (INV-03, INV-04, AC-03, AC-05); adaptadores `InventoryStock.release_lot` y `ModularityReleasePolicy`; migración aditiva `production/0004` (3 columnas y constraint con el estado nuevo); API `POST …/release/` y campos `release`, `released_at`, `released_by` en la orden (API-01..03, AC-01, AC-09); ajuste `production.min_refrigeration_hours` con tipo nuevo `integer` y fachada `get_production_settings` (AC-07, API-04); `test_boundaries` y `ddd.md` con `production → modularity`.
**Frontend:** sección «Liberación» y acción «Liberar lote» (confirmación, deshabilitada con «Disponible desde …», error 409 con la hora) en `order-detail`; badge y filtro «Listo para empacar» en la lista; campo entero con unidad «h» en Ajustes; i18n es/en/pt (UI-01..04, AC-08). Pantalla de referencia: detalle de orden existente (DDR); sin componentes compartidos nuevos.
**Pruebas escritas:** dominio (`ProductionOrderReleaseTests`, 6), API (`OrderReleaseApiTests`, 7: AC-01..AC-07, AC-09, EDGE-01), ajustes (`ProductionSettingsTests`), Karma (servicio y detalle).
**Ejecutadas:** dominio y `test_boundaries` (23 OK, sin BD); Karma `production`+`settings` 107 OK; `npm run lint` e `i18n:check` OK; `ruff`/`flake8` limpios en lo cambiado. **No ejecutadas:** las pruebas de API/ajustes del backend y `makemigrations --check` contra BD, porque esta sesión no tiene `DATABASE_URL` (el `.env` no se lee); la migración se generó con `makemigrations`. Debe correrlas `delivery-publish`/la persona con PostgreSQL local.
**Desviaciones:** ninguna de alcance. Detalle: el botón se habilita con el reloj del navegador (informativo; el servidor revalida); el estado visual usa `col-purple`.
**Deuda técnica:** `OrderReleaseApiTests` hereda de `OrderApiTests` y vuelve a ejecutar sus pruebas base (duplicación de tiempo de prueba); sin prueba Karma específica del campo entero de Ajustes.

## Review
Quality Gate ciclo 1: **FAIL** — REV-01 (High: tests de Modularidad rotos por el tipo `integer`) y REV-02 (Medium: sin prueba unitaria de validación), ambos corregidos (ver `docs/reviews/REV-2026-11-27-liberar-lote-despues-refrigeracion-0{1,2}.md`); además se aplicó L-1 (el botón usa `release.canRelease` del servidor o el reloj local) y L-4 (nota de `ddd.md`). Tras la corrección: modularidad/producción sin BD 37 OK, Karma `production` 63 OK, lint OK; la suite Karma completa del ciclo 1 fue 1928 OK.
**Con PostgreSQL local (ciclo 2):** `makemigrations --check` sin cambios; suite backend completa 2645 tests OK (incluye `OrderReleaseApiTests` y `ProductionSettingsTests`; dos aserciones de mis pruebas se ajustaron al contrato real: `min_hours` llega como texto en el 409 y el 409 de estado no trae `code`). Revisión visual en navegador: no verificada.

## Publicación
PR #139 (base `produccion`) con descripción completa, listo para aprobación humana. No se mergea. Señalar al aprobador: toca arquitectura (ADR), base de datos (migración 0004) y la dependencia nueva `production → modularity`. Revisión visual no verificada.
