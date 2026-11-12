# TASK-simplificar-flujo-proforma-cobro: Simplificar el flujo proforma → aceptación → cobro

**Etapa actual:** PUBLISH
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
| 2026-11-12 | ENGINEERING → REVIEW | Implementación completa; pendiente Quality Gate | delivery-build |
| 2026-11-12 | REVIEW → ENGINEERING | Quality Gate FAIL (1.ª ronda): REV-01 High (diálogo de cobro no se cierra tras pagar), REV-02 Medium, REV-03 Low | delivery-publish |
| 2026-11-12 | ENGINEERING → REVIEW | REV-01..03 corregidos; segunda ronda del Quality Gate | delivery-build |
| 2026-11-12 | REVIEW → PUBLISH | Quality Gate ronda 2: PASS con limitaciones (REV-04/05 Low abiertos) | delivery-publish |

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
**Resumen.** Backend: campo aditivo `proforma_id` en el detalle de Cobros (`shared/domain/commitment.py`, facades de `quotations` y `dentistry`, serializer). Frontend: el modelo y el servicio de Cobros pasan a `shared/`; nuevos `shared/components/{payment-dialog,collection-panel,status-badge}`, `shared/utils/{payment-allocation,default-acceptor}`; el diálogo de decisión (`proforma-decisions`) es de un solo paso con «Aceptar todo», precarga y CTA «Cobrar ahora»; los detalles de proforma (genérica y dental) cobran en contexto; la ficha del paciente muestra Aceptado/Cobrado/Saldo y «Cobrar»; Cobros usa el diálogo compartido, vuelve a la proforma/paciente y usa `app-status-badge`; menú plano; textos y `design-system.md` actualizados.

**Cobertura.** AC-01..03 y AC-14: `proforma-decisions.component.spec.ts` + `default-acceptor.spec.ts` (INV-05). AC-04: `proforma-decisions` (CTA y «Más tarde»). AC-05/06 (INV-01, INV-03, INV-04): `payment-allocation.spec.ts` + `payment-dialog.component.spec.ts` (atajos, reparto, distribución manual, payload, doble envío, idempotencia, error, 409/REV-02). AC-07/08: specs de detalle de proforma dental y genérica (con y sin Cobros). AC-09: `patient-proformas.component.spec.ts`. AC-10 (API-01): `receivables/tests/test_api.py`, `test_domain.py` (`proforma_id`) y `commitment-detail.component.spec.ts`. AC-11: textos de los specs y `i18n:check`. AC-12: `sidebar-menu.spec.ts`. AC-13: `status-badge.component.spec.ts` (el contraste en navegador queda para el Quality Gate). AC-15: `i18n:check` y claves es/en/pt.

**Desviaciones respecto al plan.**
- Se añadió `shared/components/collection-panel` (no estaba en el plan): encapsula, para las dos proformas, la lectura del estado de cobro, el diálogo y el comprobante; evita duplicar esa lógica en dos páginas.
- El diálogo de cobro carga el compromiso al abrirse (siempre saldo fresco, sirve a los cuatro puntos de entrada) en lugar de recibir las líneas por input.
- `app-status-badge` usa clases de Bootstrap 5.3 (`bg-*-subtle text-*-emphasis`) y no una paleta propia, para no introducir HEX.
- En la ficha del paciente, Cobrado/Saldo solo se calculan para la versión **presentada** de cada proforma (las demás filas muestran «—»), porque el cobro es por proforma vigente.
- El modelo `Commitment` del frontend tiene `proforma_id` obligatorio (`string | null`).

**Deuda técnica.** Claves i18n que quedaron sin uso (`RECEIVABLES.REVISAR/VOLVER/IR_ORIGEN`, `PROFORMA_DECISIONS.NOTA_SALDO` y similares) y el `app.routes`/estilos antiguos de `badge-outline` en el resto del sistema; la lista de obligaciones sigue paginada en memoria (PB-COB-001). Dos estilos de badge conviven hasta migrar el resto.

**Pantallas.** Referencias: «Detalle con selección de líneas y registro de decisión», `purchase-payments-tab` (alta por diálogo con saldo e idempotencia) y la lista/detalle de Cobros. Componentes compartidos creados: `app-payment-dialog`, `app-collection-panel`, `app-status-badge`; reutilizados: `money`, `Page`, `ModulesService`.

**Verificación propia (no es el Quality Gate).** Backend con PostgreSQL: `manage.py test` completo → `Ran 1502 tests ... OK`. Frontend: `ng lint`, `ng build`, `i18n:check` y `ng test` → 1344 correctas y 1 fallo previo e independiente (`screens-i18n.spec.ts`, «Entregue/Entregado»; también falla en `main`).

## Review
**Ronda 1 — FAIL.** Hallazgos: [REV-01](docs/reviews/REV-2026-11-12-simplificar-flujo-proforma-cobro-01.md) High (el diálogo de cobro no se cerraba tras un pago exitoso: `close()` salía por `saving` aún en `true`), [REV-02](docs/reviews/REV-2026-11-12-simplificar-flujo-proforma-cobro-02.md) Medium (enlace «Distribuir por tratamiento» ilegible en tema oscuro), [REV-03](docs/reviews/REV-2026-11-12-simplificar-flujo-proforma-cobro-03.md) Low (mensaje de monto mayor al saldo hablaba de «imputación»). Evidencia: backend 1502 pruebas OK; frontend lint/build/i18n OK; `ng test` con el fallo previo de `screens-i18n` y un segundo fallo intermitente no identificado en 1 de 4 ejecuciones.
**Correcciones:** REV-01 (`dismiss()` cierra sin la guarda de `saving`; la prueba ahora comprueba cierre y foco y falla con el código anterior), REV-02 (botón `btn-light`), REV-03 (mensaje «El monto supera el saldo por cobrar.»).
**Ronda 2 — PASS con limitaciones.** REV-01, REV-02 y REV-03 reverificados y resueltos (cierre y foco del diálogo en tres pantallas; contraste del enlace 1.14 → 13.95 en tema oscuro; mensaje de monto). Nuevos, Low y abiertos: [REV-04](docs/reviews/REV-2026-11-12-simplificar-flujo-proforma-cobro-04.md) (etiqueta pequeña «Saldo por cobrar» a 3.89:1 en tema oscuro) y [REV-05](docs/reviews/REV-2026-11-12-simplificar-flujo-proforma-cobro-05.md) (foco en `body` si el pago salda la deuda). Evidencia: backend 1502 pruebas OK, bandit sin hallazgos; frontend lint/build/i18n/audit OK; `ng test` 8 ejecuciones con fallos solo preexistentes de aislamiento de idioma entre specs (`screens-i18n`, `reception-quantities` de Compras), ajenos al diff. No verificado: «Aceptar todo» → «Cobrar ahora» en navegador, móvil 390 px reales, proforma dental con Cobros deshabilitado.

## Publicación
PR #65 listo para aprobación humana (no se mergea); apilado sobre el PR #61, que debe integrarse antes o retargetarse a `main`. Sin cambios sensibles propios: sin ADR, sin migraciones, sin cambios de autenticación/autorización (campo aditivo `proforma_id`). Pendiente de la persona que aprueba: revisar en navegador el flujo «Aceptar todo» → «Cobrar ahora» y el móvil a 390 px, y decidir si se corrigen REV-04/05 (Low) antes del merge.
