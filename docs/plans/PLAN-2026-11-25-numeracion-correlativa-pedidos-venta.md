# PLAN-2026-11-25-numeracion-correlativa-pedidos-venta (v2)

**Task:** TASK-numeracion-correlativa-pedidos-venta · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-numeracion-correlativa-pedidos-venta-codigo-y-bloqueo · ADR-numeracion-correlativa-pedidos-venta-contador-por-periodo

## Objective
Dar a cada pedido de venta confirmado un número correlativo `NV-000001` que se reinicia por período fiscal de contabilidad, se asigna al confirmar, no se reutiliza (los cancelados lo conservan) y nunca se duplica bajo concurrencia.

## Context
Resumen en `docs/tasks/TASK-numeracion-correlativa-pedidos-venta.md`. Compras (`NC-xxxxxx`) queda fuera: otra task.

# Specification

## Domain context
Bounded context **Sales**. Relacionado: **Accounting** (solo lectura/bloqueo del período vía su fachada pública), **Data import** (importación de ventas confirma pedidos), **Customers** (historial muestra `code`).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Confirmar | `NEW → IN_PREPARATION` (`start_preparation`) | `sales/domain/order.py:336` |
| Período fiscal | Rango inclusivo de fechas OPEN/CLOSED de la empresa | `accounting/infrastructure/django/models.py:170` |
| Número de pedido | Entero correlativo dentro de (empresa, período fiscal) | esta task |
| Código | `NV-` + número a 6 dígitos; etiqueta provisional `P-XXXXXXXX` si no tiene número | esta task |

## Current behavior
`code` = `'P-' + 8 hex del UUID` (`sales/domain/order.py:25-27`), no persistido. Confirmar no consulta Contabilidad (`sales/application/commands.py:176-185`, `placement.py:61`).

## Expected behavior
Al confirmar, el pedido recibe `(período fiscal, número)` del período que contiene su `order_date`, dentro de la misma transacción. El API devuelve `code = NV-000001`, `number` y `fiscal_period`. Los pedidos sin confirmar (NEW) muestran la etiqueta provisional.

## Domain rules / invariants
- **INV-01 (nueva)** Número único por (empresa, período): lo garantiza una restricción única en base de datos y el bloqueo del contador.
- **INV-02 (nueva)** Correlativo sin huecos por fallo: número y confirmación se escriben en la misma transacción; si algo falla, ambos se revierten.
- **INV-03 (nueva)** Inmutable: un pedido numerado nunca cambia de número ni de período; cancelar o devolver no lo borra.
- **INV-04 (nueva)** El período lo define `order_date`, no la fecha de confirmación.
- **INV-05 (nueva)** Cada empresa tiene su propia serie; los contadores de dos empresas o dos períodos son independientes.
- **INV-06 (existente)** Confirmar exige al menos un ítem y estado NEW.

## Acceptance criteria
- **AC-01** El primer pedido confirmado de un período recibe 000001 y el siguiente 000002; en otro período la serie empieza de nuevo en 000001; otra empresa tiene su propia serie.
- **AC-02** Crear un pedido NEW no consume número; solo confirmar lo hace.
- **AC-03** Un pedido cancelado después de confirmarse conserva su número y ese número no se vuelve a asignar.
- **AC-04** El período se determina por `order_date`: un pedido con fecha de 2026 confirmado en 2027 recibe número del período de 2026 si esa fecha cae en él.
- **AC-05** Si `order_date` no cae en ningún período fiscal, confirmar responde 409 `fiscal_period_missing` y el pedido sigue NEW (sin número y sin consumir contador).
- **AC-06** Si el período está cerrado, confirmar responde 409 `fiscal_period_closed`; el pedido sigue NEW.
- **AC-07** Carrera: dos (o más) confirmaciones simultáneas del mismo período reciben números distintos y consecutivos, sin duplicados ni huecos.
- **AC-08** Carrera con cierre: confirmar y cerrar el período a la vez nunca numera dentro de un período ya cerrado.
- **AC-09** Si la confirmación falla después de numerar, el contador no avanza (el siguiente pedido recibe ese número).
- **AC-10** `PlaceOrder` (creación + confirmación en un paso) y la importación de ventas numeran igual; en importación, una fecha sin período/cerrada rechaza solo esa fila con el mismo código.
- **AC-11** El API de lista, detalle, vista previa de devolución, historial de compras del cliente y asientos automáticos usan el nuevo código; la descripción de la entrega incluye el período.
- **AC-12** (v2) Migración de datos: pedidos ya confirmados quedan numerados por empresa y período en orden `created_at, id` (`0007`); los cancelados heredados con fecha dentro de un período reciben los siguientes números de su período (`0008`, aunque quizá nunca se confirmaron); el contador queda en el máximo; los NEW y los de fecha fuera de todo período quedan sin número; ambas migraciones se pueden repetir sin duplicar.
- **AC-13** UI: lista y detalle muestran el código y, si hay número, el período; el 409 de período se explica en `alert-warning` sin perder lo escrito; textos en es/en/pt.

## Edge cases / Error cases
- **EDGE-01** Confirmar un pedido ya confirmado: sigue siendo `invalid_transition`; el número no cambia.
- **EDGE-02** Contabilidad deshabilitada y sin períodos: 409 `fiscal_period_missing` (decisión del usuario).
- **EDGE-03** Renombrar el período después: el pedido conserva el nombre con que se numeró (instantánea).
- **EDGE-04** Más de 999 999 pedidos en un período: el número sigue creciendo y el formato deja de rellenar (`NV-1000000`); la restricción de unicidad no se rompe.
- **EDGE-05** Reabrir un período cerrado: vuelve a permitir confirmar y continúa la serie.

## Authorization / permissions
Sin cambios: mismos permisos de la API de pedidos; la empresa sale del usuario autenticado (`shared/tenancy.py`).

## API contract
- **API-01** Los serializers de pedido (lista y detalle) añaden `number` (entero o `null`) y `fiscal_period` (`{id, name}` o `null`). `code` cambia de valor pero conserva su tipo (texto): compatible hacia atrás para quien solo lo muestra.
- **API-02** Los endpoints que confirman (iniciar preparación y crear pedido confirmado) pueden responder 409 con `{code: 'fiscal_period_missing' | 'fiscal_period_closed', detail}`; usan el mismo envoltorio `RuleConflict` de reglas de negocio (`sales/api/views.py:70,101`).
- **API-03** La vista previa de devolución devuelve `order_code` con el nuevo código.

## UI behavior
- **UI-01** Lista (tabla y tarjetas compactas): código en el enlace; «Período {nombre}» en `small.text-body-secondary` si hay número (plantilla Lista, DDR).
- **UI-02** Detalle: `h4` «Pedido {code}» y línea «Período fiscal: {nombre}» bajo el título si hay número.
- **UI-03** Bloqueo al confirmar en `order-create` y en detalle: `alert alert-warning` con el motivo y enlace a Períodos fiscales solo si Contabilidad está habilitada; el borrador no se pierde.
- **UI-04** Diálogos y historial de compras del cliente usan `code` tal cual (sin cambios de estructura).

## Non-functional requirements
Sin dependencias nuevas. La espera por el bloqueo del período es de milisegundos. Dinero no interviene. Todo lo que se agrega al API respeta el aislamiento por `company_id`.

## Out of scope
Compras (`NC-xxxxxx`); extraer el contador a `shared/`; búsqueda de pedidos por número (hoy no existe búsqueda por código); renumerar o reasignar números; numeración de cotizaciones/cobros; cambiar la etiqueta de pedidos cancelados antiguos.

## Open questions
- Ninguna que bloquee. Seguimiento: cuando se haga Compras, evaluar extraer el contador (ADR, decisión 7).

# Test Specification

## Unit tests
- Dominio: `start_preparation(number)` asigna `OrderNumber` una sola vez; `code` con y sin número (`NV-000001`, formato más allá de 6 dígitos); cancelar no borra el número (INV-03, AC-03, EDGE-04).
- Aplicación con fakes: `StartOrderPreparation` y `PlaceOrder` invocan el puerto de numeración; error de período propaga `OrderRuleViolation` sin cambiar el pedido (AC-05, AC-06, AC-10).
## Integration tests (PostgreSQL)
- Adaptador + repositorio: serie por empresa/período, independencia entre períodos y empresas, `order_date` decide período, nombre en instantánea, descripción del asiento (AC-01, AC-02, AC-04, AC-11, INV-05, EDGE-03).
- Restricción única de base de datos rechaza un duplicado (INV-01).
- Rollback: forzar fallo tras numerar y comprobar contador intacto (AC-09, INV-02).
- API: 409 con ambos códigos, cuerpo con `number`/`fiscal_period`, vista previa de devolución (AC-05, AC-06, AC-11, API-01..03).
- Importación de ventas: fila rechazada con el código del período (AC-10).
- Migraciones de datos `0007` y `0008` con datos sembrados antes de migrar: empresas, períodos (abierto/cerrado), fuera de período, cancelados (los numera `0008`), orden `created_at`, repetición idempotente (AC-12).
## Concurrency tests (obligatorios, `TransactionTestCase` + hilos, PostgreSQL)
- N≥8 confirmaciones simultáneas de pedidos distintos del mismo período → conjunto exacto `{1..N}`, sin duplicados ni huecos (AC-07, INV-01).
- Confirmaciones simultáneas en dos períodos y en dos empresas → cada serie independiente y completa (INV-05).
- Confirmar vs. cerrar período simultáneos: si el cierre gana, la confirmación recibe `fiscal_period_closed`; si la confirmación gana, queda numerada y luego se cierra; nunca numerada en período ya cerrado (AC-08).
- El mismo pedido confirmado dos veces a la vez: una confirmación gana, la otra `invalid_transition`; un solo número consumido (EDGE-01).
## E2E
**NO** — el flujo no es crítico de punta a punta distinto de los existentes; lo cubren pruebas de API y de componentes. No se instala Playwright.
## Frontend (Karma)
Pruebas de componentes de lista, detalle y `order-create` con `provideTestTranslations()`: período visible solo con número, `alert-warning` en 409, enlace condicionado por módulo; `npm run i18n:check` y la prueba de claves es/en/pt (AC-13, UI-01..04).
## Regression tests
Ajustar pruebas que confirmaban pedidos sin período (≥16 archivos) con un fixture común; la suite completa de `sales`, `accounting`, `data_import`, `reporting`, `customers` y `modularity` debe seguir en verde.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Integración (serie por empresa/período) + concurrencia (dos períodos/empresas) |
| AC-02 | Integración: crear NEW no avanza contador |
| AC-03 | Dominio + integración: cancelar conserva y no reutiliza |
| AC-04 | Integración: `order_date` vs. fecha de confirmación |
| AC-05 | Aplicación (fake) + API 409 + integración (contador intacto) |
| AC-06 | Aplicación (fake) + API 409 |
| AC-07 | Concurrencia: N confirmaciones simultáneas |
| AC-08 | Concurrencia: confirmar vs. cerrar |
| AC-09 | Integración: rollback tras numerar |
| AC-10 | Aplicación `PlaceOrder` + importación de ventas |
| AC-11 | API (lista/detalle/vista previa), integración (descripción del asiento), prueba del historial de clientes |
| AC-12 | Integración de migración de datos |
| AC-13 | Karma de componentes + i18n check |

# Implementation Plan

## Architecture considerations
Ver ADR. Numerar en un puerto de aplicación implementado con la fachada pública de `accounting`; el dominio solo recibe un `OrderNumber`. No se importa infraestructura de otro módulo.

## Proposed solution
Columnas `fiscal_period_id`, `fiscal_period_name`, `number` en el pedido; tabla de contador por (empresa, período); `lock_open_period` + `select_for_update` para serializar; `code` calculado del número; migración de datos para el histórico.

## Files/components affected
- **Backend dominio:** `sales/domain/order.py` (`OrderNumber`, `start_preparation(number)`, `code`), errores en `sales/domain/errors.py` o equivalente.
- **Backend aplicación:** `sales/application/ports.py` (puerto `OrderNumbering`), `commands.py` (`StartOrderPreparation`), `placement.py` (`PlaceOrder`), `sales/services.py` (composición y `ImportedSale.code`).
- **Backend infraestructura:** `sales/infrastructure/django/models.py` (campos + `OrderNumberCounterModel`), `mappers.py`, `repositories.py`, `sales/infrastructure/adapters.py` (adaptador de numeración y descripción del asiento, línea 313).
- **API:** `sales/api/serializers.py` (`code`, `number`, `fiscal_period`), `sales/api/views.py` (409).
- **Migraciones:** `sales/migrations/0006_order_number_fields.py` (esquema), `0007_backfill_order_numbers.py` y `0008_backfill_cancelled_order_numbers.py` (datos).
- **Frontend:** `features/sales/models/order.ts`, `services/orders-api.service.ts`, `pages/order-list`, `pages/order-detail`, `pages/order-create`, `assets/i18n/{es,en,pt}.json`; revisar `features/customers` (solo `code`).
- **Tests:** `sales/tests/` (fakes, dominio, aplicación, API, repositorio, concurrencia nueva), fixture de período compartido para tests, ajustes en `accounting/tests`, `reporting/tests`, `modularity/tests`, `data_import` y specs de frontend que esperan `P-`.
- **Docs:** `docs/architecture/ddd.md` solo si menciona el código del pedido (revisar); nota en el TASK.

## Implementation steps
1. **Dominio** (INV-01..04, AC-03): `OrderNumber`, `start_preparation(number)`, `code`; pruebas de dominio.
2. **Puerto y casos de uso** (AC-02, AC-05, AC-06, AC-10): puerto `OrderNumbering`, errores `fiscal_period_missing`/`fiscal_period_closed`, cableado en `StartOrderPreparation` y `PlaceOrder` (numerar dentro de la transacción, justo antes de `start_preparation`); fake en `sales/tests/fakes.py`.
3. **Infraestructura y migración de esquema** (INV-01, INV-05): campos, restricción única parcial, `OrderNumberCounterModel`, mapper y repositorio; `0006` con `makemigrations`.
4. **Adaptador** (AC-01, AC-04, AC-07, AC-08, AC-09): `lock_open_period` + contador bloqueado + instantánea del nombre; traducir excepciones de accounting a errores de `sales`; descripción del asiento con período (AC-11).
5. **API** (API-01..03, AC-11): serializers y 409; vista previa de devolución.
6. **Migración de datos `0007`** (AC-12): numerar histórico; idempotente; dependencia de la migración de `accounting` que crea el período (verificar el nombre al implementar); `last_number` del contador.
7. **Pruebas:** integración, API, importación, migración y, **obligatoriamente**, las de concurrencia (con un ayudante local basado en `_run_together`, o extraído a `shared/tests` si evita duplicar); fixture común de período abierto para las suites existentes.
8. **Frontend** (AC-13, UI-01..04): modelo, mapeo, lista, detalle, `order-create`, i18n es/en/pt, specs; `npm run i18n:check`, `npm test`, `npm run lint`.
9. **Lint y suite completa:** `ruff` y `flake8` sobre `.py` cambiados; `python manage.py test` con PostgreSQL.

## Database / migrations
Dos migraciones nuevas, nunca editar las aplicadas: `0006` aditiva (columnas nulas, tabla de contador, restricción única parcial) y `0007` de datos (reversible como no-op). Probar contra una base con pedidos en varios períodos y fuera de período. Backup previo lo hace el despliegue.

## Risks
- Bloquear confirmación sin período afecta a empresas sin Contabilidad/sin período y a importaciones con fechas fuera de período (decisión del usuario; mitigado con mensaje claro y enlace).
- Volumen de pruebas heredadas por ajustar (≥16 archivos); riesgo de olvidar una suite: ejecutar la suite completa antes de publicar.
- La migración `0007` depende de una migración de `accounting`; si cambia el esquema de períodos, fallaría: solo lectura de tres columnas estables.
- Prueba de concurrencia dependiente de PostgreSQL (no corre en SQLite): marcar claramente y ejecutar en CI con PostgreSQL.

## New dependencies
Ninguna.

## Changelog
- **v2** (2026-11-25): [Specification] AC-12 cambia tras aprobación explícita del usuario en el chat: los pedidos CANCELLED heredados también se numeran (migración `0008`, a continuación de la serie ya asignada por `0007`), en vez de quedar con la etiqueta provisional. Origen: el usuario vio en la lista pedidos cancelados antiguos sin `NV-`.
