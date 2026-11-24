# PLAN-2026-11-24-cancelar-ventas-registrar-devoluciones (v2)

**Task:** TASK-cancelar-ventas-registrar-devoluciones · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-cancelar-ventas-registrar-devoluciones-acciones-y-vista-previa · ADR-cancelar-ventas-registrar-devoluciones-reversion-orquestada-y-registro

## Objective
Permitir cancelar un pedido (antes de entregar) y registrar la devolución total (después de entregar) desde su detalle, revirtiendo existencias, costo y asientos en una sola transacción, con reembolso externo declarado cuando hay cobros.

## Context
Ver `docs/tasks/TASK-cancelar-ventas-registrar-devoluciones.md`. Decisiones del usuario (2026-11-24): solo devolución total; cobros = reembolso realizado fuera de PocketBiz.

# Specification

## Domain context
Sales (agregado `Order`); fachadas de Inventory, Costing, Accounting; Reporting lee.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Cancelar venta | Anular un pedido no entregado | tarjeta Trello |
| Devolución | Anulación total de un pedido entregado; reingresa stock y contrarresta ingreso y costo | tarjeta Trello |
| Reembolso externo | Dinero devuelto al cliente fuera de PocketBiz; se contabiliza como contrasiento del cobro | decisión del usuario |
| Contrasiento | Asiento con Debe/Haber invertidos, vinculado al original | `accounting/services.py:436` |

## Current behavior
Ver TASK → Hechos encontrados.

## Expected behavior
- `DELIVERED` admite la acción `return`; `NEW/IN_PREPARATION/READY` conservan `cancel`.
- Cancelar con cobros contabilizados ya no se rechaza: exige confirmar el reembolso externo y contrarresta los cobros.
- Devolver reingresa al almacén de origen las unidades que salieron, registra el contra-evento de costo y contrarresta `INVENTORY_SALE_COST`, `SALE_DELIVERY` (y reconocimiento histórico si aplica) y, con reembolso, los cobros.
- El detalle muestra fecha, usuario, motivo, reembolso y los vínculos a movimientos y asientos, conservando originales.

## Domain rules / invariants
- **INV-01** Solo `DELIVERED → RETURNED` por `Order.register_return`; solo `NEW/IN_PREPARATION/READY → CANCELLED` por `cancel`; ambos exigen motivo.
- **INV-02** Si el pedido tiene cobros, la anulación exige `refund_acknowledged=true`; `payment_status` pasa a `REFUNDED`.
- **INV-03** Los contrasientos usan las cuentas originales y fecha de hoy en período abierto; si no, se rechaza todo.
- **INV-04** Sin salida de inventario registrada no hay cambio de existencias.
- **INV-05** Todo (pedido, movimientos, costo, asientos) en una transacción; un fallo no deja nada.
- **INV-06** Reintentos y solicitudes simultáneas no duplican efectos (bloqueo del pedido, estado terminal y reversiones idempotentes por origen).
- **INV-07** `RETURNED` y `CANCELLED` no son «pedido válido» para ventas.

## Acceptance criteria
- **AC-01** Cancelar sin salida deja el stock intacto y revierte los asientos aplicables.
- **AC-02** Cancelar con cobros contabilizados sin confirmar reembolso → 409; confirmado, contrarresta los cobros y deja `REFUNDED`.
- **AC-03** Devolver un pedido entregado repone cada unidad que salió en el almacén de origen y vincula el reverso con el movimiento original.
- **AC-04** La devolución contrarresta ingreso y costo con las cuentas originales; con fecha en período cerrado, rechaza y no cambia nada.
- **AC-05** La devolución registra costo al costo de venta (contra-evento de Costeo, promedio sin cambios).
- **AC-06** Un fallo en cualquier paso (p. ej. período cerrado) deja pedido, stock, costo y asientos como estaban.
- **AC-07** Repetir la solicitud o dos solicitudes simultáneas no duplican stock, costo ni contrasientos.
- **AC-08** Solo rol admin de la misma empresa; otra empresa recibe 404.
- **AC-09** El detalle muestra fecha, usuario, motivo, reembolso y vínculos a movimientos/asientos; la venta original se conserva.
- **AC-10** Las ventas devueltas/canceladas no suman en reportes de ventas.
- **AC-11** La vista previa de devolución no escribe nada y lista productos, almacén, unidades, asientos y cobros.

## Edge cases / Error cases
Pedido sin Contabilidad o sin Inventario (efectos omitidos según habilitación); cobros del libro anterior; pedido sin asientos (anterior a la cobertura); configuración contable ausente (`posting_configuration_missing`); devolver desde otro estado (`invalid_transition`); reembolso sin confirmar (`refund_acknowledgement_required`).

## Authorization / permissions
Rol admin con empresa activa (permiso por defecto); `company_id` del usuario autenticado; módulo `sales` requerido.

## API contract
- **API-01** `POST /api/sales/orders/{id}/cancel/` — body `{reason, refund_acknowledged?}`; compatible (campo nuevo opcional).
- **API-02** `POST /api/sales/orders/{id}/return/` — body `{reason, refund_acknowledged?}` → pedido actualizado.
- **API-03** `GET /api/sales/orders/{id}/return-preview/` — solo lectura.
- **API-04** El pedido expone `cancelled_by_name`, `returned_at`, `returned_by_name`, `return_reason`, `refund_acknowledged` y `reversal` (movimientos y asientos vinculados); `allowed_transitions` incluye `return`.

## UI behavior
- **UI-01** Botón «Registrar devolución» en DELIVERED y diálogo con vista previa (plantilla «Diálogo de acción irreversible con motivo», DDR).
- **UI-02** Al cancelar con cobros, tras indicar el motivo aparece una segunda confirmación del reembolso externo («Ya devolví el dinero»); sin cobros no aparece (v2: reemplaza la casilla dentro del diálogo).
- **UI-03** Sección «Cancelación / Devolución» con vínculos; badge «Devuelto».
- **UI-04** Estados cargando/error/éxito; textos i18n es/en/pt.

## Non-functional requirements
`Decimal` para dinero y cantidades; sin dependencias nuevas.

## Out of scope
Devolución parcial por producto/cantidad; saldo a favor del cliente; reembolso como movimiento de dinero propio; notas de crédito fiscales.

# Test Specification
## Unit tests
Dominio: `register_return`, `cancel` con cobros, `payment_status` REFUNDED, transiciones (INV-01, INV-02).
## Integration tests
Casos de uso con fakes y backend con BD: devolución con/sin salida, con/sin cobros, costo, período cerrado (rollback total), idempotencia y concurrencia, otra empresa, rol, reportes.
## E2E
**NO** — el flujo se cubre con integración API + pruebas de componente del detalle y del diálogo (`provideTestTranslations()`); no es un flujo crítico que justifique instalar Playwright.
## Regression tests
Cancelar sin cobros (comportamiento previo), entrega y cobro existentes.
## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | integración: cancelar sin salida, stock y asientos |
| AC-02 | integración: 409 sin confirmación; con ella, contrasientos y REFUNDED |
| AC-03 | integración inventario: movimientos revertidos en almacén de origen |
| AC-04 | integración contable: cuentas originales; período cerrado → rechazo |
| AC-05 | integración Costeo: contra-evento y promedio sin cambio |
| AC-06 | integración: fallo forzado → rollback de todo |
| AC-07 | integración: segundo intento y reversión idempotente |
| AC-08 | API: 403 rol, 404 otra empresa |
| AC-09 | API (serializer) + componente del detalle |
| AC-10 | prueba de `read_queries`/fachada de ventas |
| AC-11 | API: vista previa sin escrituras; componente del diálogo |

# Implementation Plan
## Architecture considerations
Según el ADR: orquestación en Sales, estado `RETURNED`, campos en `Order`, nuevo `reverse_output_cost` en Costeo.
## Proposed solution
Ver ADR.
## Files/components affected
- Backend Sales: `domain/order.py`, `domain/enums.py`, `application/commands.py` (+`returns.py`), `application/ports.py`, `infrastructure/adapters.py`, `infrastructure/django/{models,mappers,read_queries}.py`, `api/{views,urls,serializers}.py`, migración `0005_*`, tests.
- Backend Costing: `services.py`, `application/cost_use_cases.py`, `domain/cost.py`, migración si cambia `choices`.
- Frontend: `features/sales/{models,services,pages/order-detail,components/return-dialog}`, i18n es/en/pt.
- Docs: `design-system.md` solo si el diálogo introduce un patrón nuevo.
## Implementation steps
1. Dominio: `RETURNED`, campos, `register_return`, `REFUNDED`, transiciones (INV-01/02/07).
2. Costeo: `reverse_output_cost` + tests (AC-05).
3. Puertos y adaptadores de Sales (inventario, costeo, asientos incluyendo libro anterior).
4. Casos de uso `CancelOrder` ampliado y `ReturnOrder` + vista previa (AC-01..07, 11).
5. Migración, mapeadores, API, serializers y exclusión en reportes (AC-08..10).
6. Frontend: botón, diálogo, sección de historial, i18n (UI-01..04).
7. Pruebas, lint (`ruff`/`flake8` solo en lo cambiado), `npm run i18n:check`.
## Database / migrations
`sales/0005` (columnas nuevas) y, si aplica, migración de Costeo; nunca se edita una existente.
## Risks
Orden de bloqueos (pedido → empresa → almacén); cobros del libro anterior; consistencia de reportes.
## New dependencies
Ninguna.

## Changelog
- **v2** (2026-11-24): [Specification] UI-02 cambiado de «casilla de reembolso dentro del diálogo de cancelar» a «segunda confirmación tras el motivo», tras aprobación explícita del usuario en el chat (REV-04). El diálogo de devolución conserva la casilla.
