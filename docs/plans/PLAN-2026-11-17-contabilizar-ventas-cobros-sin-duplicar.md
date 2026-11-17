# PLAN-2026-11-17-contabilizar-ventas-cobros-sin-duplicar (v2)

**Task:** TASK-contabilizar-ventas-cobros-sin-duplicar · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** `docs/design/DDR-contabilizar-ventas-cobros-sin-duplicar-errores-accionables-en-detalle-de-pedido.md` · `docs/adr/ADR-contabilizar-ventas-cobros-sin-duplicar-puerto-reconocimiento-y-cobro.md`

## Objective
Contabilizar por partida doble el reconocimiento de la venta (al confirmar el pedido) y cada cobro (contra Cuentas por cobrar) usando la configuración y la fachada de CONT-12, sin duplicar ingresos ni escribir un mismo importe por dos caminos, con atomicidad, idempotencia y los controles de saldo y concurrencia existentes.

## Context
Base: `task/TASK-configurar-asientos-automaticos-modulo` (PR #86; no está en `main`). Ver TASK (hechos con `archivo:línea`, decisiones de la persona) y ADR.

# Specification

## Domain context
`sales` (pedido, cobros) consume `accounting` solo por `accounting.services` desde su infraestructura. Costo/stock = INV-01 (no se toca).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Reconocimiento | Asiento `SALE_RECOGNITION`: Debe Cuentas por cobrar / Haber Ingresos por ventas, una vez por pedido | CONT-12, `domain/posting.py:70` |
| Cobro | Asiento `SALE_PAYMENT`: Debe cuenta de dinero del método / Haber Cuentas por cobrar, uno por pago | `posting.py:71` |
| Pedido reconocido | Pedido con asiento de reconocimiento (`find_automatic_entry`) | ADR §3 |
| Cobertura | `coverage_status(fecha)`: si la operación debe crear asiento | `services.py:165` |
| Libro anterior | Entradas de una cuenta (`record_entry`, origen `PRODUCT`) | `services.py:226` |

## Current behavior
Ver TASK › Hechos. Confirmar no contabiliza; cada cobro crea una entrada del libro anterior si Contabilidad está habilitada (`adapters.py:169-198`); se puede cobrar un pedido NEW; el total es editable hasta READY; cancelar conserva los pagos.

## Expected behavior
Con **cobertura** de la fecha de la operación:
- **Confirmar** (NEW → IN_PREPARATION) crea un único asiento de reconocimiento por el total del pedido (con descuento), fechado hoy. Total 0 → sin asiento.
- **Cobrar** un pedido reconocido crea un asiento de cobro por el monto del pago, fechado en `payment_date`, y **no** una entrada en el libro anterior. Pagos parciales y mixtos = un asiento por pago.
- **Cobrar un pedido NEW** se rechaza (confirmar primero).
- **Pedido reconocido**: no cambia su total; no se cancela con cobros; si se cancela sin cobros, se revierte el reconocimiento con las cuentas originales.
- Configuración faltante o inválida bloquea confirmar/cobrar con mensaje accionable (nunca se omite en silencio).
Sin cobertura (Contabilidad deshabilitada, antes del corte, hueco): todo funciona como hoy, sin exigir cuentas. Un pedido confirmado antes de la cobertura se cobra por el camino actual (libro anterior si el módulo está habilitado).

## Domain rules / invariants
- **INV-01** (nueva) Un pedido tiene como máximo un asiento de reconocimiento (`origin_id` = id del pedido).
- **INV-02** (nueva) Cada cobro tiene como máximo un asiento (`origin_id` = id del pago) y **nunca** además una entrada del libro anterior.
- **INV-03** (nueva) Reconocimiento y cobros nunca duplican el ingreso: Ingresos = Σ reconocimientos (no Σ cobros); Cuentas por cobrar = reconocido − cobrado.
- **INV-04** (existente) Saldo: un pago no supera el saldo pendiente; la fila del pedido se bloquea (`select_for_update`); el pago es idempotente por `idempotency_key`.
- **INV-05** (existente, CONT-02/12) Importes `Decimal` > 0 en BOB; fecha en período abierto; idempotencia y reversión con cuentas originales.
- **INV-06** (nueva) Todo es atómico: si falla el asiento no queda confirmación, pago ni saldo cambiado.

## Acceptance criteria
- **AC-01** (tarjeta 1) Venta de 1.000 a crédito confirmada y cobro de 300: Ingresos (Haber) 1.000; Cuentas por cobrar (Debe 1.000, Haber 300) = 700; Caja/Banco (Debe) 300.
- **AC-02** (tarjeta 2) Venta de 500 confirmada y cobrada completa: Ingresos 500, Cuentas por cobrar 0, Caja 500 (Ingresos no es 1.000).
- **AC-03** (tarjeta 3) Reintento del mismo cobro (misma `idempotency_key`) y de confirmaciones repetidas no duplican asientos; dos cobros concurrentes que sumen más que el saldo: solo entra lo que cabe, sin exceder el saldo ni duplicar.
- **AC-04** Pagos mixtos (varios métodos) y parciales: un asiento por pago con la cuenta de su método; `origin_id` enlaza pago y pedido.
- **AC-05** Configuración faltante/inválida o cuenta deshabilitada al confirmar o cobrar → 409 `posting_configuration_missing` con `issues`; el pedido/pago no cambia y no hay asiento.
- **AC-06** Con cobertura, cobrar un pedido NEW → 409 `order_not_confirmed`; sin cobertura sigue permitido como hoy.
- **AC-07** Pedido reconocido: agregar/quitar/cambiar ítems y descuento → 409 `order_total_locked`; notas, cliente y fechas siguen editables.
- **AC-08** Cancelar: pedido reconocido sin cobros → estado CANCELLED y reversión del reconocimiento (cuentas originales); con cobros → 409 `order_has_payments_posted` sin cambios; pedido no reconocido → como hoy.
- **AC-09** Fecha de cobro sin cobertura en un pedido reconocido → 409 `payment_date_not_covered`; período cerrado → 409 con mensaje del motor; nada se guarda.
- **AC-10** Camino único: cobros de pedidos reconocidos no crean entrada en el libro anterior; cobros de pedidos no reconocidos (confirmados antes de la cobertura) siguen en el libro anterior; ningún cobro en ambos.
- **AC-11** Sin Contabilidad habilitada o sin cobertura: ningún asiento, ninguna exigencia de cuentas, mismas respuestas que hoy.
- **AC-12** Entregar un pedido no crea asientos (costo = INV-01).
- **AC-13** Aislamiento por empresa: configuración y asientos de una empresa no afectan a otra.
- **AC-15** (v2) Confirmar con cobertura un pedido que ya tiene cobros (hechos sin cobertura) → 409 `order_has_prior_payments`; el pedido sigue NUEVO y no hay asiento. Sin cobertura se confirma como hoy.
- **AC-14** Frontend: el detalle muestra el rechazo con `detail` y, para configuración faltante, la lista de `issues` y el enlace a la configuración de Ventas; es/en/pt, accesible, usable a 375 px y en tema oscuro.

## Edge cases / Error cases
- **EDGE-01** Pedido con total 0 (descuento = subtotal): se confirma sin asiento; no admite cobros (saldo 0).
- **EDGE-07** (v2) Pedido NUEVO cobrado antes de la cobertura y confirmado después: se bloquea (AC-15); la salida es cancelarlo y crearlo de nuevo.
- **EDGE-02** Pedido confirmado antes de la cobertura y cobrado después: camino actual, sin reconocimiento (no se «completa» retroactivamente).
- **EDGE-03** Cobro con fecha anterior a la del reconocimiento: permitido si el período está abierto y hay cobertura.
- **EDGE-04** Cuenta configurada que se deshabilita entre confirmar y cobrar: el cobro se bloquea con mensaje accionable; la reversión usa cuentas originales.
- **EDGE-05** Reenvío de un cobro ya contabilizado (replay) responde 200 sin crear nada, aunque la configuración haya cambiado (idempotencia previa a la validación).
- **EDGE-06** Método de pago sin cuenta de dinero configurada: `posting_configuration_missing` (con cobertura); sin cobertura, comportamiento actual (`payment_method_without_account` solo si el módulo está habilitado y camino anterior).

## Authorization / permissions
Sin cambios: permisos y `required_modules = ('sales',)` existentes; la empresa sale del usuario autenticado (`company_id_from`). No hay endpoints nuevos.

## API contract
Compatible hacia atrás; solo respuestas 409 nuevas con la forma existente `{code, detail}`:
- **API-01** `POST /api/orders/<id>/prepare/` (confirmar): 409 `order_has_prior_payments` (v2), 409 `posting_configuration_missing` (`+ issues:[{code, subject, message}]`) o error del motor traducido.
- **API-02** `POST /api/orders/<id>/payments/`: 409 `posting_configuration_missing`, `order_not_confirmed`, `payment_date_not_covered`, o error del motor; 200 en replay, 201 al crear (sin cambios).
- **API-03** `POST/PATCH/DELETE` de ítems y `POST discount/`: 409 `order_total_locked` (solo pedido reconocido).
- **API-04** `POST /api/orders/<id>/cancel/`: 409 `order_has_payments_posted` (solo reconocido con cobros).
Sin cambios en las rutas de configuración de CONT-12.

## UI behavior
Según DDR (UI-01): alerta tenue en el detalle del pedido con `detail`/`issues` y enlace «Ir a Configuración de Ventas»; sin pantallas nuevas ni cambios en `design-system.md`.

## Non-functional requirements
Confirmar y cobrar ≤ consultas razonables (cobertura + resolución del evento ≤ 8 consultas añadidas por operación, sin N+1). Todo filtrado por `company_id`. Sin dependencias nuevas.

## Out of scope
Costo de ventas e inventario (INV-01); reembolsos y devoluciones; anticipos de clientes; impuestos; conversión de divisas; asiento directo Caja/Ingresos; endpoint de verificación previa; migración de cobros históricos al motor; Servicios/Cobros (`receivables`); traducir los mensajes de Contabilidad.

## Open questions
- (No bloquea) ¿La fecha contable del reconocimiento debería ser `order_date` en lugar de la fecha de confirmación? Hoy: confirmación.

# Test Specification

## Unit tests
Comandos con puertos falsos (`sales/tests/fakes.py`): orden de operaciones, camino por reconocimiento, bloqueos de total, cancelación, replay, total 0.

## Integration tests (backend, `sales/tests/test_sales_posting.py` + ajustes)
Con Contabilidad real (cuentas por rol, métodos, período abierto y `journal_balances`): AC-01, AC-02, AC-04, AC-05..AC-12 vía API; concurrencia con hilos (`TransactionTestCase`, patrón de `accounting/tests/test_concurrency.py`) para AC-03; aislamiento con dos empresas (AC-13). Ajustes a `test_payment_ledger.py` (camino anterior sin cobertura) y `test_boundaries.py` sin cambios (solo `services`). Fachada: prueba de `find_automatic_entry` en `accounting/tests/test_posting_service.py`.

## Frontend tests
Specs de `order-detail` y `order-payments` (alerta con `detail` e `issues`, enlace, reintento); `i18n:check`; `ng lint`, `ng build`, suite completa.

## E2E
**NO** — el flujo se verifica por integración backend con Contabilidad real y specs de componentes; revisión visual en navegador (375 px, tema oscuro) durante la publicación.

## Regression tests
Suites `sales`, `accounting`, `receivables`, `reporting`, `shared`/fronteras y frontend completa.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-02, AC-04 | `test_sales_posting` (saldos por `journal_balances` y líneas de los asientos) |
| AC-03 | `test_sales_posting` (replay y confirmación repetida) + prueba de concurrencia con hilos |
| AC-05, AC-06, AC-07, AC-08, AC-09 | `test_sales_posting` vía API (409 con `code`, sin cambios ni asientos) |
| AC-10 | `test_sales_posting` + `test_payment_ledger` (entradas del libro anterior vs asientos) |
| AC-11 | `test_payment_ledger`/`test_api` existentes en verde + prueba sin módulo/sin cobertura |
| AC-12 | `test_sales_posting` (entregar no crea asientos) |
| AC-15 | `test_sales_posting.test_confirming_with_coverage_an_order_paid_before_it_is_rejected` |
| AC-13 | `test_sales_posting` (dos empresas) |
| AC-14 | specs de `order-detail`/`order-payments`, `i18n:check`, revisión visual |

# Implementation Plan

## Architecture considerations
Puerto `SalesPosting` en `sales/application`, adaptador en `sales/infrastructure/adapters.py`; dominio `Order` sin cambios; sin migraciones. Cumple `docs/architecture/ddd.md` (solo fachada `services`).

## Proposed solution
Ver ADR §1-9.

## Files/components affected
- Backend: `accounting/services.py` (+ `find_automatic_entry`, `__all__`) y su prueba; `sales/application/ports.py` (puerto), `commands.py` (Start/Add/Change/Remove/Discount/Cancel/Register), `sales/infrastructure/adapters.py` (`SalesPostingAdapter`, camino anterior detrás del puerto), `sales/api/views.py` (cablear adaptador; 409 con `issues`), `sales/tests/fakes.py` y pruebas nuevas/ajustadas.
- Frontend: `features/sales/pages/order-detail`, `components/order-payments`, `models`/servicio (tipo del error con `issues`), `assets/i18n/{es,en,pt}.json`, specs.
- Docs: TASK/ADR/DDR/PLAN; `docs/architecture/ddd.md` solo si cambia algo de fronteras (no se espera).

## Implementation steps
1. **Fachada**: `find_automatic_entry` en `accounting.services` + prueba. → INV-01/02.
2. **Puerto y adaptador** `SalesPosting` (covers, recognize, is_recognized, record_payment, reverse_recognition; traducción de `PostingConfigurationMissing`, `JournalValidationError`, `JournalConflict`, `DateOutsideFiscalPeriod`/`FiscalPeriodClosed` a `OrderRuleViolation` con `issues`); camino anterior (`record_entry`) detrás del mismo puerto. → AC-05, AC-09, AC-10.
3. **Reconocer al confirmar** (`StartOrderPreparation`): verificación previa → transición → asiento. → AC-01, AC-02, EDGE-01.
4. **Cobro** (`RegisterPayment`): decidir camino, `order_not_confirmed`, asiento o entrada anterior, `payment_date_not_covered`. → AC-01..AC-04, AC-06, AC-09, AC-10.
5. **Bloqueos**: total bloqueado en ítems/descuento; cancelar con reversión o rechazo. → AC-07, AC-08.
6. **Vistas**: cablear `SalesPostingAdapter`, mapear `issues` en el 409. → API-01..04.
7. **Pruebas backend** (AC-01..AC-13 incluyendo hilos) + `makemigrations --check` + flake8.
8. **Frontend**: tipo de error con `issues`, alerta en detalle y pagos, enlace, i18n es/en/pt, specs. → AC-14.
9. Lint, `i18n:check`, `ng build`, suites completas; revisión visual en publicación.

## Database / migrations
Ninguna (`makemigrations --check` sin cambios). Nunca editar migraciones aplicadas.

## Risks
- Cambios de reglas de estado solo con cobertura: documentados y probados (AC-06..AC-08).
- Coexistencia de libros: el camino por reconocimiento es determinista; prueba AC-10.
- Concurrencia: apoyada en el bloqueo del pedido + idempotencia por pago; prueba con hilos (puede requerir `TransactionTestCase`).
- Orden de la verificación previa respecto de la transición para no dejar el pedido a medio confirmar: la transacción de `_run` lo deshace.

## New dependencies
Ninguna.

## Changelog
- **v2** (2026-11-17): [Specification] AC-15, EDGE-07 y API-01: confirmar con cobertura un pedido con cobros previos se rechaza (409 `order_has_prior_payments`). Cambio **solicitado explícitamente por la persona en el chat** (opción A de REV-01). [Implementation Plan] sin cambios de pasos: la comprobación vive en `SalesPostingAdapter.recognize`.
