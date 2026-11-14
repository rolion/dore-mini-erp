# TASK-pagos-servicios-libro-entradas: Integrar pagos de servicios con el libro de entradas (PB-COB-002)

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** NO
**Rama:** task/TASK-pagos-servicios-libro-entradas
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/70
**Fuente:** https://trello.com/c/9owWNvVx/17-pb-cob-002-integrar-pagos-de-servicios-con-el-nuevo-libro-de-entradas

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-14 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta de Trello; `main` al día (52579a2, incluye PB-ACC-001/002/003) | delivery-start |
| 2026-11-14 | INVESTIGATION → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE (dinero, transacción entre dos módulos, nueva dependencia `receivables → accounting`); sin diseño visual nuevo | delivery-start |
| 2026-11-14 | PLANNING → ENGINEERING | Specification READY: la tarjeta y el patrón de PB-ACC-003 cubren las reglas; decisiones técnicas en el ADR | delivery-start |
| 2026-11-14 | ENGINEERING → REVIEW | Implementación completa según plan v1 | delivery-build |

## Investigación

### Requerimiento
Insumo de la tarjeta PB-COB-002 (P1; **no es una Specification aprobada**). Historia: como responsable de caja, cada pago confirmado de una proforma de servicios genera una entrada única por el dinero recibido, conservando comprobante y saldo actuales. Esperado: con accounting habilitado, resolver método → cuenta en el servidor y guardar pago, imputaciones, saldo y entrada en la misma transacción; si falta mapeo, la cuenta es inválida o falla el registro contable, no se confirma nada y se muestra un error accionable. Cada anticipo/abono/pago final genera una entrada por el monto recibido; crear, aceptar o versionar la proforma no genera entradas; un pago distribuido entre tratamientos genera una sola entrada. Reutilizar y verificar la idempotencia existente (pérdida de respuesta y concurrencia), conservar CB-NNNNNN y referencia estable al pago; reintento con datos incompatibles no se acepta. Conservar fecha efectiva, moneda, método, cuenta y autor; cambiar el mapeo solo afecta próximos pagos. Permiso de cobro, no de edición contable; no exponer notas clínicas. Funciona con Ventas deshabilitado; con accounting deshabilitado, comportamiento actual. Sin anulaciones, contramovimientos ni reembolsos; cancelar una proforma no devuelve dinero. Criterios: proforma Bs 300 con anticipo 100, abono 50 y final 150 → tres entradas y saldo cero; pago distribuido en dos tratamientos → un comprobante y una entrada; doble envío / reintento / concurrencia sobre el mismo pago no duplican; pagos distintos concurrentes respetan saldo; fallo contable o mapeo ausente no persiste nada y el reintento produce una única pareja pago/entrada; método → cuenta, fecha, moneda y CB coinciden entre origen y libro; empresa ajena no cobra ni consulta; funciona con Ventas y con accounting deshabilitados. Pruebas de integración backend y recorrido proforma → pago → libro. Fuera: reversiones (PB-ACC-006), regularización histórica (PB-ACC-004), validación final (PB-ACC-005), reporting.

### Hechos encontrados
- `backend/modules/receivables/application/collections.py:62-91` — `CollectionService.register_payment`: replay por `idempotency_key` + huella (`_digest`, `:37-40`) → bloquea obligación → vuelve a mirar replay → bloquea proforma → `Obligation.register_payment` → `repository.add_payment` → `source.mark_collected`. No hay integración contable.
- `backend/modules/receivables/application/collections.py:93-101` — `_replay`: misma clave y mismo contenido devuelve el pago registrado (200); otra huella o compromiso distinto → `ObligationStateError` (409). La idempotencia pedida ya existe; falta verificarla con la entrada.
- `backend/modules/receivables/api/views.py:68-78,139-153` — `_run` envuelve en `transaction.atomic()`; `ObligationStateError` → 409 `Conflict`; `PaymentCreateView` responde 201 / 200 (replay). `_user_name` (`:56`) y `request.user.pk` ya llegan al servicio.
- `backend/modules/receivables/infrastructure/django/models.py:36-62` — `PaymentModel` con `company_id`, `receipt_number` (CB), `payment_method`, `payment_date`, `recorded_by(_name)`, `idempotency_key` único por empresa; `receipt_number` único por empresa. El id del pago es estable (`origin_id`).
- `backend/modules/receivables/domain/obligation.py:145-175` — `register_payment` valida línea aceptada, monto, método (`PaymentMethod`, mismos códigos que el libro), fecha no futura, imputaciones = monto y ≤ saldo; una sola `Payment` con varias `Allocation`.
- `backend/modules/receivables/infrastructure/adapters.py:1-35` — único lugar de Cobros que conoce otros módulos (`quotations`, `dentistry`) por `services`; ahí vive el patrón para añadir `accounting`.
- `backend/modules/sales/infrastructure/adapters.py:169-199` y `docs/adr/ADR-pagos-ventas-libro-entradas-integracion-e-idempotencia.md` — patrón ya aprobado de PB-ACC-003: puerto, `module_gate.is_enabled(company, 'accounting')`, `resolve_account` → si `None`, rechazo accionable; `record_entry` con `EntryInput`; `EntryValidationError`/`EntryConflict` → 409.
- `backend/modules/accounting/services.py:34-95` — `resolve_account`, `EntryInput` (`origin_kind='SERVICE'`, `origin_id` = pago, `origin_document_ref` = número de proforma, `receipt_number` = CB), `record_entry` (exige transacción; idempotente por `(empresa, origen)`; `EntryConflict` si difiere).
- `backend/modules/sales/tests/test_boundaries.py:15-28` — mapa de dependencias: `receivables` no incluye `accounting`; hay que añadirla (solo vía `services` desde infraestructura). `modularity/domain/modules.py:30` ya declara `receivables` como opcional de `accounting`.
- `backend/config/permissions.py`, `receivables/api/views.py:36-46` — el cobro exige admin de empresa + módulos de la fuente; no existe permiso contable y `record_entry` no es endpoint, así que cobrar no exige nada contable.
- Frontend: `features/receivables/pages/commitment-detail.component.ts:39,73` — el error del servidor (`failure.message`) ya se muestra al registrar un pago; no hace falta pantalla nueva.
- `backend/modules/receivables/tests/test_api.py:23-110` — `TransactionTestCase` con proformas reales, doble envío y concurrencia ya probados; base para nuevas pruebas.

### Hipótesis / supuestos no confirmados
- «Permiso de cobro» = el permiso actual de Cobros (admin de empresa con los módulos de la fuente); el producto no tiene permisos granulares. Cobrar no requiere el módulo `accounting` habilitado para el operador, solo que esté habilitado en la empresa para generar la entrada.
- Moneda de los pagos de servicios: `BOB` (única de los flujos, `accounting/domain/catalog.py` `FLOW_CURRENCY`).
- Pagos anteriores a habilitar accounting no reciben entrada (regularización en PB-ACC-004); un replay de un pago previo tampoco crea entrada.

### Módulos y dependencias relacionadas
`receivables` (agregado `Obligation`/`Payment`), `accounting` (fachada `services`), `quotations` y `dentistry` (fuentes, sin cambios), `modularity` (puerto `module_gate`).

### Implementaciones similares existentes
Pagos de Ventas → libro (PB-ACC-003, `sales/infrastructure/adapters.py:169`, `sales/tests/test_payment_ledger.py`); idempotencia de Cobros (`collections.py`).

### Comportamiento actual
El pago de una proforma guarda `PaymentModel`/`AllocationModel`, marca líneas cobradas y no toca Contabilidad. No existe error por mapeo ausente.

### Restricciones
Dinero en `Decimal`; no editar migraciones aplicadas (no hace falta ninguna); dominio sin Django; `receivables` solo consume `accounting` desde infraestructura vía `services`; orden de bloqueo obligación → proforma → cuenta; no tocar reporting.

### Riesgos identificados
- Habilitar accounting convierte el método sin cuenta en rechazo del cobro (mensaje guía a Contabilidad).
- Orden de bloqueos: la cuenta se bloquea al final (`record_entry`), después de obligación y proforma; sin ciclos con la configuración de Contabilidad (bloquea empresa → cuenta).
- Un reintento de una clave cuyo primer intento se revirtió por fallo contable debe poder completarse (no queda pago huérfano porque todo es una transacción).

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — dinero, transacción atómica entre dos módulos y nueva dependencia permitida `receivables → accounting`; decisión técnica breve en ADR (sin migraciones).

### Diseño requerido
**NO** — sin pantallas nuevas; el error del servidor ya se muestra en el detalle del compromiso.

## Diseño
No aplica.

## Arquitectura
Ver `docs/adr/ADR-pagos-servicios-libro-entradas-puerto-y-atomicidad.md`.

## Plan
Ver `docs/plans/PLAN-2026-11-14-pagos-servicios-libro-entradas.md` (v1, COMPLETO).

## Implementación
Según plan v1, sin desviaciones. `ObligationStateError.code` (API-01); puerto `PaymentLedger` en `CollectionService` y llamada tras `add_payment` (INV-02, INV-05, AC-03); `PaymentLedgerAdapter` con `module_gate`, `resolve_account` y `record_entry` (INV-03, AC-05..AC-07); la vista inyecta el adaptador y expone `code` en el 409; frontera `receivables → accounting`. Pruebas: `receivables/tests/test_payment_ledger.py` (AC-01..AC-10, concurrencia incluida). Suite completa del backend ejecutada por quien implementa: 1607 pruebas OK (no es el Quality Gate). Sin cambios de frontend ni migraciones. Deuda: ninguna.

## Review
_Pendiente_

## Publicación
_Pendiente_
