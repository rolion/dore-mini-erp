# TASK-simplificar-flujo-proforma-cobro: Simplificar el flujo proforma → aceptación → cobro

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-simplificar-flujo-proforma-cobro (desde `task/TASK-cobrar-servicios-anticipos-pagos-parciales`, PR #61 aún sin mergear: depende del módulo `receivables`)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/65 (base: task/TASK-cobrar-servicios-anticipos-pagos-parciales, PR 61)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-12 | (nuevo) → INVESTIGATION | Task creado desde la crítica de diseño del flujo proforma → cobro | delivery-start |
| 2026-11-12 | INVESTIGATION → DESIGN → PLANNING | NEEDS_PLAN, diseño SI; sin decisiones de negocio abiertas | delivery-start |
| 2026-11-12 | PLANNING → ENGINEERING | Specification READY, PLAN v1 y PR | delivery-start |

## Investigación

### Requerimiento
Origen: crítica de diseño del 2026-11-12 sobre PB-COB-001 (screenshots del flujo en Odontología: ficha del paciente → proforma → presentar → aceptar → cobrar). Problema: el cobro vive en otro módulo y el recorrido completo exige unas 14 interacciones con tres confirmaciones. Pedido del usuario (alcance propuesto, confirmado al convertirlo en tarea):
1. Cobrar **dentro de la proforma** (diálogo que reutiliza un componente compartido) y CTA «Cobrar ahora» en el éxito de la aceptación; Cobros queda como lista/seguimiento con «Volver a la proforma/paciente».
2. Pago en un paso: monto con atajos (Total / 50 % / Otro), reparto automático en orden, distribución por tratamiento como opción avanzada plegada, resumen en el mismo diálogo, una confirmación.
3. Aceptación más corta: «Aceptar todo», precargar como quien acepta al **responsable** si el paciente es menor, motivo solo al rechazar/rectificar, referencia/evidencia plegada.
4. Ficha del paciente: columnas Aceptado/Cobrado/Saldo y acción «Cobrar» por fila; saldo real en el detalle de proforma en vez de «El saldo de cobro no se calcula aquí».
5. Consistencia: «Paciente» en Odontología; estados de decisión («Sin decidir») distintos de los de cobro («Por cobrar/Parcial/Pagado»); importes con dos decimales; menú Cobros sin submenú redundante; badges con fondo e icono y mejor contraste; quitar textos técnicos.
Límite: Cobros sigue siendo un módulo genérico, sin acoplarlo a Odontología; no cambian las reglas de negocio de PB-COB-001 salvo lo que haga falta para el reparto automático.

### Hechos encontrados
- `frontend/panel_admin/src/app/shared/components/proforma-decisions/proforma-decisions.component.ts:108-134,57` — la decisión es un diálogo de **dos pasos** (`step` 1 datos → 2 resumen → `confirm`), con «Revisar resumen» y «Confirmar»; `:69-74` el formulario siempre incluye `reason` y `reference`; `:120` exige nombre y medio al aceptar; `:183` `resetDialog()` deja `accepted_by_name` vacío (no hay precarga).
- `proforma-decisions.component.html:11` — nota «El saldo de cobro no se calcula aquí.» (`PROFORMA_DECISIONS.NOTA_SALDO`, `es.json:2294`); `:21-24` solo «Aceptar seleccionadas/Rechazar seleccionadas» (sin «Aceptar todo»); `:170-174` el motivo se pide también al aceptar; `:15` el éxito es un `alert-success` sin acción siguiente.
- `features/quotations/pages/proforma-detail.component.html:21` y `features/dentistry/pages/dental-proforma-detail.component.html:24` — `@if (p.collectible)` muestra un enlace «Cobrar» que **navega** a `/pocketbiz/receivables/<tipo>/<número>`; no comprueba que el módulo `receivables` esté habilitado.
- `features/receivables/pages/commitment-detail.component.ts` (formulario en panel propio) — monto + `distributeInOrder()` manual + una fila de imputación por tratamiento + «Revisar resumen» + «Confirmar»; `localToday()`, `toCents/fromCents` en `models/receivable.ts`; clave de idempotencia reutilizada en reintentos; el resumen muestra el monto tal como se tecleó (`form.controls.amount.value | money`).
- `commitment-detail.component.html:24` / `.ts` (`originLink`) — «Ver proforma» lleva a la lista (`?customer=<número>`) o a `/dentistry/patients`, porque la API de detalle no entrega el id de la proforma (`backend/modules/receivables/api/serializers.py:63-79`, `shared/domain/commitment.py` `CommitmentSnapshot` sin `proforma_id`).
- `features/dentistry/components/patient-proformas.component.html/.ts` — tabla Número/Fecha/Total/Estado/Acciones; `DentalProformaSummary` ya trae `accepted_total` y `collectible` (`backend/modules/dentistry/api/proforma_views.py` `summary_data`); sin Cobrado/Saldo.
- `backend/modules/dentistry/application/patients.py:61-66` y `features/dentistry/models/patient.ts:11-24` — el detalle del paciente (`GET /api/dentistry/patients/<id>/`) ya expone `customer.birth_date`, `responsible_name`; la regla de menor de edad (< 18) existe en `backend/modules/customers/domain/demographics.py:24-25`.
- `assets/data/routes.json` (entrada `MENUITEMS.RECEIVABLES.TEXT` con submenú «Cobros» único) y `layout/sidebar/sidebar-menu.spec.ts` — menú redundante.
- `docs/design/design-system.md` §3 «Badges de estado» (`badge-outline col-<color>`, solo texto de color), `app-payment-status-badge` en `features/sales/components/`, §8 checklist de contraste/estados. Estados actuales: decisión `ESTADO_PENDING` = «Pendiente» y cobro `RECEIVABLES.ESTADO_PENDING` = «Pendiente».
- `features/receivables/models/receivable.ts` y `services/receivables-api.service.ts` se importan solo desde `features/receivables`; los diálogos de decisión ya viven en `shared/components/` (patrón a seguir para el diálogo de cobro).
- Reglas de PB-COB-001 ya probadas (INV-01..10, 24 pruebas de integración de `receivables`): el contrato de pago exige `allocations` explícitas cuya suma sea el monto.

### Hipótesis / supuestos no confirmados
- «Reparto automático» = en el orden de las líneas de la proforma (no proporcional); se decide aquí y es solo comportamiento de la UI, el servidor sigue validando imputaciones explícitas.
- El atajo «50 %» es el 50 % del **saldo** redondeado al centavo hacia arriba (`ROUND_HALF_UP`).
- Para proformas genéricas (`quotations`) no hay concepto de menor/responsable: se precarga el nombre del cliente.
- El menú plano «Cobros» no necesita submenú porque no hay otra pantalla; si en el futuro aparecen reportes de cobranza se vuelve a agrupar.

### Módulos y dependencias relacionadas
Frontend: `shared/components/proforma-decisions`, `features/dentistry` (detalle de proforma y ficha del paciente), `features/quotations` (detalle), `features/receivables`, menú lateral, i18n. Backend: solo un campo aditivo en `receivables` (+ facades de `quotations` y `dentistry`).

### Implementaciones similares existentes
`shared/components/proforma-decisions` (diálogo compartido por dos módulos); `features/purchases/components/purchase-payments-tab` (alta de pago por diálogo con saldo y clave de idempotencia; `design-system.md` §5); `app-payment-status-badge` (badge propio con estado de pago).

### Restricciones
`CLAUDE.md` (sin texto hardcodeado, i18n es/en/pt, tipos explícitos, Reactive Forms, módulos solo por fachada, `Decimal`, sin dependencias nuevas). `design-system.md` §8 (contraste, móvil 390 px, tema claro/oscuro). PB-COB-001 y PB-COT-002 no cambian sus reglas de negocio.

### Riesgos identificados
- Mover el modelo y el servicio de Cobros a `shared/` toca varios imports y specs (mecánico pero amplio).
- Cambiar etiquetas de estado («Pendiente» → «Sin decidir» / «Por cobrar») afecta pruebas existentes y capturas.
- Un componente compartido de pago incrustado en dos páginas de módulos distintos duplica el riesgo de desalinear el estado al refrescar tras un 409 (ya corregido en REV-02 del PR #61; debe conservarse).
- La rama depende de un PR sin mergear (#61): si cambia antes de integrarse hay que rebasar.

### Veredicto de complejidad
**NEEDS_PLAN** — cambio acotado de UI con un campo aditivo de API; sin módulo, dependencia entre módulos, migración ni decisión arquitectónica nueva (los componentes compartidos siguen el patrón existente).

### Diseño requerido
**SI** — cambia un flujo de varios pasos y varias pantallas con riesgo de inconsistencia visual; introduce dos componentes reutilizables (`status-badge`, diálogo de cobro).

## Diseño
DDR: `docs/design/DDR-simplificar-flujo-proforma-cobro-flujo-y-pantallas.md` (reemplaza parcialmente `DDR-cobrar-servicios-anticipos-pagos-parciales-pantallas-cobros` y `DDR-presentar-aceptar-versionar-proformas-detalle-decisiones-e-impresion` en el diálogo de decisión y en el cobro).

## Arquitectura
No aplica según veredicto (sin ADR).

## Plan
`docs/plans/PLAN-2026-11-12-simplificar-flujo-proforma-cobro.md` (v1, COMPLETO). Specification readiness: **READY**.

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
