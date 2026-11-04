# PLAN-2026-11-04-presentar-aceptar-versionar-proformas (v1)

**Task:** TASK-presentar-aceptar-versionar-proformas · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** [DDR](../design/DDR-presentar-aceptar-versionar-proformas-detalle-decisiones-e-impresion.md) · [ADR](../adr/ADR-presentar-aceptar-versionar-proformas-libro-de-decisiones-y-versionado.md)

## Objective
Permitir registrar, por línea y de forma explícita e inmutable, qué tratamientos acepta o rechaza el paciente en una proforma presentada, derivar estado y totales (propuesto, aceptado, pendiente), conservar decisiones e historial al versionar sin duplicar compromisos, y ofrecer una vista imprimible de datos comerciales, en `quotations` y en `dentistry`.

## Context
Ver el TASK. Extiende PB-COT-001 (PR #52) y las proformas odontológicas (PR #56); apilado sobre `task/TASK-crear-proformas-de-servicios`. La lógica se implementa en cada módulo (duplicación consciente del ADR de odontología). La tarjeta Trello es insumo, esta Specification es la propuesta a implementar.

# Specification

## Domain context
Bounded contexts **Cotizaciones** (`quotations`, proforma genérica) y **Odontología** (`dentistry`, proforma del paciente). Sin nuevas dependencias entre módulos.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Proforma presentada | Versión congelada que se muestra al paciente | PB-COT-001 |
| Decisión | Aceptación o rechazo explícito de una línea; inmutable | Tarjeta |
| Rectificación | Nueva decisión (aceptada ↔ rechazada) con motivo y autor que corrige una anterior sin borrarla | Tarjeta |
| Compromiso | Una línea aceptada; se identifica por su cadena de `origin_line_id` | Tarjeta |
| Línea conservada / reemplazo / adicional | Tipo de línea en una versión nueva: igual a la anterior / cambiada / nueva | Tarjeta |
| Autorizada | Línea aceptada: único trabajo habilitado para ejecución futura | Tarjeta |
| Total propuesto / aceptado / pendiente | Σ de todas las líneas / de las aceptadas / de las sin decidir | Tarjeta |

## Current behavior
Ver el TASK (hechos con `archivo:línea`): las proformas se presentan y versionan sin decisiones; «Total aceptado» es «—»; `new_version()` copia líneas sin vínculo; el repositorio recrea todas las líneas al guardar.

## Expected behavior
Una proforma presentada permite registrar decisiones de una o varias líneas pendientes; el servidor deriva `acceptance_status` y los totales; las decisiones se guardan en un libro inmutable; una versión nueva conserva las decisiones de las líneas sin cambios, marca reemplazos y adicionales y bloquea las aceptadas; existe una vista imprimible con solo datos comerciales. No se ejecuta ni cobra nada.

## Domain rules / invariantes
- INV-01 (nueva) Solo una proforma `presented` admite decisiones; `draft` y `superseded` responden 409.
- INV-02 (nueva) Una línea nace `pending`; el silencio, presentar o crear una versión nunca la acepta. Se decide la línea completa (no hay cantidades parciales).
- INV-03 (nueva) Decidir exige ≥ 1 línea, todas de la proforma y todas `pending`; el lote es todo-o-nada. Aceptar exige `accepted_by_name` (1–120) y `medium` ∈ {`in_person`,`phone`,`message`,`email`,`signed_document`,`other`}; `reference` ≤ 200 y `reason` ≤ 500 son opcionales; en rechazo nombre y medio son opcionales.
- INV-04 (nueva) Las decisiones son un libro append-only; fecha y usuario los fija el servidor. Una decisión nunca se edita ni se borra.
- INV-05 (nueva) Rectificar: solo sobre línea decidida de la proforma `presented` vigente, con `can_rectify(user)`, motivo obligatorio (1–500), entre aceptada ↔ rechazada (nunca de vuelta a pendiente); conserva el registro anterior. Si pasa a aceptada exige nombre y medio.
- INV-06 (nueva) `acceptance_status`: `pending` (ninguna aceptada y alguna sin decidir), `accepted` (todas aceptadas), `rejected` (todas rechazadas), `partially_accepted` (el resto). Totales: propuesto = Σ subtotales; aceptado = Σ subtotales de aceptadas; pendiente = Σ de pendientes; todo en `Decimal` a dos decimales (`ROUND_HALF_UP`).
- INV-07 (nueva) Nueva versión: cada línea copiada lleva `origin_line_id` y `line_kind = carried` con su decisión vigente copiada como registro `carried`. Al guardar el borrador el servidor recalcula el tipo: sin origen → `additional`; con origen y misma cantidad/precio → `carried`; con origen y cantidad/precio distintos → `replacement` y `pending`. Una línea aceptada heredada no se edita ni se elimina en el borrador (409).
- INV-08 (nueva) El total aceptado de un número es el de su versión presentada vigente; al presentar una versión nueva la anterior pasa a `superseded` y queda solo lectura con sus decisiones: el mismo compromiso no se cuenta dos veces.
- INV-09 (nueva) Reintentos: misma `idempotency_key` + mismo payload → 200 con el estado actual y sin escrituras (`replayed: true`); misma clave + otro payload → 409; línea ya decidida con otra clave → 409.
- INV-10 (existente, conservada) Moneda BOB; dinero `Decimal`; presentar congela líneas y precios; estados por métodos del agregado; sin venta, cobro, cita, ejecución ni stock.
- INV-11 (nueva) Guardar un borrador conserva el `id` de las líneas que ya existían (no recrea las decididas).

## Acceptance criteria
- AC-01 Proforma con líneas de 100 y 200 presentada: aceptar la primera y rechazar la segunda (dos lotes) deja propuesto 300, aceptado 100, pendiente 0, `acceptance_status = partially_accepted`, y solo la primera con `authorized = true`.
- AC-02 Decidir varias líneas en un solo envío las registra todas o ninguna; la respuesta incluye el resumen (líneas e importe).
- AC-03 Reintentar la misma confirmación (misma clave) no duplica registros, totales ni estados y devuelve 200 `replayed: true`; la misma clave con otras líneas da 409; decidir de nuevo una línea ya decidida con otra clave da 409.
- AC-04 Una proforma `draft` o `superseded` rechaza decisiones y rectificaciones con 409; presentar o crear versión no cambia ninguna línea a aceptada.
- AC-05 Validaciones: aceptar sin nombre o sin medio válido → 400 por campo; `reference`/`reason` por encima del máximo → 400; línea de otra proforma o de otra empresa → 404/400 sin cambios.
- AC-06 Rectificar una línea con motivo la cambia aceptada ↔ rechazada, el historial conserva ambos registros con autor, fecha y motivo; sin motivo → 400; usuario sin permiso → 403; no se puede volver a `pending`.
- AC-07 `acceptance_status` correcto para: ninguna decisión, todas aceptadas, todas rechazadas, mezcla, y una aceptada con otra sin decidir.
- AC-08 Nueva versión desde una proforma con 100 aceptada y 200 rechazada: el borrador v2 tiene ambas líneas `carried` con sus decisiones y `origin_line_id`; el total aceptado de v2 es 100 (no 200); editar el precio de la rechazada la vuelve `replacement` `pending`; revertir el cambio la restaura `carried` rechazada; agregar una línea nueva es `additional`; editar o quitar la aceptada → 409.
- AC-09 Al presentar v2, v1 pasa a `superseded` en solo lectura con sus decisiones intactas; `allowed_actions` de v1 no incluye `decide`, y la suma de compromisos aceptados del número nunca duplica el de v1.
- AC-10 `GET …/printable/` devuelve solo datos comerciales (número, versión, fecha, vigencia, cliente/paciente, líneas con descripción/pieza/cantidad/precio/subtotal/decisión y fecha, totales, condiciones) y nada de referencia/evidencia, motivos, usuarios, ids internos ni historial; en borrador → 409.
- AC-11 Aislamiento y módulos: proforma de otra empresa → 404; módulo deshabilitado → 403 `module_disabled`; la empresa sale de la sesión; en odontología rige además el permiso clínico y que el paciente sea el de la proforma.
- AC-12 Guardar un borrador repetidamente conserva los ids de línea y no pierde los vínculos de origen.
- AC-13 Aceptar no crea ventas, cuentas por cobrar, citas, ejecución ni movimientos de stock (verificado por conteo de filas en las pruebas de integración).
- AC-14 UI en ambos detalles (DDR): decisión y fecha con texto por línea; selección de líneas; diálogo con resumen exacto de lo que se acepta/rechaza e importe; totales propuesto, aceptado y pendiente separados del saldo; historial; versiones anteriores en lectura; imprimir; estados cargando/vacío/error/éxito; doble envío bloqueado; teclado; texto en es/en/pt.
- AC-15 Los endpoints y pruebas existentes de crear, editar, presentar y versionar proformas siguen pasando (compatibilidad hacia atrás de la API).

## Edge cases / Error cases
Selección vacía → 400; `line_ids` repetidos → 400; más de 200 líneas → 400 (límite existente); doble clic en «Confirmar» → una sola escritura; dos usuarios decidiendo la misma línea a la vez → bloqueo de la proforma, el segundo recibe 409; proforma con una sola línea; todas las líneas rechazadas y nueva versión; versión nueva sin cambios; rectificación en una versión ya reemplazada → 409; cliente/paciente archivado: decidir sigue permitido (es un registro sobre un documento ya presentado), crear versión o presentar mantienen sus validaciones actuales.

## Authorization / permissions
Mismos permisos de cada módulo (`quotations`: administrador de empresa activa y módulo habilitado; `dentistry`: `CompanyClinicalPermission` + `dentistry`, `customers`, `services`). Rectificar: `can_rectify(user)` en el backend (hoy rol admin). La empresa sale de la sesión; el usuario que registra sale de la sesión.

## API contract
- API-01 `POST /api/quotations/proformas/{id}/decisions/` y `POST /api/dentistry/proformas/{id}/decisions/` — cuerpo `{idempotency_key, decision: accepted|rejected, line_ids[], accepted_by_name?, medium?, reference?, reason?}`; 200/201 con el detalle de la proforma, `replayed`, y resumen `{lines, amount}`.
- API-02 `POST …/proformas/{id}/lines/{line_id}/rectify/` — `{idempotency_key, decision, reason, accepted_by_name?, medium?, reference?}`.
- API-03 `GET …/proformas/{id}/printable/` — subconjunto comercial.
- API-04 El detalle existente suma campos aditivos por línea (`decision`, `decided_at`, `recorded_by_name`, `accepted_by_name`, `medium`, `reference`, `reason`, `line_kind`, `origin_line_id`, `authorized`) y a nivel de proforma (`acceptance_status`, `totals`, `decision_history`, `previous_version_id`; `allowed_actions` gana `decide`/`rectify`); `versions[]` suma `accepted_total` y `acceptance_status`. Sin quitar ni renombrar campos existentes.
- Errores: 400 validación por campo, 403 permiso/módulo, 404 no encontrada, 409 estado/idempotencia.

## UI behavior
- UI-01 Detalle: resumen de tres importes + badges (DDR, «Detalle con pestañas y acciones de ciclo de vida»).
- UI-02 Tabla de líneas con casillas, columna Decisión (badge + fecha), etiquetas de tipo de línea y candado de bloqueo.
- UI-03 Diálogo «Registrar decisión» en dos pasos con resumen y clave de idempotencia al abrir («Formulario con líneas y paso de resumen»).
- UI-04 Diálogo de rectificación con motivo («Diálogo de acción irreversible con motivo»).
- UI-05 Historial de decisiones y tabla de versiones ampliada; versiones reemplazadas en solo lectura.
- UI-06 Vista imprimible `…/imprimir` con `@media print`.

## Non-functional requirements
`select_for_update` en la proforma al decidir; consultas del detalle sin N+1 (`prefetch_related` de líneas y decisiones); i18n es/en/pt con las mismas claves; sin dependencias nuevas.

## Out of scope
Ejecución de tratamientos, cobros, facturación, citas y saldo financiero; aceptación parcial de cantidades; PDF generado en servidor; firma electrónica o carga de archivos de evidencia (solo referencia de texto); protección de rectificaciones frente a ejecución/cobros vinculados (no existen aún; se documenta como límite); extracción de lógica común a `shared/`.

## Open questions
Ninguna bloqueante. Supuestos a confirmar sin impedir la implementación: catálogo de medios de aceptación (INV-03), rectificación solo para admin (INV-05) y bloqueo de líneas aceptadas heredadas en el borrador (INV-07).

# Test Specification

## Unit tests
Dominio puro de cada módulo (`SimpleTestCase`): `decide` (INV-01..04, AC-04, 05), `rectify` (INV-05, AC-06), `acceptance_status` y totales con `Decimal` (INV-06, AC-01, 07), `new_version` con vínculo y recálculo de `line_kind` (INV-07, 08, AC-08, 09).

## Integration tests
API con PostgreSQL (`TransactionTestCase`) por módulo: AC-01..13 y 15 — dos empresas, módulo deshabilitado, reintento con la misma clave (y concurrente con `Barrier` para el doble envío), conservación de ids al guardar, `printable` sin campos internos, conteo de filas ajenas (ventas, stock, citas) sin cambios, regresión de las suites existentes de `quotations`, `dentistry`, `modularity` y `test_boundaries`.

## Frontend
Specs de servicios (URL, cuerpo, clave de idempotencia reutilizada) y de componentes (`provideTestTranslations()`): diálogo de decisión (resumen e importe, doble envío, error conservando datos), historial, detalle con casillas y bloqueos, vista imprimible sin campos internos; `ng build`, `npm run lint`, `npm run i18n:check`.

## E2E
**NO** — el flujo se cubre con integración de API, specs de componentes y un recorrido manual local; no se justifica instalar Playwright.

## Regression tests
`modules.quotations`, `modules.dentistry`, `modules.modularity`, `modules.service_catalog`, `modules.sales.tests.test_boundaries` y las specs de proformas existentes.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Dominio + integración (ambos módulos) |
| AC-02 | Integración |
| AC-03 | Integración (incluye concurrencia) + spec de servicio (clave reutilizada) |
| AC-04 | Dominio + integración |
| AC-05 | Dominio + integración |
| AC-06 | Dominio + integración |
| AC-07 | Dominio |
| AC-08 | Dominio + integración |
| AC-09 | Integración |
| AC-10 | Integración + spec de la vista imprimible |
| AC-11 | Integración |
| AC-12 | Integración |
| AC-13 | Integración (conteo de filas) |
| AC-14 | Specs de componentes, `ng build`, `i18n:check`, recorrido local |
| AC-15 | Suites existentes sin cambios |

# Implementation Plan

## Architecture considerations
Según el ADR: libro append-only por línea, guardado por diferencia, vínculo de origen, idempotencia por lote, duplicación consciente entre módulos, sin `shared/` de negocio.

## Proposed solution
Dominio: `LineDecision` (valor) y métodos `decide`, `rectify`, propiedades `acceptance_status`/`totals` en `Proforma` y `DentalProforma`; `new_version()` propaga `origin_line_id`, `line_kind` y la decisión; `replace_content` recalcula `line_kind`. Aplicación: `ProformaService.decide/rectify/printable` con bloqueo y puerto de lotes. Infraestructura: modelos de decisión y lote, repositorio que guarda líneas por diferencia. API: tres vistas por módulo y serializers aditivos. Frontend: modelos, servicios API, tres componentes compartidos, ajustes de ambos detalles, ruta de impresión e i18n.

## Files/components affected
- Backend `quotations`: `domain/proforma.py`, `application/proformas.py`, `infrastructure/django/{models,repositories}.py`, `api/{views,serializers,urls}.py`, `migrations/0002_*`, `tests/`.
- Backend `dentistry`: `domain/proforma.py`, `application/proformas.py`, `infrastructure/{proforma_models,proforma_repository}.py`, `api/{proforma_views,urls}.py`, `migrations/0003_*`, `tests/`.
- Frontend: `shared/models/proforma-decisions.ts`, `shared/components/proforma-decisions/{decision-dialog,rectify-dialog,decision-history}`, `features/quotations/{models,services,pages}`, `features/dentistry/{models,services,pages}`, rutas de impresión, `assets/i18n/{es,en,pt}.json`.
- Docs: `docs/design/design-system.md` (sección nueva), nota breve en `docs/architecture/ddd.md`.

## Implementation steps
1. `quotations` dominio: decisiones, estado derivado, totales, versionado con origen (INV-01..08; AC-01, 04..09) + pruebas.
2. `quotations` persistencia: modelos/migración 0002, repositorio por diferencia con ids estables y libro de decisiones (INV-04, 11; AC-12).
3. `quotations` aplicación y API: `decide` idempotente, `rectify`, `printable`, serializers aditivos, `can_rectify` (API-01..04; AC-02, 03, 06, 10, 11, 13, 15) + pruebas de integración.
4. Repetir 1–3 en `dentistry` (migración 0003; rutas `/api/dentistry/proformas/{id}/…`; permiso clínico; pieza dental en `printable`).
5. Frontend compartido: modelo y tres componentes (UI-03..05) con specs.
6. Frontend `quotations`: modelos, servicio, detalle (UI-01, 02, 05), imprimir (UI-06), i18n.
7. Frontend `dentistry`: lo mismo sobre el detalle odontológico.
8. Actualizar `design-system.md` y `ddd.md`; `ng build`, lint, `i18n:check`, suites backend con PostgreSQL; registrar resultados.

## Database / migrations
`quotations/0002`: columnas `origin_line_id` (UUID nulo) y `line_kind` (varchar, por defecto `original`) en la línea; tablas `quotations_proforma_line_decision` y `quotations_proforma_decision_batch` (único `(company_id, idempotency_key)`; índices por línea y por empresa/proforma). `dentistry/0003`: equivalente para `dentistry_proforma_line`. Aditivas y sin backfill (las líneas existentes quedan `original` y pendientes). No se editan migraciones aplicadas; `accepted_total` queda sin uso.

## Risks
Cambiar el guardado de líneas por diferencia puede romper la edición de borradores (cubrir con regresión); duplicación entre módulos; fusión con `main` (15 commits atrás) en rutas, i18n y `test_boundaries.py`; reintentos concurrentes; filtrado de datos en la vista imprimible; rectificaciones sin protección frente a ejecución/cobros porque aún no existen.

## New dependencies
Ninguna.

## Changelog
_(sin cambios desde v1)_
