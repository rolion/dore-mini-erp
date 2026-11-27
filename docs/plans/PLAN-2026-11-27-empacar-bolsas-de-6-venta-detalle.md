# PLAN-2026-11-27-empacar-bolsas-de-6-venta-detalle (v2)

**Task:** TASK-empacar-bolsas-de-6-venta-detalle · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-empacar-bolsas-de-6-venta-detalle-registrar-empaque · Ninguno

## Changelog
- **v2 — [Specification]** (aprobado por el usuario en el chat): se agrega la **etiqueta (sticker)** como tercer insumo del empaque. Decisiones: 1 por pack (fija), **opcional**, con control de stock, faltantes y costo igual que la bolsa. Nuevos INV-08 y AC-09; API-01/API-02 aditivos (`label_product_id`; `label_product`, `labels_quantity`, `labels_per_pack`); migración aditiva `0006_packing_label`. **[Implementation Plan]**: `Packing.create(label, label_requested)`, `pack_out` con lista de insumos (bolsa y etiqueta), `cost_packing_outputs` con la línea de etiqueta. Además, textos del diálogo más claros (ayuda bajo cada campo) y resumen con etiquetas.
- v1 — versión inicial.

## Objective
Permitir registrar, desde una orden Listo para empacar, tandas de packs de 6 cuñapés: descuenta cuñapés del lote y bolsas, ingresa los packs al inventario con su costo, de forma atómica e idempotente, y muestra el historial y el saldo a granel.

## Context
Fuente: tarjeta DORE-PROD-007; base `produccion` (incluye PROD-004 y PROD-005). Ver TASK.

# Specification

## Domain context
Producción (nueva entidad **Empaque**, dueña de la regla); Inventario (salidas con lote, entrada del pack); Costeo (valoración); Catálogo (productos).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Empaque (tanda) | Registro inmutable de una transformación de N packs | Tarjeta |
| Pack | Producto del catálogo que se vende al detalle; 6 cuñapés por unidad | Tarjeta / usuario |
| Bolsa | Producto del catálogo consumido: 1 por pack | Tarjeta / usuario |
| Granel / saldo a granel | Disponible del lote de la orden en Inventario | ADR lotes |

## Current behavior
La orden `ready_to_pack` no tiene acción de empaque (`production_order.py:256-274`, `order_urls.py:6-12`).

## Expected behavior
En una orden `ready_to_pack`, «Registrar empaque» con N packs, un producto pack y un producto bolsa registra: salida de `6N` cuñapés del lote de la orden, salida de `N` bolsas (stock sin lote), entrada de `N` packs (stock sin lote, disponible para venta) y el costo. Todo o nada. Se puede repetir en varias tandas mientras haya saldo.

## Domain rules / invariantes
- INV-01 Solo se empaca una orden `ready_to_pack` (lote liberado); en otro estado, 409.
- INV-02 Conversión fija: cuñapés = 6 × packs; bolsas = 1 × packs; packs = N (entero 1…99999).
- INV-03 Pack y bolsa: productos de la empresa, activos, que controlan stock, distintos entre sí y distintos del producto a granel de la orden.
- INV-04 Si faltan cuñapés (disponible del lote) o bolsas (stock sin lote en el almacén de la orden), se rechaza listando **todos** los faltantes (producto, requerido, disponible, faltante) y no se escribe nada (ni movimientos, ni costo, ni empaque).
- INV-05 Idempotencia: `request_id` (UUID) único por orden; repetir devuelve el empaque ya registrado sin nuevos movimientos.
- INV-06 Un empaque no se edita ni se elimina (reversa fuera de alcance).
- INV-07 Costo: con Costeo activo y valorizado, costo total = 6N × promedio del cuñapé + N × promedio de la bolsa (vía `cost_outputs`); costo unitario del pack = total ÷ N (6 decimales, mitad hacia arriba), registrado con `cost_receipt`. Sin Costeo o sin costo: el pack entra sin costo y el empaque guarda `cost_total = null`.

- INV-08 Etiqueta (opcional): si se elige `label_product_id`, es un producto activo que controla stock, distinto del pack, de la bolsa y del granel; se descuentan `1 × packs` etiquetas (stock sin lote, almacén de la orden), entran en el pre-chequeo de faltantes (INV-04) y en el costo (INV-07). Sin etiqueta no se descuenta nada por ese concepto.

## Acceptance criteria
- AC-01 Con lote liberado de 118 cuñapés y 10 bolsas, empacar 6 packs descuenta 36 del lote (restan 82) y 6 bolsas, e ingresa 6 packs; los tres movimientos referencian el empaque.
- AC-02 Faltan cuñapés o bolsas → 409 `insufficient_stock` con todos los faltantes; los saldos quedan intactos y no se crea empaque.
- AC-03 Repetir la misma solicitud (mismo `request_id`) responde 200 con el mismo empaque y no duplica movimientos ni costo.
- AC-04 Dos tandas distintas (distinto `request_id`) se registran y el detalle muestra ambas con lote de origen, cantidades, usuario, fecha y costo, más el saldo restante a granel.
- AC-05 El costo del pack incorpora cuñapés y bolsas según INV-07; sin costo disponible el empaque se registra con costo vacío.
- AC-06 Orden que no está `ready_to_pack` → 409; orden de otra empresa → 404.
- AC-07 Validación (400 por campo): `packs` no entero/≤0/fuera de rango; `request_id` ausente/no UUID; pack o bolsa inexistente/inactivo/sin stock/repetido/igual al granel.
- AC-08 Detalle de orden: acción «Registrar empaque» (solo `ready_to_pack`), diálogo con resumen y faltantes, sección «Empaques» con saldo y historial; textos en es/en/pt.
- AC-09 Con etiqueta elegida: se descuentan N etiquetas (cuarto movimiento `label`), faltan etiquetas → 409 con todos los faltantes sin escribir nada, el costo del pack las incluye, etiqueta inválida (inexistente/inactiva/sin stock/repetida/igual al granel) → 400 por campo `label_product_id`; sin etiqueta el empaque funciona como antes.

## Edge cases / error cases
- EDGE-01 Doble clic: mismo `request_id` (AC-03).
- EDGE-02 Bolsas consumidas por otro documento entre la lectura y la escritura: Inventario revalida bajo su bloqueo y el caso de uso traduce el rechazo a 409 `insufficient_stock` con la transacción revertida.
- EDGE-03 Sin período fiscal abierto u otro `MovementConflict` de Inventario: 409 con `code` y mensaje, nada escrito.
- EDGE-04 Saldo a granel < 6: el backend rechaza con faltante; la UI deshabilita el botón.

## Authorization / permissions
Mismo requisito que el resto de Producción: usuario autenticado con empresa y módulo `production` habilitado (`required_modules`); sin permisos finos nuevos.

## API contract
- API-01 `POST /api/production-orders/<id>/pack/` body `{request_id, packs, pack_product_id, bag_product_id}` → 201 (nuevo) o 200 (repetido) con el empaque; 409 `insufficient_stock` (`shortages[]` como en refrigerar), 409 de estado, 409 de Inventario con `code`; 400 por campo.
- API-02 `GET /api/production-orders/<id>/` agrega (aditivo) `packing: {units_per_pack: 6, bags_per_pack: 1, bulk_available, bulk_unit_abbreviation, packings: [{id, request_id, number, packs, pack_product_id/name, bag_product_id/name, bulk_quantity, bags_quantity, lot_id, lot_code, cost_total, unit_cost, created_at, created_by}]}`; vacío fuera de `ready_to_pack`. Compatible hacia atrás.

## UI behavior
- UI-01 Sección «Empaques» en el detalle (plantilla Detalle del sistema de diseño): saldo a granel, tabla de historial (apilada, con vacío «Aún no hay empaques»).
- UI-02 Diálogo `NgbModal` «Registrar empaque» (DDR): ng-select de pack y bolsa, cantidad, resumen, faltantes en lista, estados cargando/error/éxito.
- UI-03 Botón solo en `ready_to_pack`, deshabilitado con explicación si el saldo < 6.

## Non-functional requirements
Cantidades y dinero en `Decimal`; una transacción; consultas del detalle sin N+1 (productos y lote en una lectura cada uno).

## Out of scope
Reversa/anulación de empaques; estado «Empacada» al agotar el lote; configurar pack/bolsa en Ajustes o recetas; conversiones distintas de 6:1; venta de packs; reportes.

# Test Specification

## Unit tests
Dominio `Packing`: conversión (INV-02), validación de `packs` (AC-07), invariante de productos distintos (INV-03).

## Integration tests
API contra BD de prueba: `OrderPackApiTests` con lote liberado real, productos y movimientos.

## E2E
**NO** — el flujo es de un solo módulo cubierto por pruebas de API y de componentes; no justifica instalar Playwright.

## Regression tests
Suites existentes de `production`, `inventory` (filtro/etiqueta de `source_type` nuevo), `test_boundaries`, `i18n:check`.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | API: saldos de lote/bolsas/packs y movimientos tras 6 packs |
| AC-02 | API: faltante de cuñapés, de bolsas y de ambos; saldos y conteo de empaques intactos |
| AC-03 | API: mismo `request_id` dos veces → un solo empaque y movimientos |
| AC-04 | API: dos tandas; Karma: historial y saldo en detalle |
| AC-05 | API con Costeo adoptado (costo esperado) y sin Costeo (null) |
| AC-06 | API: orden en otro estado → 409; otra empresa → 404 |
| AC-07 | Unit (dominio) + API 400 por campo |
| AC-08 | Karma: detalle y diálogo (botón por estado, faltantes, resumen); `i18n:check` |

# Implementation Plan

## Architecture considerations
Sin ADR: reutiliza puertos y fachadas existentes (`StockGateway`, `CostGateway`, `inventory.services`, `costing.services`); no hay dependencias nuevas entre módulos. Estado de la orden sin cambios (INV-01); el saldo a granel se lee de Inventario (S1) para no duplicar la verdad.

## Proposed solution
Nuevo agregado `Packing` en `production/domain/packing.py` (valida y calcula cantidades). Caso de uso `ProductionOrders.pack(...)` en `application/orders.py`, bajo `for_update` de la orden: busca por `request_id` (idempotencia); valida estado y productos; consulta disponible del lote y saldo de bolsas y arma todos los faltantes; registra con el puerto `StockGateway.pack(...)` (salida del lote con `lot_id` + salida de bolsas + entrada de packs, `source_type='production_packing'`, `source_id=<packing.id>`, `source_line` 'bulk'/'bag'/'pack'); costo vía `CostGateway` con el mismo patrón que refrigerar; guarda el empaque. Idempotencia además por constraint único `(order, request_id)`.

## Files/components affected
- Backend: `production/domain/packing.py` (nuevo), `production/application/orders.py`, `production/infrastructure/adapters.py` (`InventoryStock.pack`, `CostingGateway.cost_packing`), `production/infrastructure/django/{models,order_repository}.py`, `production/api/{order_serializers,order_views,order_urls}.py`, `inventory/domain/movement.py` (`production_packing` en `SOURCE_TYPES`).
- Migración: `production/0005_packing.py` (tabla `production_packing`), aditiva.
- Frontend: `features/production/{models/order.ts, services/orders-api.service.ts, pages/order-detail/*}`, nuevo componente de diálogo `components/pack-dialog`, i18n `es/en/pt`.
- Docs: `docs/architecture/ddd.md` solo si cambia algo (no se espera).

## Implementation steps
1. Dominio `Packing` y pruebas unitarias (INV-02, INV-03, AC-07).
2. Modelo, migración `0005` (`makemigrations`), repositorio (alta, búsqueda por `request_id`, lista por orden).
3. `SOURCE_TYPES` + puertos/adaptadores de Inventario y Costeo (INV-04, INV-07).
4. Caso de uso `pack` (INV-01, INV-04, INV-05; AC-01..03, AC-05, AC-06).
5. Serializer, vista y ruta `pack/`; campo `packing` en el detalle (API-01/02; AC-04, AC-07).
6. Pruebas de API (`OrderPackApiTests`) y de Inventario por el nuevo tipo.
7. Frontend: modelos, servicio, diálogo y sección «Empaques» (UI-01..03; AC-08); i18n es/en/pt; pruebas Karma.
8. Lint (`ruff`, `flake8`, `npm run lint`, `i18n:check`) y suites completas.

## Database / migrations
Una migración aditiva `0005` con la tabla y `UniqueConstraint(order, request_id)`; no se editan `0001`–`0004`. Rollback: revertir la migración elimina solo la tabla nueva (los movimientos de Inventario creados quedarían huérfanos de origen, por eso el despliegue debe ir antes de usar la función).

## Risks
Carrera por bolsas (EDGE-02, cubierto por la revalidación de Inventario); costo promedio mezcla lotes (aceptado por el usuario); `production_packing` en listados de movimientos de Inventario (verificar etiqueta/filtro en pruebas y frontend).

## New dependencies
Ninguna.
