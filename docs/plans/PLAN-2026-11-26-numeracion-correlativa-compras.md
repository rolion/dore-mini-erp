# PLAN-2026-11-26-numeracion-correlativa-compras (v1)

**Task:** TASK-numeracion-correlativa-compras · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-numeracion-correlativa-compras-codigo-y-bloqueo · ADR-numeracion-correlativa-compras-contador-por-periodo

## Objective
Dar a cada compra confirmada un número correlativo `NC-000001` que se reinicia por período fiscal de contabilidad (según `purchase_date`), se asigna al confirmar, se conserva al cancelar, no se reutiliza y nunca se duplica bajo concurrencia; con las mismas reglas de bloqueo que la numeración de ventas.

## Context
Resumen en `docs/tasks/TASK-numeracion-correlativa-compras.md`. Gemela de TASK-numeracion-correlativa-pedidos-venta (PR #124, mergeado): se reutilizan sus decisiones.

# Specification

## Domain context
Bounded context **Purchases**. Relacionado: **Accounting** (fachada pública: bloqueo/lectura del período), **Data import** (la importación de ventas confirma una «compra inferida»).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Confirmar | `draft → confirmed` (`Purchase.confirm`) | `purchases/domain/purchase.py:361` |
| Período fiscal | Rango de fechas OPEN/CLOSED de la empresa | `accounting/infrastructure/django/models.py` |
| Número de compra | Entero correlativo dentro de (empresa, período) en la serie de compras | esta task |
| Código | `NC-` + número a 6 dígitos; etiqueta provisional `COM-XXXXXXXX` si no tiene número | esta task |

## Current behavior
`Purchase.reference` = `COM-` + 8 hex del id (`domain/purchase.py:325-327`), repetido en `purchase_repository.py:44`; confirmar no consulta Contabilidad (`application/purchase_commands.py:121-135`).

## Expected behavior
Al confirmar, la compra recibe `(período fiscal, número)` del período que contiene su `purchase_date`, dentro de la misma transacción. El API devuelve `reference = NC-000001`, `number` y `fiscal_period`. Los borradores (y heredados sin número) muestran la etiqueta provisional.

## Domain rules / invariants
- **INV-01 (nueva)** Número único por (empresa, período): restricción única en base de datos + bloqueo del contador.
- **INV-02 (nueva)** Sin huecos por fallo: número y confirmación se escriben en la misma transacción.
- **INV-03 (nueva)** Inmutable: una compra numerada nunca cambia de número ni de período; cancelar no lo borra.
- **INV-04 (nueva)** El período lo define `purchase_date` (editable solo en borrador), no la fecha de confirmación.
- **INV-05 (nueva)** Cada empresa y cada período tienen su serie; la de compras es independiente de la de ventas.
- **INV-06 (existente)** Confirmar exige borrador, proveedor activo y ≥1 ítem; confirmar una ya confirmada es idempotente.

## Acceptance criteria
- **AC-01** La primera compra confirmada de un período recibe 000001, la siguiente 000002; en otro período la serie empieza en 000001; otra empresa tiene su propia serie; la serie de compras es independiente de la de ventas.
- **AC-02** Crear o editar un borrador no consume número; solo confirmar.
- **AC-03** Una compra confirmada y luego cancelada conserva su número y este no se reasigna; una cancelada siendo borrador nunca tuvo número.
- **AC-04** El período se determina por `purchase_date`, no por la fecha de confirmación.
- **AC-05** Sin período fiscal para `purchase_date`, confirmar responde 409 `fiscal_period_missing`; la compra sigue en borrador, sin número y sin consumir contador.
- **AC-06** Período cerrado: 409 `fiscal_period_closed` con el nombre del período; la compra sigue en borrador.
- **AC-07** Carrera: confirmaciones simultáneas del mismo período reciben números distintos y consecutivos, sin duplicados ni huecos.
- **AC-08** Carrera con cierre: confirmar y cerrar el período a la vez nunca numera dentro de un período ya cerrado.
- **AC-09** Si la confirmación falla después de numerar, el contador no avanza.
- **AC-10** La importación de ventas (compra inferida) numera igual; con fecha sin período o cerrada, esa fila se rechaza con el mismo código.
- **AC-11** Lista, detalle, recepciones y descripciones de asientos de recepción, pago y reversión usan el nuevo código (con período en las descripciones); la búsqueda de la lista encuentra por `NC-000012` o `12`, y por prefijo de id/`com-…` en borradores y heredados.
- **AC-12** Migración de datos: las compras con `confirmed_at` (confirmadas y canceladas que se confirmaron) quedan numeradas por empresa y período en orden `confirmed_at, created_at, id`; contador en el máximo; borradores, canceladas sin confirmar y fechas fuera de período quedan sin número; repetible sin duplicar.
- **AC-13** UI: lista y detalle muestran el código y, si hay número, el período; el 409 de período se explica en `alert-warning` (con el nombre del período cerrado) sin perder lo escrito; textos en es/en/pt.

## Edge cases / Error cases
- **EDGE-01** Confirmar una compra ya confirmada: idempotente; no consume número y conserva el que tiene.
- **EDGE-02** Contabilidad deshabilitada y sin períodos: 409 `fiscal_period_missing`.
- **EDGE-03** Renombrar el período después: la compra conserva el nombre con que se numeró.
- **EDGE-04** Más de 999 999 compras en un período: el número sigue creciendo (`NC-1000000`).
- **EDGE-05** Reabrir un período cerrado: vuelve a permitir confirmar y continúa la serie.
- **EDGE-06** Confirmar una cancelada: `invalid_transition` como hoy; sin número nuevo.

## Authorization / permissions
Sin cambios: mismos permisos de la API de compras; la empresa sale del usuario autenticado.

## API contract
- **API-01** Lista y detalle de compras añaden `number` (entero o `null`) y `fiscal_period` (`{id, name}` o `null`); `reference` cambia de valor y conserva su tipo (texto).
- **API-02** La confirmación puede responder 409 `{code: 'fiscal_period_missing' | 'fiscal_period_closed', detail, period?}` (mismo contrato que ventas).
- **API-03** `order`-equivalentes en recepciones (`purchase.reference`) devuelven el nuevo código.

## UI behavior
- **UI-01** Lista (tabla y tarjetas): referencia en el enlace; «Período {nombre}» en `small.text-body-secondary` si hay número.
- **UI-02** Detalle: título «Compra {referencia}»; fila «Período fiscal» en el Resumen solo si hay número.
- **UI-03** Bloqueo al confirmar: `app-fiscal-period-alert` (shared) con enlace a Contabilidad solo si está habilitada; reemplaza el toast para estos dos códigos.
- **UI-04** Recepciones y pagos usan `reference` sin cambios de estructura.

## Non-functional requirements
Sin dependencias nuevas. Espera por el bloqueo del período de milisegundos. Aislamiento por `company_id`. Dinero no interviene.

## Out of scope
Inventario y Contabilidad siguen mostrando UUIDs en «Origen»/documento de origen (decisión del usuario); contador compartido en `shared/` (ADR decisión 8); numeración de recepciones y pagos; renumerar compras; búsqueda por otros campos.

## Open questions
- Ninguna que bloquee.

# Test Specification

## Unit tests
- Dominio: `PurchaseNumber.code` (`NC-000001`, `NC-1000000`), `confirm(now, number)` asigna una sola vez, cancelar conserva, `reference` con/sin número, `ensure_confirmable` (borrador, proveedor activo, ítems) (INV-01..06, AC-01, AC-03, EDGE-04).
- Aplicación con fakes: `ConfirmPurchase` numera dentro, es idempotente sobre confirmada, no consume número en confirmaciones inválidas, propaga `PurchaseNumberingRejected` sin guardar (AC-02, AC-05, AC-06, EDGE-01).
## Integration tests (PostgreSQL)
- Adaptador + repositorio: serie por empresa/período, independencia de la serie de ventas, `purchase_date` decide, snapshot del nombre, descripciones de asiento con período (AC-01, AC-04, AC-11, INV-05, EDGE-03).
- Restricciones de base de datos (único y CHECK), rollback tras numerar (INV-01, AC-09).
- API: confirmar numera; 409 con ambos códigos y `period`; lista/detalle/recepción exponen `reference`/`number`/`fiscal_period`; búsqueda por `NC-…` y por número y por prefijo de id (AC-05, AC-06, AC-11, API-01..03).
- Importación de ventas: compra inferida numerada; fila rechazada sin período y con período cerrado, sin compra huérfana (AC-10).
- Migración de datos `0011` con datos sembrados antes de migrar: confirmadas, canceladas confirmadas, borradores, canceladas sin confirmar, fuera de período, empresas, orden `confirmed_at`, repetición (AC-12).
## Concurrency tests (obligatorios, `TransactionTestCase` + hilos, PostgreSQL)
- ≥8 confirmaciones simultáneas del mismo período → `{1..N}` exacto; dos períodos y dos empresas independientes; la misma compra confirmada dos veces a la vez (un número consumido); confirmar vs. cerrar con sincronización determinista (el cierre espera) y confirmar tras cierre firme rechazado sin numerar (AC-07, AC-08, EDGE-01).
- **Mutación:** quitar `lock_open_period`/`select_for_update` debe hacer fallar las pruebas de carrera (se comprueba y se deja constancia en `## Implementación`).
## E2E
**NO** — flujo no distinto de los existentes; lo cubren API y componentes. No se instala Playwright.
## Frontend (Karma)
Componentes de lista, detalle y servicio con `provideTestTranslations()`: período visible solo con número, alerta 409 con nombre del período y enlace condicionado, componente movido a `shared`; `npm run i18n:check` y prueba de claves es/en/pt (AC-13, UI-01..04).
## Regression tests
Ajustar las pruebas que confirman compras sin período (fixture de período abierto reutilizable); suite completa de `purchases`, `sales`, `data_import`, `accounting`, `inventory` y `reporting` en verde.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Integración (serie por empresa/período/serie de ventas) + concurrencia |
| AC-02 | Aplicación (fake) + integración |
| AC-03 | Dominio + integración |
| AC-04 | Integración: `purchase_date` vs. confirmación |
| AC-05 | Aplicación (fake) + API 409 + integración (contador intacto) |
| AC-06 | Aplicación (fake) + API 409 con `period` |
| AC-07 | Concurrencia: N confirmaciones simultáneas |
| AC-08 | Concurrencia determinista confirmar vs. cerrar |
| AC-09 | Integración: rollback tras numerar |
| AC-10 | Importación de ventas (compra inferida) |
| AC-11 | API (lista/detalle/recepción/búsqueda), integración (descripciones de asiento) |
| AC-12 | Integración de la migración `0011` |
| AC-13 | Karma + i18n check |

# Implementation Plan

## Architecture considerations
Ver ADR. Mismo molde que ventas: puerto `PurchaseNumbering`, adaptador sobre la fachada de `accounting`, dominio recibe un `PurchaseNumber`. Sin contador compartido (ADR decisión 8).

## Proposed solution
Columnas y tabla de contador en `purchases`; `lock_open_period` + `select_for_update`; `reference` calculada del número; búsqueda ampliada; migración de histórico; componente de alerta movido a `shared/`.

## Files/components affected
- **Backend dominio:** `purchases/domain/purchase.py` (`PurchaseNumber`, `Purchase.number`, `ensure_confirmable`, `confirm(now, number, ...)`, `reference`), `domain/exceptions.py` (`PurchaseNumberingRejected`), `domain/repositories.py` (`PurchaseSummary` con número y referencia).
- **Aplicación:** `application/ports.py` (puerto), `purchase_commands.py` (`ConfirmPurchase`), `purchases/services.py` (`import_received_purchase`).
- **Infraestructura:** `infrastructure/django/models.py` (campos, restricciones, `PurchaseNumberCounterModel`), `mappers.py`/`purchase_repository.py` (número, referencia, búsqueda), `infrastructure/adapters.py` (adaptador y descripciones de asiento).
- **API:** `api/purchase_serializers.py` (`reference`, `number`, `fiscal_period`), `api/purchase_views.py` (409).
- **Migraciones:** `purchases/migrations/0010_purchase_number_fields.py` (esquema), `0011_backfill_purchase_numbers.py` (datos).
- **Frontend:** `shared/components/fiscal-period-alert/*` (movido desde `features/sales/components`), imports de `features/sales` (detalle y pedido nuevo) y sus specs; `features/purchases` (modelos, servicio, lista, detalle, error 409 con `code`/`period`, fixtures); `assets/i18n/{es,en,pt}.json`.
- **Tests:** `purchases/tests/` (fakes, dominio, aplicación, API, repositorio, carrera, migración), fixture de período abierto compartido (reutilizar `sales/tests/periods.py` o moverlo a un módulo común de tests), ajustes en `data_import`, `accounting` y otras suites que confirmen compras.
- **Docs:** `design-system.md` si lista el componente (ubicación).

## Implementation steps
1. **Dominio** (INV-01..06, AC-03): `PurchaseNumber`, `ensure_confirmable`, `confirm(now, number, ...)`, `reference`; pruebas de dominio.
2. **Puerto, excepción y casos de uso** (AC-02, AC-05, AC-06, EDGE-01): `PurchaseNumbering`, `PurchaseNumberingRejected`, `ConfirmPurchase`, fakes.
3. **Infraestructura + migración de esquema `0010`** (INV-01, INV-05): campos, restricciones, contador, mapper/repositorio, referencia en el resumen, búsqueda ampliada.
4. **Adaptador** (AC-01, AC-04, AC-07..AC-09): `lock_open_period` + contador; instantánea del nombre; descripciones de asiento con período (AC-11).
5. **API** (API-01..03, AC-11): serializers, 409 con `code`/`period`; `import_received_purchase` (AC-10).
6. **Migración de datos `0011`** (AC-12).
7. **Pruebas backend:** integración, API, importación, migración y **concurrencia** con comprobación por mutación; fixture de período para las suites heredadas.
8. **Frontend** (AC-13, UI-01..04): mover el componente a `shared`, actualizar ventas; modelos/servicio/lista/detalle de compras, i18n es/en/pt, specs; `i18n:check`, `ng lint`, Karma, `ng build`.
9. **Lint y suite completa:** `ruff`/`flake8` sobre `.py` cambiados; `python manage.py test` con PostgreSQL.

## Database / migrations
Dos migraciones nuevas, nunca editar las aplicadas: `0010` aditiva y `0011` de datos (reversible como no-op). Probar contra una base con compras en varios períodos, canceladas confirmadas, borradores y fuera de período; el despliegue hace backup previo.

## Risks
- Bloquear confirmación sin período afecta a empresas sin período y a importaciones con fechas fuera de período (decisión del usuario, igual que ventas).
- Mover el componente compartido toca ventas: cubrir con sus specs y la suite de Karma completa.
- Volumen de pruebas heredadas de compras (≥20 archivos); ejecutar la suite completa antes de publicar.
- Pruebas de carrera dependientes de PostgreSQL y de hilos con temporización: marcar claramente y ejecutarlas en CI con PostgreSQL.

## New dependencies
Ninguna.
