# TASK-registrar-gastos-cuenta-gasto-pago: Registrar gastos con cuenta de gasto y cuenta de pago en partida doble (GAS-01)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-registrar-gastos-cuenta-gasto-pago (base: `accounting`)
**Pull Request:** _sin abrir todavía_
**Fuente:** https://trello.com/c/w2fG3Xvu/5-gas-01-registrar-gastos-con-cuenta-de-gasto-y-cuenta-de-pago-en-partida-doble

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-17 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta GAS-01; base = rama `accounting` (indicación de la persona) | delivery-start |
| 2026-11-17 | INVESTIGATION → ARCHITECTURE → DESIGN → PLANNING | NEEDS_ARCHITECTURE: lógica financiera, frontera Gastos↔Contabilidad, migración, contrato API | delivery-start |
| 2026-11-17 | PLANNING → ENGINEERING | Specification READY (decisiones por defecto registradas en el PLAN); PLAN v1 | delivery-start |

## Investigación

### Requerimiento
Tarjeta Trello GAS-01 (insumo, no Specification aprobada). Aclaración de la persona: usar la rama `accounting` como base.

- **Objetivo:** adaptar Gastos al contrato contable de partida doble. La tarjeta estaba «En curso» con el modelo anterior (cuenta única + dirección): revisar lo existente y **no continuar** ese contrato.
- Mantener descripción, importe > 0, categoría, fecha, método, `supplier_name` y notas; el flujo representa un gasto **ya pagado**.
- Categoría → cuenta de Gastos (configuración); el gasto permite elegir una cuenta de gasto habilitada y una cuenta Caja/Banco de pago, con valor por defecto de la configuración.
- Confirmar genera Debe cuenta de Gasto / Haber Caja o Banco por el mismo importe, con vínculo al gasto, transacción atómica e idempotencia.
- No confundir categoría operativa con clasificación contable ni exigir proveedor formal.
- Un gasto contabilizado no admite editar monto, cuentas ni fecha; se corrige anulando y registrando de nuevo. Sin Contabilidad, el flujo operativo sigue independiente.
- **Aceptación:** (1) Alquiler 500 desde Banco → un gasto y asiento Debe Alquiler 500 / Haber Banco 500; (2) cuenta de gasto o de pago inválida, ajena o inactiva se rechaza y una falla contable no persiste el gasto; (3) reintentar no duplica gasto ni asiento y la categoría conserva historial al cambiar la configuración; (4) sin Contabilidad se registra sin exigir cuentas.
- **Dependencias:** CONT-12 (configuración de asientos automáticos) y CONT-10 (períodos fiscales), ambas ya en `accounting`. Transversal: API y UI, aislamiento por empresa, permisos existentes, `Decimal`, moneda existente (BOB), sin conversión de divisas.

### Hechos encontrados
- `backend/modules/accounting/domain/posting.py:81` — el evento `EXPENSE_RECORD` ya existe: Debe `EXPENSE_BY_CATEGORY` (cuenta de gasto por categoría, clase Gastos) / Haber `MONEY` (cuenta de Activo del método de pago). Nadie lo usa todavía.
- `backend/modules/accounting/services.py:520-565` — `post_automatic_entry` (idempotente por `(empresa, evento, origin_id)`, sin cobertura no crea nada, con cobertura y configuración incompleta lanza `PostingConfigurationMissing`, exige transacción abierta); `reverse_automatic_entry` (`:590-600`) y `check_posting_ready` (`:490-505`). **No admite elegir cuentas por operación**: siempre resuelve por rol/categoría/método (`accounting/application/posting.py:127-165`).
- `backend/modules/accounting/services.py:360-380` y `application/posting.py:213-222` — `set_category_account` y la API `PUT /accounting/posting-config/categories/<id>/` (`accounting/api/urls.py:67`) ya guardan categoría → cuenta de gasto (id opaco, sin verificar la categoría).
- `backend/modules/expenses/application/commands.py:30-60` — hoy un gasto con cobertura **exige una clasificación de egreso** en su categoría (`resolve_classification`, error `classification_not_configured`); es el contrato anterior (CONT-03/CONT-02), pero **ningún caso de uso de Gastos llama a `record_entry` ni a `post_automatic_entry`**: hoy un gasto no genera ningún movimiento contable.
- `backend/modules/expenses/domain/expense.py:38-110` — `Expense` solo valida y edita campos; `update` permite cambiar cualquier campo mientras no esté anulado; `void()` solo marca el estado. Sin `idempotency_key` ni referencia a cuentas/asiento.
- `backend/modules/expenses/api/views.py:61-84,123-140` — `_run` envuelve la mutación en `transaction.atomic`; errores de dominio → 400/404/409 (`{code, detail}`). `POST /expenses/` y `PATCH`/`void` son los puntos de integración.
- `backend/modules/expenses/infrastructure/django/models.py:36-62` y migraciones `0001–0003` — `ExpenseModel` sin campos de cuentas ni clave de idempotencia; `classification_id` instantánea nula en históricos.
- `backend/modules/expenses/infrastructure/adapters.py:14-35` — único lugar que conoce Contabilidad, solo vía `accounting.services`; `backend/modules/sales/infrastructure/adapters.py:237-275` es el patrón a seguir (post/reverse dentro de la transacción del comando).
- `backend/modules/sales/application/commands.py:263-285` — patrón de idempotencia por `idempotency_key` (UUID) con huella de datos y conflicto `idempotency_key_reused`.
- `backend/modules/accounting/domain/journal.py:24` — el motor rechaza un origen presente en el libro de Entradas anterior; Gastos nunca lo escribió, no hay conflicto.
- Frontend: `features/expenses/pages/expense-form`, `expense-detail`, `expense-list`, `expense-settings`; `features/accounting/components/posting-config-panel` y `expense-config-tab` (configuración); `classification-hint` compartido muestra la ayuda de clasificación en el formulario (`expense-form.component.ts:2,80`).
- `docs/design/design-system.md:111-198` — plantillas de Formulario, Detalle y «Panel de cuentas por evento con vista previa Debe/Haber».

### Hipótesis / supuestos no confirmados (resueltos por defecto en el PLAN)
- La clasificación de egreso deja de exigirse al registrar un gasto (la tarjeta pide no continuar el contrato anterior); el campo, la pantalla de clasificación y los datos históricos se conservan.
- Tras contabilizar, además de monto, cuentas y fecha, quedan bloqueados categoría y método de pago (determinan las cuentas por defecto); siguen editables descripción, proveedor y notas.
- La anulación de un gasto contabilizado revierte el asiento con fecha de hoy (debe caer en un período abierto).
- Con la cobertura ausente, las cuentas enviadas se ignoran y no se guardan.

### Módulos y dependencias relacionadas
`expenses` (dueño del gasto) → `accounting.services` (fachada). `accounting` no importa `expenses`. `reporting` no cambia (suma `amount` de gastos vigentes).

### Implementaciones similares existentes
Ventas (`SALE_PAYMENT`, `SALE_DELIVERY`): puerto en el módulo de origen + adaptador a `post_automatic_entry`/`reverse_automatic_entry`, idempotencia por clave y bloqueo de edición (`TASK-contabilizar-ventas-cobros-sin-duplicar`).

### Comportamiento actual
Un gasto se guarda con categoría y método de pago como texto; con Contabilidad cubriendo la fecha exige clasificación de egreso pero no genera movimiento ni asiento; se edita y anula libremente.

### Restricciones
`Decimal` para dinero; sin editar migraciones aplicadas (migración nueva); aislamiento por `company_id`; módulos solo por `services`; i18n es/en/pt sin texto hardcodeado; `models.py` sin FK entre módulos.

### Riesgos identificados
- Reintentos del POST sin clave duplican gastos: requiere clave de idempotencia (nuevo contrato).
- Anular con período cerrado impedirá la anulación (409): debe ser un mensaje accionable.
- Cambiar el requisito de clasificación altera un comportamiento ya publicado en `accounting`.
- `post_automatic_entry` necesita un contrato extendido (cuentas por operación) usado también por futuros eventos de Compras.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — dinero y partida doble, frontera Gastos↔Contabilidad con extensión del contrato público de `accounting.services`, migración en `expenses` y cambio de contrato API.

### Diseño requerido
**SI** — el formulario y el detalle de gasto ganan selección de cuentas, vista previa Debe/Haber y bloqueo de campos.

## Diseño
Ver `docs/design/DDR-registrar-gastos-cuenta-gasto-pago-formulario-y-detalle.md`.

## Arquitectura
Ver `docs/adr/ADR-registrar-gastos-cuenta-gasto-pago-puerto-asiento-y-bloqueo.md`.

## Plan
`docs/plans/PLAN-2026-11-17-registrar-gastos-cuenta-gasto-pago.md` (v1, COMPLETO). Specification readiness: READY.

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
