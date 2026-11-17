# PLAN-2026-11-17-contabilizar-ventas-cobros-sin-duplicar (v3)

**Task:** TASK-contabilizar-ventas-cobros-sin-duplicar · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** `docs/design/DDR-contabilizar-ventas-cobros-sin-duplicar-errores-accionables-en-detalle-de-pedido.md` · `docs/adr/ADR-contabilizar-ventas-cobros-sin-duplicar-reconocimiento-al-entregar-y-anticipos.md` (vigente) · `docs/adr/ADR-contabilizar-ventas-cobros-sin-duplicar-puerto-reconocimiento-y-cobro.md` (decisiones 1, 4, 7, 8, 9, 10 vigentes; 2, 3, 5, 6 reemplazadas)

## Objective
Contabilizar Ventas por partida doble reconociendo el ingreso **al entregar** y registrando los cobros anteriores a la entrega como **anticipos de clientes** (Pasivo), sin duplicar ingresos, con atomicidad, idempotencia y los controles de saldo y concurrencia existentes. Alcance contable: Caja/Bancos, Anticipos de clientes, Cuentas por cobrar e Ingresos por ventas; sin costo de ventas ni inventario contable.

## Context
Base: `accounting` (CONT-12 integrado). Ver TASK (hechos con `archivo:línea`, decisiones de la persona) y ADRs. v1/v2 reconocían al confirmar; v3 cambia esa regla por pedido expreso de la persona (2026-11-17).

# Specification

## Domain context
`sales` (pedido, cobros, entrega) consume `accounting` solo por `accounting.services` desde su infraestructura. `accounting` amplía su catálogo de eventos (rol y eventos nuevos). La salida física de almacén de la entrega se conserva intacta; costo/stock = INV-01.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Anticipo de cliente | Cobro registrado antes de entregar: Debe Caja/Bancos / Haber Anticipos de clientes (Pasivo), un asiento por pago (`SALE_ADVANCE`) | ADR v2 §1 |
| Reconocimiento de entrega | Asiento `SALE_DELIVERY` al entregar: Haber Ingresos por el total; Debe Anticipos aplicados + Debe Cuentas por cobrar (saldo) | ADR v2 §1, §6 |
| Cobro posterior | Cobro con el pedido reconocido: Debe Caja/Bancos / Haber Cuentas por cobrar (`SALE_PAYMENT`) | CONT-12 |
| Reconocido al confirmar | Pedido con asiento `SALE_RECOGNITION` (lógica anterior, histórico) | ADR v2 §3 |
| Cobro sin asiento | Cobro hecho fuera de cobertura (libro anterior o ninguno) | ADR v2 §5 |
| Cobertura | `coverage_status(fecha)`: si la operación debe crear asiento | `accounting/services.py:165` |

## Current behavior
Ver TASK › Hechos. Con cobertura, confirmar crea `SALE_RECOGNITION` (CxC/Ingresos por el total) y los cobros crean `SALE_PAYMENT`; un pedido NUEVO no se puede cobrar; el total se bloquea tras reconocer; cancelar sin cobros revierte el reconocimiento; confirmar un pedido con cobros previos se rechaza (v2).

## Expected behavior
Con **cobertura** de la fecha de la operación y Contabilidad habilitada:
- **NUEVO** (crear/editar): sin asiento. Cobrar → 409 `order_not_confirmed`.
- **Confirmar** (NUEVO → EN PREPARACIÓN) y **marcar listo**: sin asiento, sin exigir configuración ni cobros.
- **Cobrar en EN PREPARACIÓN / LISTO** (pedido no reconocido): un asiento por pago, Debe cuenta del método / Haber Anticipos de clientes. Se conserva el límite del saldo comercial.
- **Entregar** (LISTO → ENTREGADO): un único asiento: Haber Ingresos por el total con descuento; Debe Anticipos de clientes por los anticipos del pedido y Debe Cuentas por cobrar por el resto; sin líneas de importe cero; no mueve Caja/Bancos. Con la salida de almacén existente en la misma transacción.
- **Cobrar con el pedido entregado** (o reconocido): Debe método / Haber Cuentas por cobrar; no toca Ingresos ni Anticipos.
- El pedido nunca exige pagos para confirmar, prepararse, marcarse listo ni entregarse.
- **Total estable** tras confirmar (409 `order_total_locked`).
- **Cancelar** sin entregar y sin cobros contabilizados: sin asiento; con cobros contabilizados: 409; entregados: no cancelables (sin cambio).
- **Transición:** un pedido con reconocimiento anterior no se reconoce otra vez (sus cobros siguen contra CxC y cancelar sin cobros revierte su reconocimiento); un pedido con cobros sin asiento no se entrega con cobertura (409); un pedido con anticipos cuya entrega no tiene cobertura no se entrega (409).
Sin cobertura o sin el módulo: funcionamiento actual (libro anterior o nada).

## Domain rules / invariants
- **INV-01** (nueva) Un pedido tiene como máximo un asiento de entrega (`origin_id` = id del pedido) y solo si no tiene `SALE_RECOGNITION`.
- **INV-02** (nueva) Cada cobro tiene como máximo un asiento (`SALE_ADVANCE` o `SALE_PAYMENT`, `origin_id` = id del pago) y nunca además una entrada del libro anterior.
- **INV-03** (nueva) Ingresos = total del pedido (una vez); anticipos aplicados = Σ cobros con `SALE_ADVANCE` (≤ total); Cuentas por cobrar al entregar = total − anticipos; ningún anticipo se aplica dos veces.
- **INV-04** (existente) Un pago no supera el saldo comercial pendiente; la fila del pedido se bloquea; idempotente por `idempotency_key`.
- **INV-05** (existente, CONT-02/12) Importes `Decimal` > 0 en BOB, partida doble, fecha en período abierto, idempotencia por `(empresa, origen)`, reversión con cuentas originales.
- **INV-06** (existente) Atomicidad: entrega + salida de almacén + asiento, y cobro + asiento, son todo o nada.
- **INV-07** (nueva) Ningún asiento lleva líneas de importe cero.

## Acceptance criteria
- **AC-01** Configuración: la configuración de Ventas ofrece **Anticipos de clientes** (Pasivo; sin código ni id fijo). Una cuenta ajena, inactiva o que no es de Pasivo → 400. El panel muestra el rol y los eventos «Cobrar un pedido por adelantado», «Reconocer la entrega de un pedido» y «Cobrar una venta»; el reconocimiento al confirmar ya no se muestra.
- **AC-02** NUEVO: crear/editar sin asiento; cobrar → 409 `order_not_confirmed` (con cobertura), sin cobertura como antes.
- **AC-03** Confirmar y marcar listo no crean asientos ni exigen configuración; ningún estado exige pagos.
- **AC-04** Cobro en EN PREPARACIÓN o LISTO (parcial, completo, mixto): un asiento `SALE_ADVANCE` por pago con la cuenta de su método (300 en efectivo → Debe Caja 300 / Haber Anticipos 300); sin Anticipos o sin cuenta del método → 409 `posting_configuration_missing`; no se supera el saldo.
- **AC-05** Entrega sin pagos previos (1.000): Debe Cuentas por cobrar 1.000 / Haber Ingresos 1.000.
- **AC-06** Entrega con anticipo de 300: Debe Anticipos 300, Debe Cuentas por cobrar 700 / Haber Ingresos 1.000.
- **AC-07** Entrega pagada completa por adelantado: Debe Anticipos 1.000 / Haber Ingresos 1.000; sin línea de cuentas por cobrar.
- **AC-08** Entregar no mueve Caja/Bancos; reconoce el ingreso una sola vez; repetir la entrega o competir entre dos entregas no duplica el asiento ni aplica anticipos dos veces; un cobro concurrente con la entrega se serializa (queda como anticipo aplicado o como cobro posterior, nunca perdido).
- **AC-09** Cobro tras la entrega (700 en banco): Debe Bancos 700 / Haber Cuentas por cobrar 700; no afecta Ingresos ni Anticipos. Venta de 25 sin anticipo cobrada al entregar: entrega (CxC 25 / Ingresos 25) y luego cobro (Caja 25 / CxC 25) → Caja 25, Ingresos 25, CxC 0; entregar sin cobrar deja la cuenta por cobrar pendiente.
- **AC-10** Pedido con reconocimiento anterior (`SALE_RECOGNITION`): al entregar no se reconoce otra vez (sin asiento nuevo); sus cobros siguen Debe método / Haber CxC; cancelar sin cobros revierte su reconocimiento original.
- **AC-11** Cancelar: pedido sin entregar y sin cobros → sin asiento; con cobros contabilizados → 409 `order_has_payments_posted`; entregado → sin cambio.
- **AC-12** Total estable: con cobertura, productos/cantidades/descuento de un pedido confirmado → 409 `order_total_locked`; notas, cliente y fechas siguen editables; sin cobertura, como antes.
- **AC-13** Transición: entregar con cobertura un pedido con algún cobro sin asiento → 409 `order_has_unposted_payments` (nada cambia); entregar sin cobertura un pedido con anticipos contabilizados → 409 `delivery_date_not_covered`; entregar sin cobertura sin anticipos → como antes, sin asiento; los pedidos entregados sin asiento se cobran por el libro anterior como antes. No se modifica ningún asiento histórico.
- **AC-14** Atomicidad y validación previa: configuración incompleta, período cerrado o error del motor en un cobro o en la entrega → 409 accionable y no queda pago, entrega, salida de almacén ni asiento.
- **AC-15** Sin Contabilidad o sin cobertura: sin asientos ni exigencias (cobros por el libro anterior si el módulo está habilitado).
- **AC-16** Trazabilidad e integridad: anticipo con `origin_id` = id del pago, entrega con `origin_id` = id del pedido; aislamiento por empresa y permisos existentes.
- **AC-17** Frontend: el detalle del pedido y el diálogo de entrega muestran los rechazos (`detail` e `issues`) con enlace a la configuración de Ventas; es/en/pt, accesible, usable a 375 px y en tema oscuro.

## Edge cases / Error cases
- **EDGE-01** Pedido de total 0: se entrega sin asiento; no admite cobros.
- **EDGE-02** Cobro en preparación/listo con fecha del cobro sin cobertura → 409 `payment_date_not_covered`.
- **EDGE-03** Fecha de entrega efectiva en período cerrado o fuera de período → 409 `fiscal_period_unavailable`; nada cambia.
- **EDGE-04** Cuenta configurada deshabilitada entre el anticipo y la entrega → 409 de configuración al entregar; la reversión de lo ya contabilizado usa cuentas originales.
- **EDGE-05** Replay de un cobro (misma `idempotency_key`): 200 sin crear nada, aunque la configuración haya cambiado.
- **EDGE-06** Método de pago inactivo o sin cuenta: mismo error de configuración (con cobertura).
- **EDGE-07** Pedido entregado antes de la cobertura y cobrado después: libro anterior, sin asiento nuevo (histórico).
- **EDGE-08** Cobros fuera de cobertura en un pedido que se confirma o prepara con cobertura: se rechaza la entrega con cobertura (AC-13); la salida (cobrar de nuevo o regularizar) es una **decisión pendiente** (ver TASK).

## Authorization / permissions
Sin cambios: permisos y `required_modules = ('sales',)`; la empresa sale del usuario autenticado. Configuración de cuentas: permiso por defecto de CONT-12.

## API contract
Compatible hacia atrás; solo respuestas 409 con la forma existente `{code, detail}` (+ `issues` en configuración):
- **API-01** `POST /api/orders/<id>/prepare/` y `.../ready/`: sin errores contables nuevos (se eliminan `posting_configuration_missing` y `order_has_prior_payments` de v1/v2 en `prepare`).
- **API-02** `POST /api/orders/<id>/payments/`: 409 `order_not_confirmed`, `posting_configuration_missing`, `payment_date_not_covered`, `fiscal_period_unavailable`, `ledger_*`; 200 replay, 201 al crear.
- **API-03** `POST /api/orders/<id>/deliver/`: 409 `posting_configuration_missing`, `order_has_unposted_payments`, `delivery_date_not_covered`, `fiscal_period_unavailable`, `ledger_*` (además de los existentes de stock).
- **API-04** `POST/PATCH/DELETE` de ítems y `POST discount/`: 409 `order_total_locked`.
- **API-05** `POST /api/orders/<id>/cancel/`: 409 `order_has_payments_posted`.
- **API-06** Configuración (CONT-12): `GET /api/accounting/posting-config/?module=sales` incluye el rol `CUSTOMER_ADVANCES` y los eventos nuevos; `PUT .../roles/CUSTOMER_ADVANCES/` con la validación de Pasivo. Sin cambio de forma.
- **Fachada:** `post_automatic_entry(..., advance_applied=None)` y `automatic_entry_origins(company_id, event, origin_ids)` (aditivas).

## UI behavior
Según DDR (actualizado): sin pantallas nuevas; el diálogo de entrega y el detalle muestran los rechazos accionables; el panel de configuración se actualiza por datos.
- **UI-01** Diálogo de entrega: `alert-error` con el mensaje del servidor y, para `posting_configuration_missing`, enlace a la configuración de Ventas.
- **UI-02** Detalle del pedido: alerta con `issues` (ya implementada) para el cobro.

## Non-functional requirements
Entrega o cobro: ≤ 10 consultas contables añadidas, sin N+1 por pago (una consulta para los orígenes de anticipos). Todo filtrado por `company_id`. Sin dependencias nuevas.

## Out of scope
Costo de ventas e inventario contable; reembolsos, devoluciones y anulaciones de pedidos entregados; impuestos; conversión de divisas; acción «Entregar y cobrar» (no existe en la interfaz); migración o ajuste automático de asientos históricos; regularización de cobros sin asiento; traducción de los mensajes de Contabilidad; endpoint de verificación previa.

## Open questions
- **Decisión pendiente (no bloquea):** ¿cómo se resuelven los pedidos con cobros fuera de cobertura que se entregan con cobertura (hoy se bloquean con 409)? Opciones: asiento manual de regularización del anticipo, reconocer solo el saldo, o registrar el cobro de nuevo.
- **Decisión pendiente (no bloquea):** ¿qué tratamiento tienen los pedidos ya reconocidos al confirmar y cancelados con cobros? Hoy se bloquea la cancelación.
- Criterio adoptado: la fecha contable de la entrega es la fecha de entrega efectiva; el bloqueo de total aplica con cobertura.

# Test Specification

## Unit tests
Dominio de Contabilidad (`domain/posting.py`, sin BD): catálogo con el rol y eventos nuevos, `extra_debit_role`, evento histórico oculto de `events_for`, `modules_using`. Comandos de Ventas con puertos falsos (`sales/tests/fakes.py`): ruteo de cobros, entrega con y sin anticipos, cancelaciones, bloqueos.

## Integration tests (backend)
Contabilidad real (cuentas por rol, métodos, período abierto, `journal_balances`) en `sales/tests/test_sales_posting.py` (reescrito para v3): AC-02..AC-16, incluida concurrencia con hilos (`TransactionTestCase`) para AC-08. `accounting/tests/test_posting_service.py` y `test_posting_config_api.py`: AC-01, `post_automatic_entry` con `advance_applied`, `automatic_entry_origins`. Ajustes a `test_payment_ledger.py`, `test_unified_journey.py` (corte futuro, libro anterior) y a las pruebas de CONT-12 que listan los eventos de Ventas.

## Frontend tests
Spec del diálogo de entrega con `posting_configuration_missing`, spec del detalle (cobro), `i18n:check`, lint, build, suite completa.

## E2E
**NO** — el flujo se verifica por integración backend con Contabilidad real y specs de componentes; revisión visual en navegador durante la publicación.

## Regression tests
Suites `sales`, `accounting`, `receivables`, `reporting`, `inventory` (salida al entregar), `shared` (fronteras) y frontend completa.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | `test_posting_config_api` + `test_posting_domain` (rol Pasivo, eventos visibles/ocultos) |
| AC-02, AC-03 | `test_sales_posting` (NUEVO, confirmar, listo: sin asientos) |
| AC-04 | `test_sales_posting` (anticipos parciales/mixtos, configuración faltante) |
| AC-05, AC-06, AC-07 | `test_sales_posting` (saldos con `journal_balances` y líneas del asiento) |
| AC-08 | `test_sales_posting` (reintento, entrega repetida) + concurrencia con hilos |
| AC-09 | `test_sales_posting` (cobro posterior; ejemplo de 25) |
| AC-10 | `test_sales_posting` (pedido con `SALE_RECOGNITION` sembrado: sin re-reconocer, cobros, cancelar) |
| AC-11 | `test_sales_posting` (cancelar sin/con cobros, entregado) |
| AC-12 | `test_sales_posting` (bloqueo con cobertura; sin cobertura libre) |
| AC-13 | `test_sales_posting` (cobros sin asiento, fecha de entrega sin cobertura, histórico) |
| AC-14 | `test_sales_posting` (período cerrado, cuenta deshabilitada, sin residuos) |
| AC-15 | `test_sales_posting` + `test_payment_ledger` (sin módulo / corte futuro) |
| AC-16 | `test_sales_posting` (`origin_id`, dos empresas) |
| AC-17 | specs de `delivery-dialog`/`order-detail`, `i18n:check`, revisión visual |

# Implementation Plan

## Architecture considerations
Dominio de Contabilidad: catálogo ampliado y compatible; fachada aditiva; puerto `SalesPosting` de Ventas rediseñado (`recognition_state`, `locks_total`, `has_posted_payments`, `record_payment`, `recognize_delivery`, `reverse_recognition`). Dominio `Order` sin cambios. Sin migraciones. Cumple `docs/architecture/ddd.md`.

## Proposed solution
Ver ADR v2 (§1-§10).

## Files/components affected
- Backend `accounting/`: `domain/posting.py` (rol, eventos, `extra_debit_role`, `active`), `application/posting.py` (líneas extra en vista previa), `services.py` (`advance_applied`, `automatic_entry_origins`), tests.
- Backend `sales/`: `application/ports.py`, `application/commands.py` (`StartOrderPreparation` sin contabilidad, `DeliverOrder`, `RegisterPayment`, `CancelOrder`, bloqueos), `infrastructure/adapters.py`, `api/views.py`, `tests/fakes.py` y pruebas.
- Frontend: `features/sales/components/delivery-dialog` (+ spec), detalle del pedido (sin cambios de lógica), `assets/i18n/{es,en,pt}.json`.
- Docs: TASK/ADR/DDR/PLAN.

## Implementation steps
1. **Catálogo** (INV-01/07, AC-01): rol `CUSTOMER_ADVANCES`, eventos `SALE_ADVANCE` y `SALE_DELIVERY` (`extra_debit_role`), `SALE_RECOGNITION` histórico oculto; vista previa de tres líneas; pruebas.
2. **Fachada** (INV-02/03/05/07): `advance_applied`, `automatic_entry_origins`; pruebas de líneas y de importes cero.
3. **Puerto y adaptador** (AC-04..AC-16): `recognition_state`, ruteo de cobros, entrega, cancelación, bloqueo de total, traducción de errores.
4. **Comandos**: quitar contabilidad de confirmar; `DeliverOrder` con asiento en la misma transacción; `RegisterPayment` con ruteo; `CancelOrder`; bloqueos. → AC-02..AC-13.
5. **Vistas**: cablear el adaptador en entregar. → API-01..05.
6. **Pruebas backend** (reescribir `test_sales_posting`; ajustar las de CONT-12) + `makemigrations --check`.
7. **Frontend**: diálogo de entrega (rechazos con enlace), specs, i18n. → AC-17.
8. Lint, `i18n:check`, `ng build`, suites completas; revisión visual en publicación.

## Database / migrations
Ninguna (`makemigrations --check` sin cambios).

## Risks
- Cambio de reglas ya implementadas en v1/v2: el código y las pruebas se reescriben; riesgo de regresión en `test_payment_ledger` y `test_unified_journey` (corte futuro).
- Pedidos bloqueados en la transición (AC-13): requiere decisión de negocio posterior.
- Primer evento con dos líneas de Debe: afecta la vista previa del panel y `modules_using`.
- Concurrencia entrega/cobro: se apoya en el bloqueo de la fila del pedido; prueba con hilos.

## New dependencies
Ninguna.

## Changelog
- **v1** (2026-11-17): versión inicial (reconocimiento al confirmar).
- **v2** (2026-11-17): [Specification] AC-15 y EDGE-07: confirmar con cobertura un pedido con cobros previos se rechaza (`order_has_prior_payments`). Cambio solicitado por la persona (opción A de REV-01).
- **v3** (2026-11-17): [Specification] El ingreso se reconoce **al entregar** y los cobros previos son **anticipos de clientes**: nuevo rol Pasivo `CUSTOMER_ADVANCES` y eventos `SALE_ADVANCE` y `SALE_DELIVERY`; confirmar y marcar listo no contabilizan; reglas de transición (pedidos con reconocimiento anterior, cobros sin asiento, entrega sin cobertura); se elimina `order_has_prior_payments` de `prepare` (v2/AC-15 reemplazado por AC-13). Los AC se renumeran (AC-01..AC-17). [Implementation Plan] pasos reescritos; `SALE_RECOGNITION` queda como evento histórico. Cambio **solicitado explícitamente por la persona en el chat** (instrucción de rediseño del flujo contable de Ventas). Reemplaza parcialmente el ADR de v1.
