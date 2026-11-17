# TASK-contabilizar-servicios-cobros-odontologicos: Contabilizar servicios y cobros odontológicos por partida doble (SRV-01)

**Etapa actual:** ENGINEERING
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
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
