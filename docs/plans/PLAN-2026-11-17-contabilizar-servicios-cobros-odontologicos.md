# PLAN-2026-11-17-contabilizar-servicios-cobros-odontologicos (v1.1)

**Task:** TASK-contabilizar-servicios-cobros-odontologicos · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** `docs/design/DDR-contabilizar-servicios-cobros-odontologicos-prestacion-y-errores-en-cobros.md` · `docs/adr/ADR-contabilizar-servicios-cobros-odontologicos-prestacion-asientos-y-enrutamiento-de-cobros.md`

## Objective
Contabilizar por partida doble los servicios odontológicos y sus cobros: un tratamiento marcado como prestado reconoce el ingreso (Cuentas por cobrar / Ingresos por servicios, aplicando anticipos) y cada cobro sigue un único camino (anticipo, cobro contra Cuentas por cobrar o libro anterior), sin duplicar ingresos.

## Context
Resumen en el TASK. Base: rama `accounting` (VEN-01, CONT-10, CONT-12 incluidos). El patrón es el de VEN-01 adaptado a Cobros; la persona fijó el evento de reconocimiento (acción «Marcar como prestado», por tratamiento, irreversible).

# Specification

## Domain context
Bounded context `receivables` (Cobros), con `accounting` como proveedor de asientos (fachada `services`) y `quotations`/`dentistry` como fuentes del compromiso (solo `mark_lines_collected`, ya existente).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Compromiso / obligación | Proforma presentada vigente y su registro de cobros | `receivables/domain/obligation.py` |
| Tratamiento / línea | Línea aceptada de la proforma; `lineage_id` estable entre versiones | `shared/domain/commitment.py` |
| Servicio prestado | Tratamiento marcado por la persona; reconoce el ingreso | Decisión 2026-11-17 |
| Anticipo de cliente | Cobro imputado a un tratamiento aún no prestado (Pasivo) | VEN-01, `posting.py` |

## Current behavior
Cada pago crea una entrada del libro anterior (`origin_kind` `SERVICE`) (`receivables/infrastructure/adapters.py:46-73`); no hay reconocimiento de ingresos ni forma de marcar un tratamiento como prestado.

## Expected behavior
- Con Contabilidad cubriendo la fecha: un cobro a un tratamiento sin prestar crea un asiento de anticipo; marcar como prestado crea el reconocimiento; un cobro a un tratamiento prestado crea un asiento contra Cuentas por cobrar. Una proforma sin prestación ni cobro no crea asientos.
- Sin cobertura (Contabilidad deshabilitada, fecha anterior al corte o en un hueco): sin cambios respecto de hoy.

## Domain rules / invariants
- **INV-01** (nueva) Una línea se presta una sola vez; la prestación es única por (obligación, `lineage_id`) y no se deshace.
- **INV-02** (nueva) Solo se presta una línea aceptada de la proforma presentada vigente; el importe reconocido es el aceptado de la línea.
- **INV-03** (nueva) Fecha de prestación ≤ hoy (zona horaria de la empresa); por defecto hoy.
- **INV-04** (nueva) Cada porción de un cobro sigue exactamente un camino y un cobro nunca aumenta Ingresos: el ingreso solo lo reconoce la prestación.
- **INV-05** (nueva) El ingreso reconocido por una línea = su importe aceptado; Debe Anticipos = lo imputado a la línea antes de prestarla; Debe Cuentas por cobrar = el resto. No se generan líneas de importe cero.
- **INV-06** (existente, se conserva) Idempotencia por `idempotency_key` + huella; imputación ≤ saldo de línea; suma de imputaciones = monto; bloqueo obligación → proforma.
- **INV-07** (existente, se conserva) Una línea con movimiento (cobrada o prestada) no se rectifica a rechazada.

## Acceptance criteria
- **AC-01** Catálogo: `SERVICE_RECOGNITION` con segunda línea de Debe `CUSTOMER_ADVANCES` y nuevo `SERVICE_ADVANCE`; ambos aparecen en la configuración del módulo Cobros con sus roles (Ingresos por servicios, Cuentas por cobrar, Anticipos de clientes, cuenta del método).
- **AC-02** (tarjeta 1) Servicio de 500 prestado, cobro de 200 en efectivo y 300 por banco → Ingresos por servicios 500, saldo por cobrar 0 (los dos cobros contra Cuentas por cobrar, cada uno con la cuenta de su método).
- **AC-03** (tarjeta 2) Una proforma presentada/aceptada sin prestación ni pago no genera ningún asiento.
- **AC-04** (tarjeta 3) Reintentar el mismo cobro (misma clave) devuelve el pago original sin asiento nuevo; con la misma clave y otros datos, 409; si el asiento falla (configuración, período cerrado) el pago y la imputación se deshacen.
- **AC-05** (tarjeta 4) Cobrar un tratamiento sin prestar: Debe Caja/Banco / Haber Anticipos; Ingresos no cambia. Al prestarlo: Debe Anticipos por lo aplicado + Debe Cuentas por cobrar por el resto / Haber Ingresos por el importe aceptado.
- **AC-06** Prestar sin cobros previos: Debe Cuentas por cobrar / Haber Ingresos; sin línea de Anticipos. Prestar con anticipo igual al importe: Debe Anticipos / Haber Ingresos, sin línea de Cuentas por cobrar.
- **AC-07** Pago que mezcla líneas prestadas y no prestadas: dos asientos (cobro y anticipo) con las porciones correctas; reintento idempotente; la suma de ambos = monto del pago.
- **AC-08** Repetir «Marcar como prestado» sobre la misma línea devuelve la prestación existente (200) sin asiento nuevo; dos peticiones concurrentes crean una sola prestación y un solo asiento.
- **AC-09** Rechazos accionables (409 con `code`): configuración incompleta (con `issues`), período cerrado/fecha fuera de período, `payment_date_not_covered`, `service_has_unposted_payments`; ninguno deja datos a medias.
- **AC-10** Cobro con fecha sin cobertura a una línea sin prestar, o con Contabilidad deshabilitada: comportamiento actual (libro anterior / nada), sin cambios.
- **AC-11** Línea prestada: no se puede rectificar a rechazada; línea no aceptada, rechazada, de proforma no vigente o ya prestada con otro pedido: 409/422 claro y sin asiento.
- **AC-12** Aislamiento por empresa y permisos: la API de prestación usa los mismos permisos que cobrar (clínico en Odontología); otra empresa no ve ni afecta prestaciones.
- **AC-13** Frontend: acción «Marcar como prestado» por tratamiento con diálogo de confirmación (fecha, advertencia irreversible), estado «Prestado» por fila, total «Reconocido» y alertas contables accionables en prestar y cobrar; todo en es/en/pt.

## Edge cases / Error cases
- **EDGE-01** Fecha de prestación sin cobertura: se presta sin asiento si no hay anticipos; con anticipos ya contabilizados, `service_date_not_covered` (o `fiscal_period_unavailable` si el período está cerrado) y no se presta.
- **EDGE-02** Línea con cobros del libro anterior (sin asiento) prestada con cobertura: `service_has_unposted_payments` (decisión pendiente de negocio).
- **EDGE-03** Cobro posterior a una línea prestada sin asiento (prestada antes de la cobertura): libro anterior.
- **EDGE-04** Proforma que se versiona después de prestar: la prestación sigue ligada por `lineage_id`.
- **EDGE-05** Pago por exactamente el saldo restante tras prestar: saldo por cobrar 0.

## Authorization / permissions
Sin permisos nuevos: `CompanyModulePermission`/`CompanyClinicalPermission` de `_authorize`. El frontend solo oculta el botón; el backend decide.

## API contract
- **API-01** `POST /api/receivables/commitments/<kind>/<number>/services/` `{line_id: uuid, service_date?: 'AAAA-MM-DD'}` → 201 prestación nueva / 200 ya prestada; cuerpo = detalle del compromiso + `service` (`id`, `line_id`, `service_date`, `amount`) + `replayed`.
- **API-02** El detalle (`GET .../commitments/<kind>/<number>/`) añade por línea `rendered`, `service_date`, `can_render` y en `totals` `recognized`; cambios aditivos, compatibles hacia atrás.
- **API-03** Los 409 conservan `{detail, code}`; `posting_configuration_missing` añade `issues`.

## UI behavior
- **UI-01** Detalle del compromiso (plantilla «Detalle con selección de líneas», `design-system.md` §5): columna «Prestación» con `app-status-badge` («Prestado el dd/MM/aaaa» / «Sin prestar») y botón «Marcar como prestado» por línea elegible.
- **UI-02** Diálogo de confirmación con tratamiento, importe, fecha (≤ hoy), advertencia irreversible; estados de carga/error/éxito; foco restaurado.
- **UI-03** Alerta de rechazos contables compartida (extraída de Ventas) en el diálogo de prestación y en el de cobro, con enlace a la configuración del módulo.
- **UI-04** Total «Reconocido» en el resumen del detalle.

## Non-functional requirements
Dinero en `Decimal` a dos decimales; BOB sin conversión; atomicidad (`transaction.atomic`); sin N+1 al construir el detalle (una consulta de `automatic_entry_origins`).

## Out of scope
Vincular citas atendidas con tratamientos; desmarcar/anular prestaciones; reembolsos; costo/stock; honorarios y profesional por línea; impuestos; tratamiento de cobros previos a la cobertura sobre líneas prestadas con cobertura (se bloquea).

## Open questions
- Tratamiento de líneas con cobros anteriores a la cobertura contable (hoy bloqueado).
- Anulación/reembolso de servicios prestados.

# Test Specification

## Unit tests
- Dominio `Obligation.mark_rendered` (INV-01..03, AC-08, AC-11) y `build_statement` con prestaciones; función pura de división de porciones de un cobro (INV-04, AC-07); catálogo (AC-01).
## Integration tests
- `receivables/tests/test_service_posting.py` con Contabilidad real (PostgreSQL): AC-02..AC-10 incluidos hilos para concurrencia (AC-08, cobro vs. prestación), reversión por fallo contable (AC-04), cobros mixtos (AC-07), períodos cerrados, aislamiento por empresa y permisos (AC-12); `test_api.py` actualizado; `accounting/tests/test_posting_*` para el catálogo; fronteras (`test_boundaries`).
- Frontend: specs de componentes (diálogo de prestación, detalle, alerta compartida) y `i18n:check`.
## E2E
**NO** — los flujos se cubren con pruebas de integración contra PostgreSQL y specs de componentes; no se instala Playwright. Revisión visual manual en `delivery-publish`.
## Regression tests
Suite completa del backend y del frontend; `makemigrations --check`.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | `accounting/tests/test_posting_domain.py`/`test_posting_config_api.py`, fixtures del panel, i18n |
| AC-02, AC-03, AC-05, AC-06 | `receivables/tests/test_service_posting.py` (libro real) |
| AC-04 | `test_service_posting.py` + `test_api.py` (idempotencia, reversión) |
| AC-07 | dominio (división de porciones) + `test_service_posting.py` |
| AC-08 | dominio + `test_service_posting.py` (hilos) |
| AC-09, AC-10 | `test_service_posting.py` |
| AC-11 | dominio + `test_api.py` + rectificación en `quotations`/`dentistry` |
| AC-12 | `test_api.py` (permisos, otra empresa) |
| AC-13 | specs de `commitment-detail`, `service-dialog`, alerta compartida; `i18n:check` |

# Implementation Plan

## Architecture considerations
Seguir ADR: tabla propia en Cobros, hecho deducido del libro, `post_automatic_entry` dentro de la transacción, un camino por porción de cobro; Cobros solo importa `accounting.services` desde `infrastructure/adapters.py`.

## Proposed solution
Ver ADR §1-8. Reutilizar el patrón de `SalesPostingAdapter` (`_posting_errors`, 409 con `issues`).

## Files/components affected
- **Backend:** `accounting/domain/posting.py` (catálogo), `receivables/domain/obligation.py` (`RenderedService`, `mark_rendered`, estado por línea, división de porciones), `receivables/application/collections.py` (puerto de contabilización, `render_service`, `register_payment` con porciones), `receivables/infrastructure/adapters.py` (`ServicePostingAdapter`), `receivables/infrastructure/django/{models,repositories}.py`, `receivables/api/{views,urls,serializers}.py`, `receivables/migrations/0002_*`, fachadas de `quotations`/`dentistry` solo si el mensaje de rectificación necesita ajustarse.
- **Frontend:** `features/receivables/pages/commitment-detail.*`, nuevo `shared/components/service-dialog`, extracción de la alerta de rechazos contables desde `features/sales` a `shared/components`, `shared/components/{payment-dialog,collection-panel}`, modelo y servicio de API de Cobros (`shared/`), i18n es/en/pt (incluidas las claves del evento `SERVICE_ADVANCE` y del módulo en el panel de configuración).
- **Tests y docs:** los de la Test Specification; `docs/design/design-system.md` (§3, alerta compartida) y `docs/producto/modulos-implementados.md` si lista Cobros.

## Implementation steps
1. Catálogo de Contabilidad: `SERVICE_RECOGNITION` con `extra_debit_role` y nuevo `SERVICE_ADVANCE`; ajustar `events_for`/pruebas del panel y fixtures (AC-01).
2. Dominio de Cobros: `RenderedService`, `Obligation.mark_rendered`, `Statement` con `rendered`/`recognized`, división de un cobro en porciones (INV-01..05, AC-07, AC-08, AC-11).
3. Persistencia: modelo, migración `0002`, repositorio (`add_rendered`, lectura por obligación/lote sin N+1).
4. Puerto y adaptador de contabilización de servicios (`ServicePostingAdapter`: estado por libro, ruteo por porción, reconocimiento con anticipos aplicados, bloqueos, traducción de errores) (AC-02..AC-06, AC-09, AC-10).
5. Caso de uso: `register_payment` con porciones (conserva libro anterior como camino c) y `render_service` (bloqueo obligación → proforma, `mark_lines_collected`) (AC-04, AC-08).
6. API: ruta `services/`, serializers y campos aditivos del detalle (API-01..03, AC-12).
7. Frontend: modelos/servicio, `service-dialog`, columna y acción en el detalle, total «Reconocido», alerta compartida y su uso en el diálogo de cobro/panel (UI-01..04, AC-13); claves i18n es/en/pt.
8. Pruebas de integración y de componentes; suites completas, `makemigrations --check`, lint, `i18n:check`, build.
9. Documentación (design-system, módulos implementados) y notas en el TASK.

## Database / migrations
`receivables/0002_rendered_service` (tabla nueva con FK a obligación, único `(obligation, lineage_id)`, `CHECK amount > 0`, índice por empresa). No se edita ninguna migración aplicada; sin migración de datos.

## Risks
- Cambio de reglas con cobertura (cobrar/prestar exigen cuentas configuradas): acotado a empresas con cobertura y explicado por el 409.
- Dos asientos por un mismo pago mixto: cubierto por `(evento, origen)` y pruebas de reintento.
- La marca `collected` cambia de sentido: revisar el texto del error de rectificación en ambas fuentes.
- Pruebas con PostgreSQL requieren `TEST_DATABASE_NAME`/credenciales del entorno.

## New dependencies
Ninguna.

## Changelog
- **v1.1** (2026-11-17): [Implementation Plan] EDGE-01 nombra el código `service_date_not_covered` (antes se decía `payment_date_not_covered`); sin cambio de comportamiento ni de Specification. Además se añadió la pantalla Cobros → Configuración (ruta `receivables/settings`) como paso implícito de AC-01. Solicitado por delivery-publish, REV-12.
