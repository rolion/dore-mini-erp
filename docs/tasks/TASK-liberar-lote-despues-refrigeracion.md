# TASK-liberar-lote-despues-refrigeracion: Liberar el lote después de refrigeración

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-liberar-lote-despues-refrigeracion (base: `produccion`)
**Pull Request:** _sin abrir todavía_
**Fuente:** https://trello.com/c/y04uzI4Y/5-dore-prod-005-liberar-el-lote-despu%C3%A9s-de-refrigeraci%C3%B3n

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-27 | (nuevo) → INVESTIGATION | Task creado desde DORE-PROD-005 | delivery-start |
| 2026-11-27 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE: nueva dependencia Producción → Modularidad (ajuste) y nuevo tipo de ajuste | delivery-start |
| 2026-11-27 | PLANNING → ENGINEERING | Specification READY; PLAN v1 y PR abiertos | delivery-start |

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
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
