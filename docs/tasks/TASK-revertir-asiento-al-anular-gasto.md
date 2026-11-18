# TASK-revertir-asiento-al-anular-gasto: Revertir el asiento completo al anular un gasto (GAS-02)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** NO
**Rama:** task/TASK-revertir-asiento-al-anular-gasto (base: `accounting`)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/92
**Fuente:** https://trello.com/c/NymyeXFY/6-gas-02-revertir-todas-las-l%C3%ADneas-del-asiento-al-anular-un-gasto

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-18 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta GAS-02; base = rama `accounting` (indicación de la persona; la rama de trabajo se actualizó a `origin/accounting`, commit `de1abd4`) | delivery-start |
| 2026-11-18 | INVESTIGATION → PLANNING | NEEDS_PLAN: GAS-01 ya implementó la reversión; quedan brechas acotadas (usuario, módulo deshabilitado, pruebas de AC, vínculo a la reversión) | delivery-start |
| 2026-11-18 | PLANNING → ENGINEERING | Specification READY; PLAN v1 | delivery-start |
| 2026-11-18 | ENGINEERING → REVIEW | Implementación según PLAN v1; pruebas propias en verde (backend y frontend) | delivery-build |
| 2026-11-18 | REVIEW → PUBLISH | Quality Gate sin Critical/High; todas las pruebas pasan; revisión visual no verificada; REV-01..02 (Low) abiertos | delivery-publish |

## Investigación

### Requerimiento
Tarjeta Trello GAS-02 (insumo, no Specification aprobada). Aclaración de la persona: usar la rama `accounting` como base.

- **Objetivo:** conservar la anulación lógica del gasto y neutralizar su asiento con partida doble.
- Anular un gasto contabilizado crea **una sola** reversión: Debe Caja/Banco original, Haber Gasto original, por los importes originales. Usa el motor CONT-02; mantiene asiento original, vínculo, motivo, usuario y fecha; no consulta la configuración nueva para cuentas históricas.
- Anulación y reversión son atómicas; reintentos concurrentes se deduplican.
- Se permiten cuentas originales deshabilitadas; la fecha de la reversión cae en un período abierto explícito y no se modifica un período cerrado.
- Un gasto histórico sin asiento no genera reversión ficticia. No se deben perder correcciones al deshabilitar Contabilidad (reglas de modularidad).
- **Aceptación:** (1) anular gasto Banco 200 → Debe Banco 200 / Haber Gasto 200 y saldos originales neutralizados; (2) dos anulaciones concurrentes → una sola reversión, un fallo revierte la anulación; (3) la reversión conserva la cuenta original aunque cambie la configuración o esté deshabilitada; (4) gasto anterior al corte sin asiento no altera saldos, período cerrado no se reescribe.
- **Dependencias:** GAS-01, CONT-02, CONT-10 (todas ya en `accounting`). Transversal: API y UI donde corresponda, aislamiento por empresa, permisos existentes, `Decimal`, moneda existente.

### Hechos encontrados
- `backend/modules/expenses/application/commands.py:140-155` — `VoidExpense` bloquea el gasto (`get_for_update`), llama `expense.void(...)`, y si `is_posted` invoca `posting.reverse(expense.id)` y luego guarda; la vista lo corre en `transaction.atomic` (`api/views.py:72-95,212-217`). Anulación y reversión ya son atómicas y dos anulaciones se serializan por el bloqueo de fila.
- `backend/modules/expenses/infrastructure/adapters.py:106-111` — `AccountingPosting.reverse` llama `accounting.reverse_automatic_entry(company_id, EXPENSE_RECORD, expense_id, timezone.localdate(), VOID_REASON)`. **No pasa `created_by` / `created_by_name`**: la reversión no registra qué usuario anuló. El motivo es el texto fijo `'Anulación de gasto'` (`adapters.py:15`).
- `backend/modules/expenses/application/ports.py:59-61` — el puerto `reverse(expense_id)` no recibe al actor.
- `backend/modules/accounting/services.py:686-697` — `reverse_automatic_entry` busca el asiento original por `(evento, origen)`; sin asiento devuelve `None` (no hay reversión ficticia); no consulta la configuración ni la cobertura actuales; delega en `reverse_journal_entry`.
- `backend/modules/accounting/services.py:434-448` y `domain/journal.py:183-194` — `reverse_journal_entry` invierte **todas** las líneas con las cuentas originales (`line.inverted()`), vincula `reverses_id`, exige motivo, es idempotente (devuelve la existente con `created=False`), exige fecha en período abierto (`lock_open_period`), permite cuentas deshabilitadas y no modifica el original. No importa si el período del original está cerrado.
- `backend/modules/accounting/domain/journal.py:186-187` — una reversión no se puede revertir.
- `backend/modules/accounting/infrastructure/lifecycle.py:11-22` — `DjangoOutflowLedger.open_count()` sigue devolviendo `0` ("CONT-02 lo reemplaza"): deshabilitar Contabilidad **no** se bloquea con egresos contabilizados sin revertir (ADR modularidad, decisión 6). Como `reverse_automatic_entry` no consulta el módulo ni la cobertura, la reversión debería seguir funcionando con Contabilidad deshabilitada, pero **no hay prueba que lo demuestre**.
- `backend/modules/expenses/tests/test_posting_api.py:175-200` — pruebas existentes: anular contabilizado crea una reversión (solo cuenta filas), repetir → 409, período cerrado → 409 y el gasto sigue activo, anular sin asiento (empresa sin Contabilidad) no crea reversión. `test_posting_application.py:145-157` cubre el fallo del puerto. **No hay**: aserción de líneas/importes/saldos de la reversión, concurrencia de dos anulaciones, cuentas originales tras cambiar configuración o desactivar la cuenta, anulación con Contabilidad deshabilitada, gasto anterior al corte con Contabilidad habilitada, ni usuario/fecha/motivo de la reversión.
- `backend/modules/expenses/tests/test_posting_concurrency.py` — patrón `TransactionTestCase` + `_run_together` reutilizable para la concurrencia de anulaciones.
- `backend/modules/expenses/api/views.py:128-134` y `api/serializers.py:129-132` — el detalle expone `journal_entry_id` (asiento original) pero no la reversión; `JournalEntryRef.reversed_by_id` (`accounting/services.py:385-386`) ya la entrega.
- `frontend/panel_admin/src/app/features/expenses/pages/expense-detail/expense-detail.component.html:48-49,65-81` — el detalle muestra el enlace «Ver asiento» y la fecha de anulación, pero no enlaza la reversión.

### Hipótesis / supuestos no confirmados (resueltos por defecto en el PLAN)
- El **motivo** de la reversión es el texto fijo existente (`Anulación de gasto`); el API de anulación no gana un campo `reason` (no es contrato nuevo ni lo pide la tarjeta explícitamente).
- La **fecha** de la reversión es la fecha local de hoy (decisión ya tomada en GAS-01); si hoy no cae en un período abierto, la anulación falla con 409 accionable y no se reescribe el período del original.
- El **usuario** de la reversión es la persona autenticada que anula (`created_by`, `created_by_name`).
- Con Contabilidad deshabilitada, anular un gasto que tiene asiento **sí** revierte el asiento (la corrección no se pierde); la decisión depende de que exista el asiento, no de la cobertura vigente.

### Módulos y dependencias relacionadas
`expenses` → `accounting.services` (fachada). Sin cambios en `accounting` salvo, si hiciera falta, una prueba de contrato. `reporting` no cambia.

### Implementaciones similares existentes
Reversión de cobros en Ventas (`sales/infrastructure/adapters.py:237-275`) y `ReverseJournalEntry`.

### Comportamiento actual
Anular un gasto contabilizado ya crea la reversión completa en la misma transacción; falta registrar al usuario, probar el comportamiento exigido por la tarjeta (saldos, concurrencia, cuentas históricas, módulo deshabilitado, corte) y enlazar la reversión en el detalle.

### Restricciones
`Decimal`; sin migración (no hay datos nuevos en `expenses`); aislamiento por `company_id`; módulos solo por `services`; i18n es/en/pt; no se edita código de GAS-01 más allá de lo necesario.

### Riesgos identificados
- Si la prueba de «Contabilidad deshabilitada» falla, habrá que decidir dónde ubicar la corrección (la fachada de `accounting`); se corrige en la fachada, sin duplicar reglas en `expenses`.
- Cambiar la firma del puerto `reverse` afecta a los dobles de prueba existentes.

### Veredicto de complejidad
**NEEDS_PLAN** — cambio acotado sobre una arquitectura ya decidida (ADR de GAS-01): un argumento más en el puerto, un campo aditivo en el detalle y pruebas. Toca dinero, por eso el PLAN es COMPLETO.

### Diseño requerido
**NO** — solo se añade un enlace «Ver reversión» dentro de la sección «Asiento contable» ya diseñada en `DDR-registrar-gastos-cuenta-gasto-pago-formulario-y-detalle`, con el mismo patrón que «Ver asiento». Sin pantallas ni flujos nuevos.

## Diseño
No aplica (ver arriba).

## Arquitectura
No aplica según veredicto; se sigue `ADR-registrar-gastos-cuenta-gasto-pago-puerto-asiento-y-bloqueo`.

## Plan
`docs/plans/PLAN-2026-11-18-revertir-asiento-al-anular-gasto.md` (v1, COMPLETO). Specification readiness: READY.

## Implementación
Resumen: la anulación ya revertía el asiento completo (GAS-01); se cierran las brechas de la tarjeta.

- **Actor en la reversión** (INV-04, AC-05): `ExpensePostingGateway.reverse(expense_id, actor_id, actor_name)`, `VoidExpense.execute(..., actor_id, actor_name)`, `AccountingPosting.reverse` reenvía `created_by`/`created_by_name` a `reverse_automatic_entry`; la vista toma al usuario autenticado.
- **`reversal_entry_id`** (API-01/02, AC-07): `AccountingPosting.entry_ids` devuelve `(asiento, reversión)` (reemplaza `entry_id`, sin otros usos); campo aditivo en el detalle y la respuesta de void.
- **Frontend** (UI-01): `reversalEntryId` en modelo/servicio/fixture, enlace «Ver reversión» (`data-testid="reversal-link"`) junto a «Ver asiento», claves `VER_REVERSION` es/en/pt. Pantalla de referencia: Detalle existente; sin componentes nuevos.
- **Pruebas escritas:** `expenses/tests/test_voiding_api.py` (AC-01, 03, 04, 05, 06, 07, 08, EDGE-03), `test_voiding_concurrency.py` (AC-02), ajuste de `test_posting_application.py` (actor), specs del detalle y del servicio.

Desviaciones: ninguna. No fue necesario tocar `accounting`: AC-04 (corte y período cerrado) y AC-06 (Contabilidad deshabilitada) pasan con la fachada actual. Un ajuste de pruebas: `reversal_entry_id` se añadió al conjunto de claves de `test_api.py`, y la prueba de período cerrado fija un corte anterior (el corte por defecto es hoy).

**Verificación propia (no es el Quality Gate), sobre la rama fusionada con `accounting` (2026-11-18):** backend completo `Ran 2222 tests ... OK`; `makemigrations --check`: No changes detected; frontend `1664 specs, 0 failures`, `npm run lint` sin errores, `npm run build` OK, `i18n:check` 2260 claves, 0 faltantes. Revisión visual en navegador: no realizada.

Deuda técnica: el `DjangoOutflowLedger.open_count()` sigue devolviendo 0, por lo que deshabilitar Contabilidad no se bloquea con egresos sin revertir (ADR modularidad, decisión 6); fuera de alcance.

## Review
**Quality Gate: PASS con reservas** (subagente aislado, 2026-11-18). Sin hallazgos Critical/High; abiertos REV-2026-11-18-revertir-asiento-al-anular-gasto-01 (Low: EDGE-01/EDGE-02 sin prueba dedicada) y -02 (Low: código residual en `test_voiding_api.py`).

Evidencia: backend `Ran 2222 tests ... OK`; `makemigrations --check`: No changes detected; `bandit -r modules`: 0 High, 0 Medium, 23 Low preexistentes, ninguno en el diff; frontend `TOTAL: 1664 SUCCESS` (cobertura líneas 88,91 %); `npm run lint` sin errores; `npm run build` OK; `i18n:check` 2260 claves, 0 faltantes; `npm audit --omit=dev`: 0 vulnerabilidades. Todos los AC (01..09), INV e invariantes verificados con aserciones reales; sin scope creep (20 archivos, todos del plan), sin secretos, límites DDD respetados. Revisión visual en navegador: **no verificada**.

## Publicación
PR #92 listo para aprobación humana (no se mergea); base `accounting`, no `main`. Sin cambios sensibles de base de datos (sin migración), autenticación ni infraestructura; no hay ADR nuevo.
