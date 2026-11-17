# TASK-contabilizar-servicios-cobros-odontologicos: Contabilizar servicios y cobros odontológicos por partida doble (SRV-01)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-contabilizar-servicios-cobros-odontologicos (desde `origin/accounting` b10b293, que ya contiene CONT-10, CONT-12 y VEN-01; base del PR = `accounting`, no `main`)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/88 (base `accounting`)
**Fuente:** https://trello.com/c/OhJ58t4R/17-srv-01-configurar-y-contabilizar-servicios-y-cobros-odontol%C3%B3gicos

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-17 | (nuevo) → INVESTIGATION | Task creado; base = rama `accounting` indicada por la persona | delivery-start |
| 2026-11-17 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE (lógica financiera, migración, frontera Cobros↔Contabilidad↔fuentes); 2 decisiones de negocio resueltas por la persona | delivery-start |
| 2026-11-17 | PLANNING → ENGINEERING | Specification READY; PLAN v1 | delivery-start |
| 2026-11-17 | ENGINEERING → REVIEW | Implementación completa según PLAN v1; pruebas propias en verde | delivery-build |
| 2026-11-17 | REVIEW → PUBLISH | Quality Gate PASS condicional (0 Critical/High); REV-01 y REV-02 resueltos, REV-03..06 Low abiertos | delivery-publish |

## Investigación

### Requerimiento
Tarjeta Trello SRV-01 (insumo, **no** Specification aprobada). Aclaración de la persona: usar como base la rama `accounting`.
- **Objetivo:** integrar servicios con cuentas por cobrar y cobros, sin duplicar ingresos.
- Configuración en Servicios/Cobros: Ingresos por servicios, Cuentas por cobrar y Caja/Banco por método.
- Determinar el evento que reconoce un servicio prestado; una proforma/borrador no reconoce ingresos por sí sola.
- Servicio reconocido: Debe Cuentas por cobrar / Haber Ingresos por servicios. Cobro posterior: Debe Caja/Banco / Haber Cuentas por cobrar. Prestación y cobro simultáneos pueden usar asiento directo si no hay reconocimiento previo; no contabilizar un cobro dos veces como ingreso.
- Si el flujo permite anticipos antes de prestar, usar Pasivo «Anticipos de clientes» y aplicarlo al reconocer; si no existe ese flujo, no introducirlo y documentar el límite.
- Preservar pagos parciales/mixtos, permisos clínicos, atomicidad, idempotencia y vínculo con servicio/cobro. Adaptar anulaciones existentes, sin asumir reembolsos.
- Aceptación: (1) servicio prestado 500, cobro efectivo 200 + banco 300 → Ingresos 500, saldo por cobrar 0; (2) una proforma sin prestación ni pago no genera ingresos; (3) reintentar un cobro no duplica el asiento y un fallo contable revierte el cobro; (4) si existen anticipos, recibirlos no aumenta Ingresos antes de prestar.
- Dependencias: CONT-12 (configuración) y CONT-10 (períodos), ya en `accounting`. Transversal: API y UI, aislamiento por empresa, permisos existentes, `Decimal`, BOB sin conversión; trabajar sobre `accounting` y verificar el código real antes de tocar contratos.

### Hechos encontrados
- **Los eventos ya existen en el catálogo y nadie los usa:** `SERVICE_RECOGNITION` (Debe `RECEIVABLE` / Haber `SERVICE_INCOME`) y `SERVICE_PAYMENT` (Debe `MONEY` / Haber `RECEIVABLE`) del módulo `receivables` (`backend/modules/accounting/domain/posting.py:90-91`); el rol `CUSTOMER_ADVANCES` (Pasivo) y `Event.extra_debit_role` los creó VEN-01 (`posting.py:44,63-65`). La fachada `post_automatic_entry(..., advance_applied=…)`, `check_posting_ready`, `automatic_entry_origins`, `find_automatic_entry` y `reverse_automatic_entry` está en `accounting/services.py:507-610`.
- **Cobros hoy:** `CollectionService.register_payment` (`receivables/application/collections.py:73-100`) corre en `transaction.atomic` (`receivables/api/views.py:68-77`), bloquea obligación → proforma, es idempotente por `idempotency_key` + huella (`collections.py:46-48,102-110`) y llama a `PaymentLedgerAdapter.record` → `record_entry` del **libro anterior** con origen `SERVICE` (`receivables/infrastructure/adapters.py:46-73`). No hay partida doble para servicios.
- **El pago se imputa por línea aceptada** (`Allocation`, `receivables/domain/obligation.py:54-60,180-207`); el saldo por línea = aceptado − imputado (`build_statement`, `obligation.py:110-129`). Solo se cobra una proforma **presentada vigente** (`obligation.py:154-155`, `shared/domain/commitment.py:36-38`).
- **No existe el hecho «servicio prestado»:** ni `Obligation`, ni las proformas (`quotations`/`dentistry`) ni Agenda lo modelan; `agenda/domain/appointment.py:8-11` tiene la cita «atendida» pero sin vínculo con tratamientos o proformas (`grep` de proforma/obligación en `agenda`: solo migraciones). Los cobros actuales son, por tanto, anticipos de un servicio aún no reconocido.
- **La línea cobrada queda protegida:** `mark_lines_collected` (`quotations/services.py:46-52`) marca la línea y sus copias posteriores y `rectify` no la deja pasar a rechazada (`quotations/domain/proforma.py:292`); Odontología tiene la copia equivalente. No hay anulación ni reembolso de pagos en Cobros.
- **Permisos:** `_authorize` aplica `CompanyClinicalPermission` a las proformas odontológicas y `CompanyModulePermission` a las genéricas (`receivables/api/views.py:42-56`).
- **Patrón a seguir (VEN-01):** `SalesPostingAdapter` decide por estado contable derivado del libro (sin banderas), enruta cada cobro a exactamente un camino, bloquea con errores accionables y traduce los errores del motor (`sales/infrastructure/adapters.py:175-330`); el 409 de configuración faltante lleva `issues` (`code`, `role`, `subject`, `message`, `params`).
- **Frontera:** `receivables/infrastructure/adapters.py:3` ya importa `modules.accounting.services` (solo desde infraestructura y por fachada).
- **Frontend:** detalle del compromiso `features/receivables/pages/commitment-detail.component.*` (tabla de tratamientos con Propuesto/Aceptado/Cobrado/Saldo), `shared/components/{payment-dialog,collection-panel,status-badge}`; el aviso de configuración faltante de VEN-01 vive en `features/sales/components/delivery-dialog` y `order-detail` (`posting_configuration_missing`).

### Hipótesis / supuestos no confirmados
- La fecha del asiento de reconocimiento es la **fecha de prestación** elegida (por defecto hoy, nunca futura); la del cobro es `payment_date`.
- Líneas de importe 0 no existen (los importes de línea son > 0), así que no hay caso de «servicio gratuito».
- Cobros con fecha sin cobertura contable (anteriores al corte) o con Contabilidad deshabilitada siguen el camino anterior sin cambios; los pagos hechos antes de esta tarea no tienen asiento de partida doble.

### Decisiones resueltas (persona, 2026-11-17)
1. **Evento de reconocimiento = acción explícita «Marcar como prestado» sobre cada tratamiento aceptado** de la proforma presentada vigente (no la cita atendida, no el cobro).
2. **Por tratamiento e irreversible:** cada línea aceptada se marca por separado; no se desmarca (revertir exigiría anulaciones/reembolsos que la tarjeta no asume). Una línea prestada no se puede rectificar a rechazada.
- Resto por criterio, documentado en ADR/PLAN (ver «Decisiones por criterio»).

### Decisiones por criterio (documentadas en ADR/PLAN)
- Los cobros anteriores a prestar **son anticipos** (el flujo actual ya los permite), así que se usa `CUSTOMER_ADVANCES`: no se introduce un flujo nuevo, se contabiliza el existente.
- Cobros imputados a líneas ya prestadas: Debe Caja/Banco / Haber Cuentas por cobrar; a líneas no prestadas: Debe Caja/Banco / Haber Anticipos. Un pago que mezcla ambos genera **dos asientos con el mismo `origin_id` y eventos distintos** (idempotentes por evento).
- Marcar como prestado es naturalmente idempotente (una fila por obligación y línea de origen): repetirlo devuelve la prestación existente sin asiento nuevo.
- Los casos sin tratamiento definido se **bloquean** con error claro, igual que VEN-01 (`service_has_unposted_payments`, `payment_date_not_covered`).

**Decisiones pendientes (no bloquean):** tratamiento de líneas con cobros hechos antes de la cobertura contable que se prestan con cobertura (hoy bloqueado, igual que VEN-01); reembolsos/anulaciones de servicios prestados (fuera de alcance).

### Módulos y dependencias relacionadas
`receivables` (dominio, caso de uso, adaptador, API, migración), `accounting` (catálogo: evento nuevo y segunda línea de Debe en `SERVICE_RECOGNITION`), `quotations` y `dentistry` (solo vía `mark_lines_collected` ya existente), frontend `receivables` y `shared/components`.

### Implementaciones similares existentes
VEN-01 (`SalesPostingAdapter`, `SALE_ADVANCE`/`SALE_DELIVERY`/`SALE_PAYMENT`), `PaymentLedgerAdapter` (libro anterior), PB-COB-001 (obligación, imputaciones, idempotencia).

### Comportamiento actual
Con Contabilidad habilitada cada cobro crea una entrada de una cuenta en el libro anterior (origen `SERVICE`); no hay reconocimiento de ingresos ni cuentas por cobrar por servicios, ni forma de indicar que un tratamiento fue prestado.

### Restricciones
`CLAUDE.md`: `Decimal`, aislamiento por `company_id`, no editar migraciones aplicadas (migración nueva y aditiva), sin dependencias nuevas, módulos solo por fachada, i18n es/en/pt sin texto hardcodeado, sin `any`, `docs/architecture/ddd.md`.

### Riesgos identificados
- **Cambio de reglas con cobertura:** cobrar y prestar exigirán cuentas de Anticipos/Ingresos/Cuentas por cobrar configuradas (409 accionable); sin cobertura no cambia nada.
- **Doble camino:** cada porción de cobro sigue exactamente un camino (anticipo, cobro contra CxC o libro anterior); prueba explícita de «nunca ambos».
- **Concurrencia:** cobrar y marcar prestado a la vez sobre la misma línea; mitigado con el bloqueo obligación → proforma ya existente y la unicidad (obligación, línea) en la prestación.
- **Pagos históricos sin asiento** sobre una línea que luego se presta con cobertura: bloqueado hasta definir su tratamiento (decisión pendiente).
- **Marca `collected`** también significará «prestada»: el mensaje de rectificación debe seguir siendo veraz.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — lógica financiera nueva, migración de datos (tabla de prestaciones), nueva regla de estado en un agregado y dos fronteras de módulo; se fija en un ADR.

### Diseño requerido
**SI** — nueva acción por tratamiento con confirmación y estados en el detalle del compromiso, y rechazos contables accionables en cobrar/prestar.

## Diseño
`docs/design/DDR-contabilizar-servicios-cobros-odontologicos-prestacion-y-errores-en-cobros.md`

## Arquitectura
`docs/adr/ADR-contabilizar-servicios-cobros-odontologicos-prestacion-asientos-y-enrutamiento-de-cobros.md`

## Plan
`docs/plans/PLAN-2026-11-17-contabilizar-servicios-cobros-odontologicos.md` (v1, COMPLETO) · Specification readiness: **READY**

## Implementación
Implementado según **PLAN v1**, sin cambios de Specification.

- **Catálogo de Contabilidad** (`accounting/domain/posting.py`; AC-01): `SERVICE_RECOGNITION` con segunda línea de Debe (`CUSTOMER_ADVANCES`) y nuevo `SERVICE_ADVANCE`; claves i18n es/en/pt del evento (el panel de configuración es dirigido por datos).
- **Dominio de Cobros** (`receivables/domain/obligation.py`; INV-01..05, AC-07/08/11): `RenderedService`, `Obligation.mark_rendered` (idempotente por línea de origen), `applied_to`, `split_payment` (porciones de un cobro: cobro contra CxC, anticipo, libro anterior), `Statement`/`StatementLine` con `rendered`, `service_date`, `can_render` y `recognized`.
- **Persistencia** (`receivables/0002_rendered_service`, aditiva): tabla `receivables_rendered_service` con único `(obligation, lineage_id)` y `CHECK amount > 0`; repositorio `add_rendered`.
- **Adaptador y caso de uso** (`receivables/infrastructure/adapters.py`, `application/collections.py`; AC-02..AC-10): `ServicePostingAdapter` reemplaza a `PaymentLedgerAdapter` (puerto `ServicePosting`: `record_payment`, `recognize`); estado contable deducido del libro, ruteo por porción, anticipos aplicados al reconocer, bloqueos accionables (`posting_configuration_missing` con `issues`, `fiscal_period_unavailable`, `payment_date_not_covered`, `service_date_not_covered`, `service_has_unposted_payments`) y `CollectionService.render_service` (bloqueo obligación → proforma, `mark_lines_collected`).
- **API** (API-01..03): `POST /api/receivables/commitments/<kind>/<number>/services/` (201 nueva / 200 repetida); el detalle añade `rendered`, `service_date`, `can_render`, `totals.recognized` y la acción `render_service`; los 409 ahora llevan `data` adicional (`issues`).
- **Frontend** (UI-01..04, AC-13): `app-service-dialog` y `app-posting-issues-alert` compartidos, columna «Prestación» y total «Reconocido» en el detalle del compromiso, alerta contable también en el diálogo de cobro, `ReceivablesApiService.renderService` y 409 con `code`/`issues`.
- **Pruebas:** `receivables/tests/test_service_posting.py` (AC-01..AC-12 con Contabilidad real, hilos para concurrencia), `test_domain.py` (INV-01..05, split), specs de `service-dialog`, `commitment-detail` y `receivables-api.service`; las pruebas del libro anterior (`test_payment_ledger.py`) fijan un corte futuro, igual que VEN-01.

**Desviaciones respecto al plan (detalle de implementación, sin cambio de Specification):**
- Se añadió la pantalla **Cobros → Configuración** (ruta `receivables/settings`, `module-settings` con `receivables` en `POSTING_MODULES`) y el menú Cobros pasa de ítem plano a grupo con dos ítems: sin ella no había dónde configurar las cuentas de Cobros (la tarjeta pide «Configuración en Servicios/Cobros»). Se actualizó `sidebar-menu.spec.ts` (el AC-12 antiguo decía «ítem plano… si aparecen otras pantallas se vuelve a agrupar»).
- Código del bloqueo por fecha de prestación sin cobertura con anticipos: `service_date_not_covered` (el plan decía `payment_date_not_covered`/`fiscal_period_unavailable` según el caso).
- La extracción de la alerta de Ventas a `shared/` (DDR) se hizo solo para Cobros: Ventas conserva su aviso propio (deuda anotada en `design-system.md` §10) para no tocar Ventas fuera de alcance.

**Verificación propia (no es el Quality Gate):** backend `manage.py test` 2057 OK, `makemigrations --check` sin cambios; frontend `ng lint` OK, `i18n:check` 2193 claves y 0 faltantes, `ng build` OK, `ng test` 1599 de 1599 OK. Entorno: `.env` copiado sin leer desde otro worktree y `node_modules` enlazado (mismo `package-lock.json`); revisión visual no realizada.

**Deuda técnica / pendiente:** decisiones de negocio abiertas (cobros previos a la cobertura sobre líneas prestadas con cobertura: bloqueado; anulación/reembolso de servicios prestados); mensajes de configuración faltante solo en español (deuda CONT-12 REV-05); unificar la alerta de Ventas con la compartida.

## Review
**Quality Gate (PLAN v1): PASS con limitaciones** (subagente aislado, 2026-11-17). Backend: `manage.py test` 2057 OK, `makemigrations --check` sin cambios, bandit 0 High/Medium (23 Low solo en pruebas); ruff/flake8 no instalados (no realizado). Frontend: `ng lint` OK, `i18n:check` 2193 claves y 0 faltantes, `npm run build` OK, `ng test` 1599 de 1599 OK; `npm audit` 26 vulnerabilidades preexistentes (el diff no toca `package*.json`). Fronteras DDD, aislamiento por empresa, atomicidad/concurrencia y ausencia de doble contabilización verificados. **Revisión visual en navegador: no verificada.** No se comparó el warning de build «23 rules skipped» con la rama base.
- Resueltos tras el Gate: [REV-01](docs/reviews/REV-2026-11-17-contabilizar-servicios-cobros-odontologicos-01.md) (pruebas de `payment_date_not_covered` y `service_date_not_covered`; siguen sin prueba EDGE-04 y el conteo de consultas), [REV-02](docs/reviews/REV-2026-11-17-contabilizar-servicios-cobros-odontologicos-02.md) (mensaje de rectificación). Verificación posterior: `manage.py test modules.receivables modules.quotations modules.dentistry` 168 OK.
- **Revisión visual (2026-11-17, navegador integrado, app real con backend y base de datos de desarrollo; sin capturas porque el panel estaba oculto, medido por DOM):** detalle del compromiso con «Marcar como prestado» por tratamiento, diálogo con importe, fecha de hoy y advertencia; al confirmar, la fila pasa a «Prestado el 17/11/2026», se anuncia el resultado y el foco va a ese aviso; cobrar un anticipo sin la cuenta «Anticipos de clientes» muestra la alerta de configuración incompleta con enlace a Cobros → Configuración (contraste 8:1 aprox., texto 102/77/3 sobre 255/243/205); el panel de configuración de Cobros lista los roles y los tres eventos con su asiento previsto; a 375 px sin scroll horizontal y el diálogo cabe; cancelar devuelve el foco al botón. Tema oscuro: badge «Prestado» 10,35:1. **Hallazgos corregidos en la revisión:** el mensaje de error se mostraba duplicado (alerta roja y lista de faltantes) y el foco caía en `body` tras marcar. **No verificado:** capturas de pantalla, Chrome en tema claro/oscuro con el conmutador real, la pestaña de ajustes General de Cobros. Observación: las etiquetas `text-muted` (p. ej. «Sin prestar») quedan a ~3,8:1 en tema oscuro, patrón preexistente de la página.
- Tras el Gate se resolvieron REV-03 (alerta compartida también en Ventas), REV-04 (`_dark-tokens.scss`), REV-05 (líneas largas) y REV-06 (alertas del diálogo).
**Quality Gate, 2.ª pasada (PLAN v1.1, HEAD b778d3d): PASS con limitaciones** (subagente aislado, 2026-11-17). Backend: `manage.py test` 2059 OK, `makemigrations --check` sin cambios, bandit 0 High/Medium; ruff/flake8 no instalados. Frontend: `ng lint` OK, `i18n:check` 2189 claves y 0 faltantes, build OK, `ng test` 1599 de 1599 OK; `npm audit` preexistente. Verificó REV-01..06 contra el diff (el CSS de `skins/_dark.scss` compilado es idéntico al de `accounting`), sin regresiones en Ventas. **Sin verificar:** capturas, conmutador real de tema, pestaña General de Cobros, aspecto de la alerta compartida en Ventas, aviso de build «23 rules skipped» frente a la base.
- Hallazgos de la 2.ª pasada: REV-07 (alerta en Ventas, docs resuelta), REV-12 (PLAN, resuelto); **abiertos:** REV-10 Medium (sin prueba de EDGE-04 ni del conteo de consultas del detalle), REV-08, REV-09 y REV-11 Low (texto del mensaje de rectificación, permiso clínico sobre `services/`, línea de 122 en una prueba).

## Publicación
PR https://github.com/rolion/dore-mini-erp/pull/88 (base `accounting`) listo para aprobación humana; no se mergea. Cambio sensible: base de datos (migración aditiva `receivables/0002`), lógica financiera y cambio de reglas de cobro con cobertura contable; respaldo: ADR de prestación y asientos. Pendiente de la persona: revisión visual con capturas y del conmutador de tema, flake8/ruff, los REV-08..11 abiertos y las decisiones de negocio abiertas (cobros previos a la cobertura sobre líneas prestadas con cobertura; anulación/reembolso de servicios).
