# TASK-empacar-bolsas-de-6-venta-detalle: Empacar bolsas de 6 para venta al detalle

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-empacar-bolsas-de-6-venta-detalle (base: `produccion`)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/143 (base `produccion`)
**Fuente:** https://trello.com/c/1kI5jd1c/7-dore-prod-007-empacar-bolsas-de-6-para-venta-al-detalle

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-27 | (nuevo) → INVESTIGATION | Task creado desde DORE-PROD-007 | delivery-start |
| 2026-11-27 | INVESTIGATION → DESIGN → PLANNING | NEEDS_PLAN con diseño; decisiones de negocio resueltas con el usuario | delivery-start |
| 2026-11-27 | PLANNING → ENGINEERING | Specification READY; PLAN v1 y PR abiertos | delivery-start |
| 2026-11-27 | ENGINEERING → REVIEW | Implementación completa; pruebas de API del backend pendientes de BD | delivery-build |
| 2026-11-27 | REVIEW → PUBLISH | Quality Gate ciclo 1 PASS | delivery-publish |
| 2026-11-27 | PUBLISH → PUBLISH | Revisión visual en navegador; REV-visual-01 (historial no apilado en móvil) corregido | delivery-publish |

## Investigación

### Requerimiento
Tarjeta DORE-PROD-007 (insumo, no Specification aprobada). Historia: como operario de empaque quiero convertir cuñapés a granel en packs de 6 para disponer de un producto listo para vender al detalle.
Comportamiento esperado de la tarjeta:
1. Desde una orden con lote listo, «Registrar empaque» permite elegir cuántos packs preparar. Con 6 packs se descuentan 36 cuñapés del lote y 6 bolsas, y se ingresan 6 packs al inventario disponible para venta.
2. Si faltan cuñapés liberados o bolsas, el sistema identifica el faltante y conserva los saldos. El movimiento es atómico y el reintento no lo duplica.
3. Se puede empacar en varias tandas. El detalle muestra el historial de empaques, su lote de origen y el saldo restante a granel.
4. El costo de los packs incorpora los cuñapés y las bolsas según la valoración de Inventario.
Dependencia: DORE-PROD-005 (liberar lote; ya integrado en `produccion`).
Aclaraciones del usuario: «usa la rama de producción» → el trabajo parte de `origin/produccion` y el PR apunta a `produccion` (igual que PROD-004/005). Decisiones de negocio respondidas: (a) el pack y la bolsa se eligen en cada empaque; (b) conversión fija: 6 cuñapés y 1 bolsa por pack; (c) costo = promedio vigente de Costeo (36 × cuñapé + 6 × bolsa); sin Costeo activo o sin costo, el pack entra sin costo.

### Hechos encontrados
- La orden `ready_to_pack` ya tiene `lot_id`, `lot_code`, `warehouse_id` y `actual_output` (`backend/modules/production/domain/production_order.py:126-154`); el estado y la liberación existen (`:256-274`). No hay entidad ni acción de empaque.
- Inventario ya soporta la salida de un lote liberado: `record_movement(..., lot_id=...)` exige lote liberado con saldo (`backend/modules/inventory/services.py:64-88`; `check_lot_output`, `inventory/application/movement_use_cases.py:35-48`) y las entradas/salidas sin lote son idempotentes por `(source_type, source_id, source_line)` (`services.py:77-79`). `get_lot` da físico y disponible (`services.py:365`); `get_balances(..., unlotted=True)` da el saldo de las bolsas (`services.py:211`).
- `SOURCE_TYPES` solo conoce `production_order` para Producción (`inventory/domain/movement.py:34-42`).
- Costeo: `cost_outputs` valoriza salidas al promedio y `cost_receipt` registra la entrada con costo unitario, idempotentes por origen y producto, y `CostUnavailable` si falta costo (`costing/services.py:48-70`); el patrón de uso está en `CostingGateway` (`production/infrastructure/adapters.py:125-149`).
- Patrón a seguir: `ProductionOrders.refrigerate/release` (bloqueo `for_update` de la orden, puertos `StockGateway`/`CostGateway`, `Actor`, 409 con `code`) (`production/application/orders.py:160-200`; `production/api/order_views.py:19-50,147-170`). Errores de faltantes ya modelados con `IngredientShortage`/`InsufficientIngredients` (`production_order.py:35-53`) y 409 `insufficient_stock` (`order_views.py:30-38`).
- Dependencias permitidas: `production → {catalog, costing, inventory, modularity}` (`sales/tests/test_boundaries.py:23`); no se necesita ninguna nueva.
- Persistencia: `production_order` con constraint de estado (`infrastructure/django/models.py:44-77`); última migración `0004_release_lot.py`.
- Frontend: `features/production/pages/order-detail` con acciones y secciones por estado (`order-detail.component.html:14-23,118-133`); pantalla de referencia del DDR de liberación.

### Hipótesis / supuestos no confirmados
- S1: el saldo a granel restante = disponible del lote en Inventario (físico si liberado), no una columna propia.
- S2: la orden permanece `ready_to_pack` aunque el lote se agote (no se crea estado «Empacada»); fuera de alcance.
- S3: el reintento se identifica con un `request_id` (UUID) generado por el cliente por intento de empaque; sin él, dos clics serían dos tandas válidas.
- S4: pack y bolsa deben ser productos activos, distintos entre sí y distintos del cuñapé a granel, que controlan stock en la empresa.

### Módulos y dependencias relacionadas
Producción (nueva entidad Empaque, caso de uso, API, UI), Inventario (salidas con lote, entrada del pack; nuevo `source_type`), Costeo (valoración), Catálogo (productos).

### Implementaciones similares existentes
`ProductionOrders.refrigerate` (todo o nada, consumo + entrada + costo) y `release` (idempotente bajo bloqueo de la orden).

### Comportamiento actual
Una orden Listo para empacar no puede transformarse en producto de venta: los cuñapés a granel liberados no tienen salida hacia packs.

### Restricciones
`Decimal` para cantidades y dinero; migración aditiva (no editar `0001`–`0004`); aislamiento por `company_id`; módulos solo por `services`; reglas validadas en el backend; sin texto hardcodeado (i18n es/en/pt); sin dependencias nuevas.

### Riesgos identificados
Atomicidad de 3 movimientos + costo + registro; doble envío; condición de carrera por bolsas compartidas con otros documentos (Inventario revalida bajo su bloqueo de almacén); costo promedio mezcla lotes (aceptado); productos mal elegidos (validación).

### Veredicto de complejidad
**NEEDS_PLAN** — nueva entidad y migración aditiva dentro de un solo módulo, sin dependencias nuevas entre módulos ni decisión arquitectónica nueva; las reglas de Inventario y Costeo ya existen.

### Diseño requerido
**SI** — nuevo formulario/diálogo «Registrar empaque» y sección de historial en el detalle de la orden.

## Diseño
`docs/design/DDR-empacar-bolsas-de-6-venta-detalle-registrar-empaque.md`.

## Arquitectura
No aplica según veredicto (decisiones en el PLAN).

## Plan
`docs/plans/PLAN-2026-11-27-empacar-bolsas-de-6-venta-detalle.md` (v1, COMPLETO, READY).

## Implementación
**Backend:** dominio `Packing` con conversión fija 6:1 y validaciones (INV-02, INV-03; AC-01, AC-07); caso de uso `ProductionOrders.pack` bajo bloqueo de la orden, idempotente por `request_id` (INV-01, INV-05; AC-03, AC-06); adaptadores `InventoryStock.pack_out/pack_in/lot_available` (pre-chequeo que lista todos los faltantes, INV-04, AC-02; salida del lote con `lot_id`, bolsas y pack sin lote) y `CostingGateway.cost_packing_*` (INV-07, AC-05); entidad `PackingModel` + migración aditiva `0005_packing` generada con `makemigrations`; `POST …/pack/` (201/200) y campo `packing` en el detalle de la orden (API-01, API-02; AC-04); `production_packing` en `SOURCE_TYPES` de Inventario.
**Frontend:** `PackDialogComponent` (NgbModal, ng-select de pack y bolsa, cantidad, resumen, faltantes), sección «Empaques» con saldo a granel e historial y botón «Registrar empaque» en `order-detail` (UI-01..03; AC-08); filtro de movimientos con el nuevo origen; i18n es/en/pt. Pantalla de referencia: detalle de orden existente (DDR); sin componentes compartidos nuevos.
**Pruebas escritas:** dominio (`PackingDomainTests`), API (`OrderPackApiTests`: AC-01..AC-07, EDGE-01), Karma (servicio, diálogo, detalle).
**Ejecutadas:** dominio + `order_domain` + `test_boundaries` (26 OK, sin BD); Karma `production` 72 OK; `npm run lint` e `i18n:check` OK; `ruff`/`flake8` limpios en `modules/production` y `inventory/domain/movement.py`. **No ejecutadas:** pruebas de API del backend y `makemigrations --check` contra BD, porque esta sesión no tiene `DATABASE_URL` (no se lee `.env`); la migración se generó con `makemigrations`. Debe correrlas `delivery-publish`/la persona con PostgreSQL.
**Desviaciones:** ninguna de alcance. El pre-chequeo de saldos en el adaptador (para listar todos los faltantes) se suma a la revalidación de Inventario, que cubre la carrera (EDGE-02).
**Deuda técnica:** `RefrigerationRejected` se reutiliza para conflictos de Inventario al empacar (nombre histórico); el historial no pagina.

## Review
Quality Gate ciclo 1 (subagente aislado): **PASS** — sin hallazgos Critical/High/Medium. Evidencia: backend con PostgreSQL, suite completa 2656 OK (autor) y `modules.production`+`test_boundaries` 125 OK (revisor); `makemigrations --check` sin cambios; `ruff`/`flake8` limpios; `npm run lint` e `i18n:check` OK; Karma `production` 72 OK (autor). **No verificado:** revisión visual en navegador (UI-01..03 solo por lectura de código).
**Revisión visual (navegador integrado, base PostgreSQL aparte con datos de prueba):** flujo completo verificado: diálogo con resumen en vivo («36 u del lote … y 6 bolsas; ingresarán 6 packs»), registro (saldo a granel 118 → 82, historial con lote, bolsas, costo «Sin costo» y usuario), validación de campo («Elige un producto») y faltante 409 («Bolsa: necesitas 10, hay 4 (faltan 6)»). Móvil 390 px: diálogo sin desborde. Defecto hallado y corregido: el historial era una tabla con scroll horizontal en móvil (el DDR pide apilada); ahora son tarjetas en pantallas estrechas, como Ingredientes (prueba Karma añadida). Tema oscuro revisado solo en móvil y forzando la clase `dark` de la plantilla; escritorio solo en tema claro.
Hallazgos Low (no bloquean, sin REV): (1) sin prueba de EDGE-02/EDGE-03; (2) un `request_id` repetido con otros datos devuelve el empaque anterior sin avisar; (3) faltante de carrera sin unidad en el mensaje; (4) selector de productos limitado a 100; (5) `_packing` arma datos en la vista; (6) historial sin paginar.

## Publicación
PR #143 (base `produccion`) listo para aprobación humana; no se mergea. Señalar al aprobador: toca base de datos (migración `0005_packing`). Sin ADR ni dependencias nuevas entre módulos. Revisión visual hecha (ver `## Review`).
