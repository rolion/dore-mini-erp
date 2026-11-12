# PLAN-2026-11-12-simplificar-flujo-proforma-cobro (v1)

**Task:** TASK-simplificar-flujo-proforma-cobro · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-simplificar-flujo-proforma-cobro-flujo-y-pantallas · Ninguno (ADR)

## Objective
Reducir el recorrido «presentar → aceptar → cobrar» de unas 14 interacciones a 6-7: aceptar todo en un paso, cobrar en contexto con reparto automático y una sola confirmación, y mostrar el saldo donde se decide, sin cambiar las reglas de negocio de PB-COT-002 ni de PB-COB-001.

## Context
Ver TASK y DDR. Rama apilada sobre el PR #61 (módulo `receivables`). El backend solo gana un campo aditivo; casi todo el trabajo es frontend.

# Specification

## Domain context
Contextos tocados solo en presentación: Cotizaciones (`quotations`), Odontología (`dentistry`) y Cobros (`receivables`). No hay dependencias nuevas entre módulos de backend; el frontend consume las APIs existentes.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Sin decidir | Línea o proforma sin decisión del paciente (antes «Pendiente») | DDR |
| Por cobrar / Parcial / Pagado | Estado de cobro (antes «Pendiente/Parcial/Pagado») | DDR |
| Cobrar ahora | CTA tras aceptar que abre el diálogo de cobro | DDR |
| Reparto automático | Aplicar el monto a las líneas con saldo en el orden de la proforma | DDR |
| Responsable | Persona que acepta por un paciente menor de edad (< 18) | `customers/domain/demographics.py:24-25` |

## Current behavior
Ver TASK «Hechos encontrados» (diálogo de decisión de dos pasos, «Cobrar» navega a otro módulo, pago con distribución manual, sin saldo en la proforma ni en la ficha).

## Expected behavior
Aceptar todo con un diálogo de un paso; tras aceptar, «Cobrar ahora» abre un diálogo de cobro compartido que propone el total, reparte solo y confirma de una vez; la proforma y la ficha del paciente muestran Cobrado y Saldo; Cobros vuelve a la proforma; etiquetas, badges y menú son consistentes.

## Domain rules / invariants
- INV-01 (existente, PB-COB-001): el servidor solo acepta imputaciones explícitas cuya suma es el monto y que no superan el saldo de la línea. La UI genera esas imputaciones; **no se cambia el contrato de pago**.
- INV-02 (existente): una línea con cobros no se puede rectificar a rechazada.
- INV-03 (nueva, solo UI): el reparto automático recorre las líneas con saldo en el orden de la proforma y asigna `min(restante, saldo de línea)`.
- INV-04 (nueva, solo UI): el atajo «50 %» es el 50 % del saldo redondeado al centavo hacia arriba; «Total» es el saldo.
- INV-05 (nueva, solo UI): *quién acepta* se precarga con el responsable si el paciente es menor (< 18 años según `birth_date` y `responsible_name` no vacío); si no, con el nombre del paciente/cliente; es editable y sigue siendo obligatorio.

## Acceptance criteria
- AC-01: con líneas sin decidir existe «Aceptar todo»; abre el diálogo con todas ellas seleccionadas.
- AC-02: el diálogo de decisión es de un solo paso (resumen + campos + un «Confirmar»); el motivo solo se pide al rechazar y rectificar; referencia/evidencia está plegada («Más datos»).
- AC-03: *quién acepta* viene precargado según INV-05 (dental: responsable si menor; genérica: nombre del cliente).
- AC-04: tras aceptar, si la proforma es cobrable y Cobros está habilitado, el mensaje de éxito ofrece «Cobrar ahora (Bs X)» y «Más tarde»; «Cobrar ahora» abre el diálogo de cobro sin navegar.
- AC-05: el diálogo de cobro ofrece atajos Total / 50 % / Otro, reparto automático (INV-03) con la línea «Se aplicará a…», la distribución por tratamiento plegada y editable, y una sola confirmación; reutiliza la clave de idempotencia ante reintentos y conserva los datos ante errores; tras un 409 recarga y reconstruye la distribución.
- AC-06: el payload enviado al servidor mantiene el contrato actual (allocations explícitas, suma = monto); el éxito muestra el comprobante y refresca los importes.
- AC-07: el botón «Cobrar» del detalle de proforma abre el diálogo (no navega) y solo aparece si Cobros está habilitado, la proforma es cobrable y hay saldo.
- AC-08: el detalle de proforma muestra Cobrado y Saldo (con Cobros habilitado) y ya no muestra «El saldo de cobro no se calcula aquí».
- AC-09: la ficha del paciente muestra Aceptado · Cobrado · Saldo y «Cobrar» por fila (con Cobros habilitado); sin obligación, Cobrado = 0.00 y Saldo = Aceptado; sin Cobros habilitado no hay columnas ni acción.
- AC-10: el detalle de Cobros ofrece «Volver a la proforma» (usa `proforma_id`) y, en dental, «Volver al paciente»; «Registrar pago» abre el mismo diálogo compartido.
- AC-11: etiquetas: decisión «Sin decidir/Aceptada/Rechazada»; cobro «Por cobrar/Parcial/Pagado»; «Paciente» en contexto dental; todos los importes con dos decimales.
- AC-12: el menú «Cobros» es un ítem plano sin submenú.
- AC-13: `app-status-badge` (icono + fondo tintado + texto) se usa para decisión, aceptación y cobro, con contraste ≥ 4.5:1 en claro y oscuro; `design-system.md` §3 lo documenta.
- AC-14: se eliminan los textos técnicos («El saldo de cobro no se calcula aquí», «Autorizada para el trabajo» → «Aprobada para realizar»).
- AC-15: i18n es/en/pt completa; accesibilidad del diálogo (foco al abrir y al cerrar, `aria-label` por importe, atajos con `aria-pressed`); sin regresión de las suites existentes.

## Edge cases / Error cases
Proforma sin líneas aceptadas o saldo 0 (no se ofrece cobrar); pago mayor al saldo (el atajo «Total» no lo permite y el servidor lo rechaza con 400); 409 por cambio concurrente (recarga y reconstruye la distribución); módulo Cobros deshabilitado (sin CTA, sin columnas); paciente sin fecha de nacimiento o sin responsable (se precarga el paciente); proforma de otro paciente/empresa (404 del servidor); falla de la carga de datos de cobro en la ficha (la tabla de proformas sigue visible, columnas de cobro con «—» y aviso discreto).

## Authorization / permissions
Sin cambios: el servidor valida módulos por fuente, empresa, líneas aceptadas e idempotencia. La UI solo oculta acciones que no aplican; no es la barrera.

## API contract
- API-01: `GET /api/receivables/commitments/<kind>/<number>/` añade el campo `proforma_id` (id de la versión vigente de la proforma); aditivo, sin romper clientes. El resto de contratos no cambia.

## UI behavior
- UI-01: diálogo de decisión de un paso (plantilla «Detalle con selección de líneas», §5) con «Aceptar todo» y CTA «Cobrar ahora».
- UI-02: diálogo de cobro compartido (patrón `purchase-payments-tab`, §5).
- UI-03: ficha del paciente con columnas de cobro y acción «Cobrar» (plantilla Detalle con tabla).
- UI-04: detalle de Cobros con navegación de regreso.
- UI-05: `app-status-badge` y menú plano. Estados (cargando/vacío/error/éxito), foco y móvil 390 px según DDR y §8.

## Non-functional requirements
Sin dependencias nuevas; sin HEX ni fuentes propias; la ficha del paciente hace una sola llamada adicional a Cobros por página de proformas; contraste ≥ 4.5:1 (claro y oscuro).

## Out of scope
Anulación o reversión de pagos; cobro automático al aceptar; cambios a las reglas de PB-COT-002/PB-COB-001; profesional por línea u honorarios; impresión de comprobante; migrar todos los badges del sistema; rediseño del paso de «Presentar» (solo texto más corto si cabe); nuevos reportes de cobranza.

## Open questions
Ninguna que bloquee.

# Test Specification

## Unit tests
- Frontend (`localToday`, `toCents/fromCents` existentes) + nuevos: función pura de **reparto automático** (INV-03), atajos Total/50 % (INV-04), precarga del que acepta (INV-05: menor con/sin responsable, mayor, sin fecha), componente `app-status-badge` (tono → clase/icono/texto).
- Backend: construcción de `CommitmentSnapshot` con `proforma_id` (`shared/domain/commitment.py`).

## Integration tests
- Backend (`receivables/tests/test_api.py`): el detalle incluye `proforma_id` = id de la versión vigente y cambia al presentar una versión nueva (genérica y dental).
- Frontend (`TestBed` + `HttpTestingController`): componente de decisión (un paso, Aceptar todo, motivo condicional, precarga, CTA tras éxito); diálogo de cobro (atajos, reparto automático, distribución avanzada, una confirmación, idempotencia, 409, error conserva datos); detalle de proforma (botón Cobrar abre diálogo, Cobrado/Saldo, módulo deshabilitado); ficha del paciente (columnas y acción, join, fallo parcial); detalle de Cobros (volver, «Paciente» en dental); menú (spec de `routes.json`).

## E2E
**NO** — el flujo se cubre con pruebas de componente y de API; no se instala Playwright. Revisión manual en navegador (escritorio y 390 px, claro y oscuro) en `delivery-publish`.

## Regression tests
Suites completas de frontend (`ng test`, `lint`, `build`, `i18n:check`) y de backend (`manage.py test`); en particular `proforma-decisions`, `dental-proforma-detail`, `patient-proformas`, `receivables` y `sidebar-menu`.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-02, AC-03 | Componente `proforma-decisions` + unit de precarga (INV-05) |
| AC-04 | Componente `proforma-decisions` (CTA) + detalle de proforma (abre diálogo) |
| AC-05, AC-06 | Unit del reparto/atajos + componente `payment-dialog` (payload, idempotencia, 409) |
| AC-07, AC-08 | Componentes de detalle de proforma (genérica y dental), con y sin módulo |
| AC-09 | Componente `patient-proformas` |
| AC-10 | Backend: `proforma_id` en API-01; componente `commitment-detail` |
| AC-11, AC-14, AC-15 | `i18n:check`, prueba de claves es/en/pt y specs de texto de los componentes |
| AC-12 | `sidebar-menu.spec.ts` |
| AC-13 | Unit de `app-status-badge` + revisión de contraste manual en `delivery-publish` |

# Implementation Plan

## Architecture considerations
Sin cambios de arquitectura. Los componentes nuevos van a `shared/` (patrón existente). Se mueven a `shared/` el modelo y el servicio de Cobros porque ahora los usan Odontología y Cotizaciones; `features/receivables` los importa desde allí. El módulo habilitado se consulta con `ModulesService.enabledKeys$`.

## Proposed solution
1. Backend: `proforma_id` en el snapshot, en ambas fachadas y en el serializer de detalle.
2. Frontend compartido: `shared/models/receivable.ts` y `shared/services/receivables-api.service.ts` (movidos), `shared/utils/payment-allocation.ts` (reparto y atajos), `shared/components/payment-dialog/`, `shared/components/status-badge/`.
3. `proforma-decisions`: diálogo de un paso, «Aceptar todo», precarga (input `defaultAcceptor`), CTA «Cobrar ahora» (input `collectible` + output `collect`), badges nuevos, etiquetas.
4. Detalles de proforma (genérica y dental): abren el diálogo, muestran Cobrado/Saldo y pasan `defaultAcceptor`; el dental carga el paciente para el responsable.
5. Ficha del paciente: columnas y acción con join a Cobros.
6. Cobros: botón de volver, diálogo compartido en lugar del panel, etiquetas; menú plano.
7. i18n, `design-system.md` y actualización de pruebas.

## Files/components affected
- Backend: `shared/domain/commitment.py`, `modules/quotations/services.py`, `modules/dentistry/services.py`, `modules/receivables/api/serializers.py`, `modules/receivables/tests/{test_api,test_domain}.py`.
- Frontend: `shared/components/{payment-dialog,status-badge,proforma-decisions}`, `shared/models/{receivable,proforma-decisions}.ts`, `shared/services/receivables-api.service.ts`, `shared/utils/payment-allocation.ts`, `features/dentistry/{pages/dental-proforma-detail,components/patient-proformas}`, `features/quotations/pages/proforma-detail`, `features/receivables/pages/{commitment-detail,obligation-list}`, `assets/data/routes.json`, `assets/i18n/{es,en,pt}.json`.
- Docs: `docs/design/design-system.md` (§3), DDR anteriores marcados «reemplazado parcialmente».

## Implementation steps
1. `proforma_id` en backend + pruebas (AC-10, API-01).
2. Mover modelo/servicio de Cobros a `shared/` y actualizar imports y specs (sin cambio de comportamiento).
3. `payment-allocation.ts` + unit tests (INV-03, INV-04).
4. `app-status-badge` + unit tests; etiquetas «Sin decidir/Por cobrar» en i18n (AC-11, AC-13).
5. `payment-dialog` + pruebas (AC-05, AC-06).
6. `proforma-decisions` de un paso, «Aceptar todo», precarga y CTA (AC-01..04, AC-14).
7. Detalles de proforma: diálogo, Cobrado/Saldo, gating por módulo (AC-07, AC-08).
8. Ficha del paciente: columnas y acción (AC-09).
9. Cobros: volver, diálogo compartido, «Paciente» en dental; menú plano (AC-10..12).
10. i18n es/en/pt, `design-system.md`, regresión completa y revisión manual.

## Database / migrations
Ninguna.

## Risks
Mover archivos compartidos (imports masivos); cambios de etiquetas que rompen specs; contraste del nuevo badge en tema oscuro (verificar en navegador); dependencia de un PR sin mergear.

## New dependencies
Ninguna.
