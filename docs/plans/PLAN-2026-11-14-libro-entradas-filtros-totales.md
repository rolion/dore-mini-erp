# PLAN-2026-11-14-libro-entradas-filtros-totales (v1)

**Task:** TASK-libro-entradas-filtros-totales · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-libro-entradas-filtros-totales-pantallas-entradas · ADR-libro-entradas-filtros-totales-registro-unico-y-contrato

## Objective
Crear en `accounting` el libro inmutable de entradas (cobros recibidos de productos y servicios) con su contrato de registro transaccional e idempotente, y la consulta (API y pantalla) con filtros, totales por moneda sobre todo el conjunto filtrado, periodo y cobertura.

## Context
Ver TASK (hechos con `archivo:línea`), ADR y DDR. Insumo: tarjeta Trello PB-ACC-002. Las integraciones con Ventas y Cobros son PB-ACC-003 y PB-COB-002.

# Specification

## Domain context
`accounting`. `sales` y `receivables` solo como valores de origen (`PRODUCT`, `SERVICE`) y por su estado de habilitación (`shared/module_gate`); nunca se importan.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Entrada | Registro inmutable de dinero efectivamente recibido por un pago | Trello |
| Origen | Tipo de pago que la genera: Productos (pago de pedido) o Servicios (pago de proforma, con comprobante CB) | Trello |
| Fecha efectiva | Fecha del pago en el origen (`payment_date`) | Trello |
| Fecha de creación | Cuándo se registró la entrada en el libro | Trello |
| Cobertura | Periodo del que el libro tiene entradas (no incluye pagos previos a su registro) | Trello/ADR |

Inconsistencia declarada: la tarjeta dice «cuenta destino… permanece tras cambiar mapeo»; el mapeo vive en PB-ACC-001 y aquí solo se guarda la cuenta usada.

## Current behavior
No hay libro ni entradas (TASK).

## Expected behavior
Un módulo de negocio puede registrar una entrada llamando a `services.record_entry` dentro de su transacción; repetir la llamada con los mismos datos devuelve la misma entrada y con datos distintos informa conflicto. El administrador ve en Contabilidad → Entradas el listado paginado, el detalle y los totales por moneda de todo lo filtrado, con periodo y cobertura. Nada puede crearse, editarse ni borrarse desde la API.

## Domain rules / invariants
- INV-01 Monto `Decimal` > 0 con a lo sumo 2 decimales (y ≤ 12 dígitos); nunca `float`.
- INV-02 Método ∈ catálogo (`CASH, QR, BANK_TRANSFER, CARD, OTHER`); moneda ∈ catálogo; origen ∈ {`PRODUCT`, `SERVICE`}.
- INV-03 La cuenta pertenece a la empresa y la moneda de la entrada es la de la cuenta; si no, se rechaza.
- INV-04 Única por `(company_id, origin_kind, origin_id)`; orígenes distintos con el mismo ID coexisten.
- INV-05 Inmutable: el agregado no tiene métodos de cambio y no existe ninguna ruta de alta/edición/borrado.
- INV-06 La cuenta se guarda en la entrada; cambiar el mapeo no la altera.
- INV-07 Sin texto libre del pago ni datos clínicos.
- INV-08 Una cuenta que ya tiene entradas no puede cambiar de moneda (409 `account_in_use`-like con mensaje propio); sigue pudiendo renombrarse y desactivarse según PB-ACC-001. (Cambio aditivo en `UpdateAccount`.)

## Acceptance criteria
- AC-01 `record_entry` válido crea la entrada con todos los campos; rechaza monto ≤ 0 (o con más de 2 decimales), método/origen/moneda inválidos, cuenta de otra empresa o inexistente e incompatibilidad de moneda con la cuenta.
- AC-02 Dos llamadas concurrentes para el mismo origen producen una sola entrada (la segunda recibe `created=False`); el mismo `origin_id` con distinto `origin_kind` crea dos entradas.
- AC-03 Reintento con los mismos datos → misma entrada sin duplicar; con datos distintos (monto, cuenta, moneda, fecha, método, comprobante o referencia) → `EntryConflict`.
- AC-04 `record_entry` fuera de una transacción falla (`EntryContractError`); dentro de la transacción del llamante, si esta se revierte la entrada desaparece, y un conflicto/reintento no rompe la transacción externa.
- AC-05 Con más de una página, `total`, `count` y filtros (fecha efectiva, cuenta, método, origen) corresponden al conjunto completo filtrado; monedas distintas salen en filas separadas, sin convertir; por origen se desglosan.
- AC-06 Tras cambiar el mapeo del método, la entrada previa conserva su cuenta; `resolve_account` aplica el destino nuevo al siguiente registro.
- AC-07 Aislamiento y permisos: listado y detalle solo de la empresa del usuario (detalle ajeno 404); cuenta ajena en el filtro no devuelve datos ajenos; no admin → 403; módulo `accounting` deshabilitado → bloqueo por gate; `source.available` refleja la habilitación del módulo de origen.
- AC-08 La API no tiene POST/PUT/PATCH/DELETE sobre `/entries/` (405) y el listado no contiene texto libre del pago.
- AC-09 La respuesta incluye periodo consultado y cobertura (primera/última fecha efectiva y primer registro); libro vacío devuelve nulos y totales vacíos.
- AC-10 UI: lista con estados cargando/vacío (con y sin filtros)/error/éxito, filtros, paginación, totales por moneda, periodo y cobertura, aviso «cobros recibidos, no saldo»; detalle; enlace al origen solo si `available`; menú Entradas visible para admin con el módulo habilitado.

## Edge cases / Error cases
- EDGE-01 `date_from > date_to` → 400; fecha inválida → 400. EDGE-02 `account_id`/`method`/`origin` desconocidos → 400 (no listan nada ajeno). EDGE-03 `page` fuera de rango → 404 estándar DRF. EDGE-04 Entrada sin usuario (histórica/regularización futura) se muestra «—». EDGE-05 Entrada sin comprobante (productos) muestra «—». EDGE-06 Cuenta de la entrada después inactiva: se sigue mostrando.

## Authorization / permissions
`CompanyAdminPermission`; empresa del usuario autenticado; `required_modules=('accounting',)` en las vistas del libro. `record_entry` no es un endpoint: lo invoca otro módulo ya autorizado para cobrar (no requiere permiso de edición contable).

## API contract
- API-01 `GET /api/accounting/entries/?date_from=&date_to=&account_id=&method=&origin=&page=&page_size=` → `{count, next, previous, results:[Entry], totals:[{currency, count, amount, by_origin:{PRODUCT, SERVICE}}], period:{date_from, date_to}, coverage:{first_payment_date, last_payment_date, first_recorded_at}}`. `Entry = {id, account:{id,name,currency}, currency, amount (texto decimal), payment_date, created_at, method, method_label, recorded_by_name, origin:{kind, label}, source:{id, document_ref, receipt_number, available}}`.
- API-02 `GET /api/accounting/entries/<id>/` → `Entry` (+ `origin_id`).
- API-03 Fachada: `services.record_entry(company_id, EntryInput) -> RecordedEntry{entry, created}`; `EntryInput(account_id, currency, amount, payment_date, method, origin_kind, origin_id, origin_document_ref, receipt_number='', recorded_by=None, recorded_by_name='')`; errores `EntryValidationError`, `EntryConflict`, `EntryContractError`.
- Contrato nuevo y aditivo; ningún endpoint existente cambia.

## UI behavior
- UI-01 Ruta `/pocketbiz/accounting/entries` y `/:id`; menú Contabilidad → Entradas (`adminOnly`, `module: accounting`).
- UI-02 Lista: plantilla «Lista de solo lectura con filtros» (DDR), filtros en la URL, paginación del servidor (20), columnas del DDR.
- UI-03 Totales por moneda con desglose Productos/Servicios; periodo y cobertura; aviso «cobros recibidos».
- UI-04 Detalle: plantilla Detalle; enlace al origen según `available`.
- UI-05 Todo texto con `translate` (es/en/pt) y estados del DDR; propuesta de actualización de `design-system.md` §5 y §6.

## Non-functional requirements
Agregación de totales en SQL con índice `(company_id, payment_date)`; listado sin N+1 (`select_related('account')`). Sin secretos ni dependencias nuevas.

## Out of scope
Integración con Ventas y Cobros (PB-ACC-003, PB-COB-002), regularización (PB-ACC-004), reversiones (PB-ACC-006), cambios en reporting/ventas − gastos, saldos de cuenta, exportación, partida doble, fiscal, egresos, transferencias.

## Open questions
- Ninguna que bloquee. Pendiente para PB-ACC-003/COB-002: qué hacer si la cuenta resuelta está inactiva al cobrar (la entrada la admite; la política de cobro es de esas tarjetas).

# Test Specification

## Unit tests
Dominio `Entry.record` (INV-01, INV-02, INV-05); validaciones de catálogo.

## Integration tests
Servicio `record_entry` con BD (AC-01..04, INV-03/04/06/08): cuenta ajena, moneda, unicidad, `created=False`, conflicto, fuera de transacción, rollback del llamante, savepoint tras conflicto. Concurrencia con hilos (patrón de `accounting/tests/test_concurrency.py`) para AC-02. API con dos empresas (AC-05..09): varias páginas, totales por moneda, filtros, aislamiento, 403/gate, 405, cambio de mapeo. `makemigrations --check`. Test de fronteras de `accounting` (no importa `sales`/`receivables`/`accounts`).

## E2E
**NO** — recorrido cubierto por integración API y specs de componentes; el flujo de punta a punta pago → libro lo valida PB-ACC-005.

## Regression tests
Suites de `accounting`, `modularity`/`test_enforcement` (nueva ruta con módulo `accounting`), `sales`, `receivables` y menú (`sidebar-menu.spec.ts`).

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Dominio + integración servicio |
| AC-02 | Integración con concurrencia (hilos) |
| AC-03 | Integración servicio |
| AC-04 | Integración servicio (`TransactionTestCase`/`atomic`) |
| AC-05 | Integración API (>1 página, dos monedas) |
| AC-06 | Integración API + `resolve_account` |
| AC-07 | Integración API dos empresas, no admin, gate, `available` |
| AC-08 | Integración API (405 y forma de la respuesta) |
| AC-09 | Integración API (con y sin datos) |
| AC-10 | Specs de componentes (lista, detalle, servicio) + `i18n:check` + `sidebar-menu.spec.ts` |

# Implementation Plan

## Architecture considerations
Ver ADR: agregado inmutable en dominio, restricción única, `record_entry` con punto de guardado exigiendo transacción, consulta con agregación SQL, sin imports hacia otros módulos de negocio.

## Proposed solution
Ampliar `accounting` con `domain/entry.py`, `EntryModel`, `DjangoEntryRepository`, casos de uso de consulta, `record_entry` en `services.py`, vistas/serializers de solo lectura y la feature Angular `features/accounting` (lista y detalle).

## Files/components affected
- Backend: `accounting/domain/entry.py` (nuevo), `domain/catalog.py` (orígenes), `infrastructure/django/models.py` y `repositories.py`, `application/use_cases.py` (consulta, guarda de moneda en `UpdateAccount`), `services.py`, `api/serializers.py`, `api/views.py`, `api/urls.py`, `migrations/0002_entry.py`, tests (`test_entry_domain.py`, `test_entry_service.py`, `test_entry_concurrency.py`, `test_entries_api.py`, `test_boundaries.py`), `modularity/tests/test_enforcement.py`.
- Frontend: `features/accounting/pages/entry-list`, `pages/entry-detail`, `services/entries-api.service.ts`, `models/entry.ts`, `app.routes.ts`, `assets/data/routes.json`, `assets/i18n/{es,en,pt}.json`.
- Docs: `docs/design/design-system.md` (§5 variante con totales por moneda, §6 ítem Entradas), `docs/producto/modulos-implementados.md`.

## Implementation steps
1. Dominio `Entry` y catálogo de orígenes + tests (INV-01, 02, 05; AC-01 parcial).
2. Modelo, migración `0002`, repositorio con inserción segura y lectura por origen (INV-03, 04, 06).
3. `record_entry` y errores en `services.py` (AC-01..04) + tests de servicio y concurrencia.
4. Guarda de moneda en `UpdateAccount` si la cuenta tiene entradas (INV-08) + test.
5. Casos de uso de consulta, totales/cobertura SQL, serializers, vistas, URLs y gate (API-01, 02; AC-05..09) + tests API, `test_enforcement` y fronteras.
6. Servicio y modelos Angular; lista con filtros en URL, totales, periodo/cobertura (UI-01..03).
7. Detalle, ruta, menú, i18n es/en/pt y specs (UI-04, 05; AC-10).
8. Docs (design-system, módulos implementados) y verificación completa (suite backend, lint, `i18n:check`, build, Karma acotado).

## Database / migrations
`accounting/0002_entry`: solo `CreateModel` (con `CheckConstraint`, `UniqueConstraint`, índices). No se edita `0001`.

## Risks
- `IntegrityError` en transacción externa (mitigado con savepoint; test dedicado).
- Totales parciales (mitigado: agregación SQL y test con >1 página).
- Concurrencia en tests sobre PostgreSQL (se sigue el patrón existente de `test_concurrency.py`).

## New dependencies
Ninguna.

## Changelog
_(v1)_
