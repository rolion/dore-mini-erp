# PLAN-2026-11-17-asientos-manuales-navegacion-contable (v1)

**Task:** TASK-asientos-manuales-navegacion-contable · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-asientos-manuales-navegacion-contable-pantallas · ADR: ninguno (contrato del motor = CONT-02)

## Objective
Exponer el motor de asientos (CONT-02) por API y UI: registrar asientos manuales cuadrados, listarlos con paginación estable y filtros, consultarlos y revertirlos, y simplificar la navegación contable a Cuentas, Movimientos, Saldos y Configuración.

## Context
Ver TASK. Base: rama `accounting`. Decisiones de la persona: pantallas existentes conservadas sin submenú; Saldos «Próximamente»; Clasificaciones = las seis contables.

# Specification

## Domain context
Bounded context `accounting` (agregado `JournalEntry`). Sin otros contextos: el enlace a origen solo consulta qué módulos están habilitados (`modularity` gate, como el libro anterior).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Asiento / Movimiento | `JournalEntry` confirmado con ≥2 líneas | `domain/journal.py`; «Movimientos» es el nombre en el menú |
| Origen | Manual (sin referencia) o Automático (`origin_kind`+`origin_id`) | `domain/journal.py:15-17` |
| Diferencia | Σ Debe − Σ Haber del formulario | tarjeta CONT-11 |
| Entradas | Libro anterior de una cuenta por fila (se conserva) | `EntryModel` |

## Current behavior
Motor sin API ni UI (`services.py`); lista, ruta y detalle solo del libro anterior (`api/urls.py:54-55`); menú con 3 ítems (`routes.json:308-352`).

## Expected behavior
1. API de asientos bajo `journal-entries/` (lista, alta manual, detalle, reversión); el libro anterior `entries/` no cambia.
2. Alta manual: fecha y descripción obligatorias, líneas Cuenta/Debe/Haber; valida en servidor lo mismo que el formulario; todo o nada (cabecera y líneas en una transacción).
3. Lista de Movimientos paginada y estable, con filtros fecha desde/hasta, cuenta y origen, aislada por empresa.
4. Detalle con líneas (código y nombre de cuenta), origen, usuario, período y reversión vinculada; sin edición ni borrado en ninguna capa.
5. Reversión con fecha y motivo vía `reverse_journal_entry`.
6. Menú con cuatro submenús; Cuentas y Configuración (Clasificaciones, Períodos fiscales) como pantallas propias; Saldos «Próximamente»; configuración heredada y Entradas/Regularizar accesibles por URL y enlaces.

## Domain rules / invariants
- INV-01 (existente) Σ Debe = Σ Haber > 0, ≥2 cuentas distintas, una sola cara por línea, ≤2 decimales, sin `float` (`domain/journal.py`).
- INV-02 (existente) Confirmado inmutable; corrección = reversión única, completa, no revertible (`reverse`).
- INV-03 (existente) Cuentas de la empresa, activas, con código y clasificación habilitada, misma moneda; fecha en período abierto.
- INV-04 (nueva) Orden de lista total: `accounting_date desc, created_at desc, id desc`; la paginación no repite ni omite filas aunque coincidan fechas.
- INV-05 (nueva) Todo acceso (lista, detalle, reversión, filtro por cuenta) se limita a la empresa de la sesión; una cuenta o asiento ajeno → 404/400 sin revelar existencia.
- INV-06 (nueva) El alta manual nunca recibe origen: el servidor ignora/rechaza `origin_*` del cliente (los automáticos los crean los módulos).

## Acceptance criteria
- AC-01 Registrar servicio 500: Caja Debe 200, Banco Debe 300, Ingresos servicios Haber 500 → 201 con total 500.00.
- AC-02 Diferencia 0 permite confirmar; con diferencia 1 la API responde 400 (`lines`) y **no persiste** cabecera ni líneas; el botón del formulario está deshabilitado.
- AC-03 Con fechas contables iguales, recorrer todas las páginas devuelve cada asiento una vez en orden `accounting_date, created_at, id` descendentes; los filtros (fechas, cuenta, origen) y la página se conservan en la URL y al volver del detalle.
- AC-04 Otra empresa no ve el asiento (lista vacía, detalle 404, reversión 404) ni puede filtrar por cuentas ajenas (400).
- AC-05 Detalle muestra líneas con código y nombre, origen, usuario, período; para automático: origen con enlace si `origin.available`, sin ninguna acción de edición; para revertido/reversión: enlace al vinculado.
- AC-06 No existen rutas PUT/PATCH/DELETE de asientos (405).
- AC-07 Reversión con fecha y motivo crea el contra-asiento vinculado; repetir devuelve el existente; reversión de una reversión → 400; fecha en período cerrado → 400 con mensaje; el diálogo exige motivo y fecha.
- AC-08 Formulario: empieza con dos filas, permite agregar/quitar (mínimo dos), muestra Total Debe, Total Haber y Diferencia y bloquea «Confirmar» mientras haya Diferencia ≠ 0 o validaciones pendientes.
- AC-09 Menú Contabilidad = Cuentas, Movimientos, Saldos, Configuración; Configuración = pestañas Clasificaciones y Períodos fiscales; Métodos de pago, Egresos, Corte y cobertura, Entradas y Regularizar siguen operativos por URL con enlaces visibles.
- AC-10 Todo texto visible usa claves i18n es/en/pt idénticas; `npm run i18n:check` pasa.

## Edge cases / Error cases
- Importes con más de 2 decimales, negativos, ambos lados en una línea o `float` JSON no entero-seguro → 400 por línea.
- Una sola cuenta repetida, línea sin cuenta, cuenta inactiva/sin clasificar/de otra empresa o moneda mezclada → 400 en `lines`.
- Fecha sin período o en período cerrado → 400 en `accounting_date`.
- Filtro desconocido (`source` inválido, `date_from > date_to`) → 400, nunca lista vacía silenciosa.
- Doble clic en «Confirmar»: el botón se deshabilita al enviar (riesgo residual documentado: sin origen no hay idempotencia).
- Lista vacía; detalle con id inexistente → 404 con pantalla de error.

## Authorization / permissions
Mismas reglas que el resto de Contabilidad: usuario autenticado de la empresa con módulo `accounting` habilitado (`CompanyModulePermission`, `required_modules = ('accounting',)`); el menú es `adminOnly`. Sin permisos nuevos. El frontend no es la barrera.

## API contract
- API-01 `GET /api/accounting/journal-entries/?date_from&date_to&account_id&source=MANUAL|AUTOMATIC&origin_kind&page&page_size` → `{count,next,previous,results[]}`; ítem: `id, accounting_date, description, source, origin{kind,available}|null, currency, total, created_by_name, created_at, is_reversal, reversed_by_id`. `page_size` ≤ 100.
- API-02 `POST /api/accounting/journal-entries/` `{accounting_date, description, lines:[{account_id, debit, credit, memo?}]}` → 201 con el detalle; importes como cadenas decimales; 400 `{lines:[...], accounting_date:[...], description:[...]}`.
- API-03 `GET /api/accounting/journal-entries/<id>/` → detalle: cabecera + `period{id,name}` + `lines[{position, account{id,code,name}, debit, credit, memo}]` + `origin{kind, id, available}` + `reverses_id`, `reversed_by_id`, `reversal_reason` + `can_reverse` (false si es reversión o ya revertido).
- API-04 `POST /api/accounting/journal-entries/<id>/reverse/` `{reversal_date, reason}` → 201 (creado) o 200 (ya existía) con el detalle de la reversión.
- Compatibilidad: `entries/` y `regularization/` sin cambios.

## UI behavior
UI-01 Menú y rutas (`/accounting/accounts`, `/journal`, `/journal/new`, `/journal/:id`, `/balances`, `/settings`, `/settings/legacy`). UI-02 Lista según plantilla «Lista de solo lectura con filtros». UI-03 Formulario con totales (variante de un solo paso). UI-04 Detalle con bloque Reversión. UI-05 Diálogo de reversión con motivo. UI-06 Cuentas, Configuración y Saldos. Detalle completo y estados en el DDR.

## Non-functional requirements
Consultas por `company_id`; lista sin N+1 (prefetch de líneas, `select_related`); filtro por cuenta con `EXISTS` sobre líneas con índice `(company_id, account)`.

## Out of scope
Saldos reales (CONT-04/05), configuración de automatismos por módulo (CONT-12), migración de llamantes y del libro anterior (CONT-13, VEN-01…), edición de asientos, conversión de divisas, adjuntos, plantillas de asientos, idempotencia de asientos manuales.

## Open questions
- Vocabulario de `origin_kind` de los módulos: hasta definirse, el enlace usa `ORIGIN_MODULES` existente y los tipos desconocidos se muestran como texto.

# Test Specification

## Unit tests
- Frontend: cálculo de totales/diferencia (enteros), reglas de habilitación de «Confirmar», normalización de filtros ↔ URL, mapeo de origen a enlace.
## Integration tests
- Backend (`test_journal_api.py`): AC-01, AC-02 (sin escrituras parciales: contar filas), AC-03 (≥ 3 asientos con misma fecha, recorrer páginas de tamaño 2), AC-04 (dos empresas), AC-05 (detalle manual/automático/revertido), AC-06 (405), AC-07 (idempotencia, reversión de reversión, período cerrado), filtros inválidos, permiso sin módulo/ sin sesión.
- Frontend (specs de componentes con `provideTestTranslations()`): lista (filtros, vacío, error), formulario (dos filas, agregar/quitar, bloqueo), detalle (reversión, origen con/sin enlace), diálogo (exige motivo/fecha), menú (`sidebar-menu.spec.ts` actualizado), Configuración (dos pestañas).
## E2E
**NO** — el flujo se cubre con pruebas de API y de componentes; no se instala Playwright.
## Regression tests
Suite de `accounting` completa (libro anterior, regularización, períodos) y `i18n:check`, `lint`, `build`.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-02 | `test_journal_api` + spec del formulario |
| AC-03 | `test_journal_api` (paginación) + spec de la lista (URL/filtros) |
| AC-04 | `test_journal_api` (dos empresas) |
| AC-05, AC-06 | `test_journal_api` + spec del detalle |
| AC-07 | `test_journal_api` + spec del diálogo |
| AC-08 | spec del formulario (funciones puras y componente) |
| AC-09 | `sidebar-menu.spec.ts`, specs de Configuración/Cuentas/Saldos |
| AC-10 | prueba de claves i18n + `npm run i18n:check` |

# Implementation Plan

## Architecture considerations
Seguir `domain → application → infrastructure → api`. Lectura (lista/detalle) por repositorio y caso de uso de aplicación sin Django; escritura por `post_journal_entry`/`reverse_journal_entry` dentro de `transaction.atomic` en la vista (como `_run`). El orden y la paginación viven en el queryset del repositorio, que ya declara el orden total.

## Proposed solution
Añadir `list` al repositorio de asientos (filtros fecha, cuenta con `EXISTS`, origen), casos de uso `ListJournalEntries`/`GetJournalEntry`, serializadores de forma/tipos (importes `DecimalField` sin float; el dominio decide el negocio), cuatro vistas con `required_modules`; en el frontend, `features/accounting/pages/journal-*` y servicio `journal-api.service.ts`, reorganizando rutas y menú.

## Files/components affected
- **Backend:** `infrastructure/django/repositories.py` (list), `application/journal_queries.py` (nuevo), `services.py` (DTO/consulta de lista si hace falta), `api/serializers.py`, `api/views.py`, `api/urls.py`, tests `test_journal_api.py`, `test_journal_listing.py`.
- **Frontend:** `app.routes.ts`, `assets/data/routes.json`, `assets/i18n/{es,en,pt}.json`, `features/accounting/{models/journal.ts, services/journal-api.service.ts, services/journal-filters-state.ts, pages/{journal-list, journal-form, journal-detail, accounts, balances, settings(legacy)}, components/journal-reverse-dialog}`, `accounting-settings` (recortado a 2 pestañas) y heredada, specs.
- **Docs:** `design-system.md` §6 (submenú de Contabilidad), este TASK/PLAN/DDR.

## Implementation steps
1. Repositorio `DjangoJournalRepository.list(filters)` + prueba de orden/filtros/aislamiento (INV-04, INV-05, AC-03, AC-04).
2. Casos de uso de lectura y serializadores (formas API-01/03, `origin.available`, `can_reverse`).
3. Vistas y rutas API-01..04; alta con `transaction.atomic`, rechazo de `origin_*`; mapeo de excepciones (400/404) (AC-01, AC-02, AC-06, AC-07, INV-06).
4. Pruebas de integración de API (AC-01..07).
5. Frontend modelos + servicio + estado de filtros en memoria.
6. Lista de Movimientos (UI-02) y detalle con bloque Reversión (UI-04) (AC-03, AC-05).
7. Formulario con totales y reglas de bloqueo (UI-03) (AC-02, AC-08) y diálogo de reversión (UI-05) (AC-07).
8. Navegación: `routes.json`, rutas, Cuentas, Configuración de dos pestañas, pantalla heredada, Saldos «Próximamente» (UI-01, UI-06) (AC-09).
9. i18n es/en/pt, `i18n:check`, specs, `lint`, `build`; actualizar `design-system.md` §6 (AC-10).

## Database / migrations
Sin migración. Solo lecturas nuevas sobre `accounting_journal_*` y su índice `(company_id, accounting_date)`.

## Risks
- Doble envío del formulario manual → asientos duplicados (mitigación UI; sin idempotencia en manuales; fuera de alcance).
- Reorganizar rutas puede romper enlaces de otras pantallas a `/accounting/settings` o `/entries`: buscar y conservar sus destinos.
- Filtro por cuenta puede ser lento con muchos asientos: `EXISTS` con índice; medir con datos de prueba.

## New dependencies
Ninguna.
