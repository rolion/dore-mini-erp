# PLAN-2026-11-04-cobrar-servicios-anticipos-pagos-parciales (v1)

**Task:** TASK-cobrar-servicios-anticipos-pagos-parciales · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-cobrar-servicios-anticipos-pagos-parciales-pantallas-cobros · ADR-…-modulo-cobros-y-fuentes · ADR-…-pagos-idempotencia-y-concurrencia

## Objective
Cobrar las líneas aceptadas de proformas (genéricas y odontológicas) mediante anticipos y abonos imputados por tratamiento, con una sola obligación por compromiso, saldo siempre derivado, idempotencia y sin sobrepago concurrente.

## Context
Ver TASK. PB-COT-002 (decisiones y versiones) ya está en `main`. No se reutiliza el agregado `Order` de Ventas; sí su contrato de pago.

# Specification

## Domain context
Bounded context nuevo **Cobros** (`receivables`). Lee de `quotations` y `dentistry` por fachada; `customers` solo para identidad. No toca Ventas, Inventario ni Reportes.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Compromiso | Proforma (por número, sin versión) que se cobra | ADR módulo |
| Obligación | Agregado único por compromiso con pagos e imputaciones | ADR módulo |
| Importe aceptado/exigible | Σ importes de líneas aceptadas de la versión vigente | `proforma.py:156` |
| Imputación | Parte de un pago aplicada a una línea (por `lineage_id`) | ADR pagos |
| Saldo | Exigible − cobrado (obligación y por línea) | Trello |

## Current behavior
Las proformas se aceptan y versionan pero no se cobran (`quotations/domain/proforma.py:254-297`); Ventas solo cobra pedidos de productos (`sales/domain/order.py:348`).

## Expected behavior
Desde una proforma presentada con líneas aceptadas se registran pagos que se reparten explícitamente entre líneas aceptadas; se ve propuesto, aceptado, cobrado y saldo; reintentos y concurrencia no distorsionan el saldo.

## Domain rules / invariants
- INV-01: solo líneas aceptadas de una proforma presentada vigente son cobrables; rechazadas/pendientes no.
- INV-02: una obligación por `(empresa, tipo de fuente, número)`, sin duplicarse al versionar.
- INV-03: pago: monto > 0 con 2 decimales, método ∈ enum de Ventas, fecha no futura (por defecto hoy), referencia ≤ 100.
- INV-04: Σ imputaciones = monto; cada imputación > 0 y ≤ saldo de su línea; sin líneas repetidas.
- INV-05: saldo = exigible − cobrado, nunca negativo; derivado, no asignable.
- INV-06: misma clave de idempotencia y mismo contenido → mismo pago (sin duplicar); mismo key con otro contenido → 409.
- INV-07: dos pagos concurrentes nunca superan el saldo (serialización por bloqueo de la obligación).
- INV-08: una línea con cobro no puede rectificarse a rechazada (409) ni editarse/quitarse en versiones nuevas; la marca se hereda en `new_version`. *(cambia COT-002; aprobado por el usuario)*
- INV-09: pagos e imputaciones inmutables; sin anulación (fuera de alcance).
- INV-10: cobrar no crea pedidos, ni movimientos de inventario, ni ventas.

## Acceptance criteria
- AC-01: aceptado 300 → pago 100 imputado → saldo 200; pago 50 → saldo 150.
- AC-02: el mismo envío (misma clave) dos veces crea un solo pago.
- AC-03: dos pagos concurrentes de 100 sobre saldo 150 → solo uno se registra; cobrado ≤ 150.
- AC-04: líneas rechazadas o pendientes no aparecen como cobrables y rechazan la imputación (400).
- AC-05: nueva versión de la proforma no crea otra obligación y conserva lo cobrado por línea (`lineage_id`).
- AC-06: rectificar a rechazada una línea con cobro devuelve 409 (genérica y dental).
- AC-07: la suma de imputaciones debe igualar el monto; imputar más que el saldo de la línea → 400.
- AC-08: el detalle muestra propuesto, aceptado, cobrado y saldo separados, pagos con sus imputaciones y comprobante.
- AC-09: la lista filtra por cliente, fecha y estado de cobro.
- AC-10: aislamiento por empresa y módulo habilitado (otra empresa → 404; módulo deshabilitado → bloqueo).
- AC-11: la UI conserva datos ante fallos, impide doble envío, muestra resumen antes de confirmar y estados de carga/vacío/error/éxito; no muestra diagnósticos.
- AC-12: i18n es/en/pt completo.

## Edge cases / Error cases
Proforma en borrador/superseded (no cobrable, 409); sin líneas aceptadas (exigible 0, sin acción); monto con >2 decimales; fecha futura; método inválido; clave reutilizada con otro contenido (409); fuente inexistente o de otra empresa (404); creación concurrente de la misma obligación (un solo registro, `IntegrityError` capturado).

## Authorization / permissions
Usuario autenticado con empresa; `required_modules`: genérica `('receivables','quotations')`, dental `('receivables','dentistry','customers','services')`. Empresa siempre desde el usuario (`shared/tenancy.py`).

## API contract
Prefijo `/api/receivables/`:
- API-01: `GET obligations/?customer_id=&status=&date_from=&date_to=&page=` → lista paginada.
- API-02: `GET commitments/<kind>/<number>/` (`kind` = `quotation|dental`) → detalle derivado (totales, líneas, pagos, `allowed_actions`), también sin pagos previos.
- API-03: `POST commitments/<kind>/<number>/payments/` con `idempotency_key`, `amount`, `payment_method`, `payment_date?`, `reference?`, `allocations[{line_id, amount}]` → 201 (nuevo) o 200 (`replayed`); 400 validación, 404 fuente, 409 estado/clave.
- API-04: ampliación aditiva del detalle de ambas proformas con `collectible` (bool) para mostrar «Cobrar»; sin romper campos existentes.

## UI behavior
- UI-01: lista de Cobros (plantilla lista de solo lectura con filtros). UI-02: detalle de cobro (plantilla detalle con selección de líneas). UI-03: diálogo de pago con resumen (plantilla formulario con líneas y resumen). UI-04: botón «Cobrar» en proformas y enlace en la ficha del paciente. Estados y teclado según DDR.

## Non-functional requirements
`Decimal` en todo el dinero; índices `(company_id, customer_id)`, `(company_id, source_kind, source_number)`; sin N+1 en la lista; sin dependencias nuevas.

## Out of scope
Anulación/reversión de pagos; profesionales y honorarios; ejecución de tratamientos; impresión de comprobante; ingresos de servicios en Reportes; catálogo configurable de métodos; sucursales; rol de caja; consumo de stock.

## Open questions
Ninguna que bloquee.

# Test Specification

## Unit tests
Dominio `Obligation`: INV-01…05, 09; saldo derivado; imputaciones; lineage. Dominio de `Proforma`/`DentalProforma`: INV-08 (rectificar bloqueado, marca heredada).
## Integration tests
API de ambos tipos de fuente: AC-01…10 (idempotencia, doble envío, concurrencia con hilos/`TransactionTestCase`, dos empresas, módulo deshabilitado, versionado). Migraciones y `test_boundaries` (dependencias y fachadas). Catálogo de módulos.
## E2E
**NO** — los flujos se cubren con pruebas de API y de componentes; no se instala Playwright.
## Regression tests
Suites de `quotations`, `dentistry`, `modularity` y límites de módulos; lint/i18n/test del frontend.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01,05 | Integración API (secuencia 100/50, nueva versión) + unit dominio |
| AC-02,03 | Integración API (reintento; `TransactionTestCase` concurrente) |
| AC-04,07 | Unit dominio + API |
| AC-06 | Unit dominio de ambas fuentes + API |
| AC-08,11 | Pruebas de componente (detalle, diálogo, estados, doble envío) |
| AC-09 | Integración API lista + componente de filtros |
| AC-10 | Integración API (empresa/módulo) + `test_boundaries` |
| AC-12 | Prueba de claves i18n + `npm run i18n:check` |

# Implementation Plan

## Architecture considerations
Ver ADRs. Orden de bloqueo obligación → proforma. Fuentes consumidas solo vía `infrastructure/adapters.py` y `services.py`.

## Proposed solution
Módulo `receivables` con agregado `Obligation`, casos de uso `GetCommitment`, `RegisterPayment`, `ListObligations`; puertos hacia las fuentes; vistas DRF; feature Angular `receivables`; marca `collected` en líneas de ambas fuentes.

## Files/components affected
- Backend nuevo: `backend/modules/receivables/{domain,application,infrastructure,api,migrations,tests}`; registro en `config/settings/base.py` y `config/urls.py`.
- Backend modificado: `quotations` y `dentistry` (`services.py` con fachada, columna `collected`, regla en `rectify`, `new_version`, migración aditiva, serializer `collectible`); `modularity/domain/modules.py` (+ tests); `sales/tests/test_boundaries.py` (dependencias).
- Frontend: `features/receivables/{pages,components,services,models}`, rutas, menú, botón en `proforma-detail` y `dental-proforma-detail`, enlace en `patient-detail`, `assets/i18n/{es,en,pt}.json`, módulo en la lista de módulos.
- Docs: `docs/producto/modulos-implementados.md`.

## Implementation steps
1. Dominio `Obligation`/`Payment`/`Allocation` + pruebas (INV-01…05, 09).
2. Fachadas y marca `collected` en `quotations` y `dentistry` con migración y regla INV-08 (AC-06).
3. Modelos, migración y repositorio de `receivables` (bloqueo, contador, lote idempotente).
4. Casos de uso `GetCommitment`/`RegisterPayment`/`ListObligations` (AC-01…05, 07).
5. API, serializers, permisos y módulos requeridos; registro en `modularity`; `collectible` en proformas (AC-08…10).
6. Pruebas de integración, concurrencia y límites de módulos.
7. Frontend: modelos, servicio API, lista, detalle, diálogo con resumen, accesos y menú (UI-01…04, AC-08,09,11).
8. i18n es/en/pt y verificación `i18n:check`, lint y pruebas (AC-12).
9. Actualizar `docs/producto/modulos-implementados.md`.

## Database / migrations
`receivables/0001_initial` (obligation, payment, allocation, counter); migración nueva aditiva en `quotations` y `dentistry` (`collected` bool default `False`). Nunca se editan migraciones aplicadas.

## Risks
Interbloqueos (orden fijo documentado); carrera pago/rectificación (bloqueo de proforma); `IntegrityError` en alta simultánea de la obligación; duplicación entre las dos fuentes.

## New dependencies
Ninguna.
