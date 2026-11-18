# TASK-registrar-gastos-cuenta-gasto-pago: Registrar gastos con cuenta de gasto y cuenta de pago en partida doble (GAS-01)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-registrar-gastos-cuenta-gasto-pago (base: `accounting`)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/90
**Fuente:** https://trello.com/c/w2fG3Xvu/5-gas-01-registrar-gastos-con-cuenta-de-gasto-y-cuenta-de-pago-en-partida-doble

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-17 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta GAS-01; base = rama `accounting` (indicación de la persona) | delivery-start |
| 2026-11-17 | INVESTIGATION → ARCHITECTURE → DESIGN → PLANNING | NEEDS_ARCHITECTURE: lógica financiera, frontera Gastos↔Contabilidad, migración, contrato API | delivery-start |
| 2026-11-17 | PLANNING → ENGINEERING | Specification READY (decisiones por defecto registradas en el PLAN); PLAN v1 | delivery-start |
| 2026-11-17 | ENGINEERING → REVIEW | Implementación completa según PLAN v1; pruebas propias en verde | delivery-build |
| 2026-11-17 | REVIEW → PUBLISH | Quality Gate sin Critical/High; todas las pruebas pasan; revisión visual no verificada; REV-01..04 abiertos | delivery-publish |
| 2026-11-17 | PUBLISH (corrección) | REV-01..04 resueltos a pedido de la persona; PLAN v2 (INV-03 aprobado por la persona) | delivery-build |

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
`docs/plans/PLAN-2026-11-17-registrar-gastos-cuenta-gasto-pago.md` (v2, COMPLETO). Specification readiness: READY.

## Implementación
Resumen: un gasto con Contabilidad cubriendo su fecha se contabiliza en la misma transacción con el evento `EXPENSE_RECORD` (Debe cuenta de gasto / Haber Caja-Banco), con cuentas por defecto o elegidas, idempotencia y bloqueo posterior; sin cobertura el flujo operativo no cambia.

- **Accounting** (`services.py`, `application/posting.py`, `domain/posting.py`): `post_automatic_entry(account_overrides=…)`, `validate_posting_account`, `posting_options`, `describe_accounts`; la cuenta de pago elegida debe ser de dinero (Caja/Banco/Billetera) — INV-03, EDGE-01..03, AC-02, AC-07.
- **Expenses dominio/persistencia**: `Expense.is_posted`, bloqueo de monto/categoría/fecha/método (`expense_posted_locked`), `same_submission`; migración `0004` (cuentas, `idempotency_key`, índice único parcial por empresa) — INV-05, INV-04, AC-08.
- **Expenses aplicación/infraestructura**: puerto `ExpensePostingGateway` y adaptador `AccountingPosting` (traduce errores contables); `CreateExpense` (guarda, contabiliza, idempotente incluso ante carrera), `VoidExpense` (revierte el asiento en la misma transacción), clasificación de egreso ya no exigida — INV-01, INV-02, INV-06, INV-07, AC-01, AC-03..06, AC-09, AC-10.
- **API**: `POST /expenses/` con `expense_account_id`, `payment_account_id`, `idempotency_key` (200 `replayed` en reintento); `GET /expenses/posting-options/`; gasto con `posted`, `expense_account`, `payment_account`, `journal_entry_id`; errores 400 `posting_configuration_missing` y 409 de período — API-01..04, AC-11.
- **Frontend**: bloque «Contabilidad» con cuentas por defecto/elegibles y vista previa Debe/Haber, avisos accionables (textos traducidos con `issueText`), clave de idempotencia por formulario, campos bloqueados al editar un gasto contabilizado, sección «Asiento contable» en el detalle con enlace al asiento; i18n es/en/pt — UI-01..03, AC-12.
- **Pruebas**: `accounting/tests/test_posting_overrides.py`, `expenses/tests/test_posting_api.py` (BD y Contabilidad reales), `test_posting_application.py`, ajuste de pruebas de clasificación; specs del formulario, detalle y servicio. Corridas propias: backend completo 2067 OK; frontend 1601 OK; `ng lint` e `i18n:check` OK; `makemigrations --check` sin cambios (no es el Quality Gate).

Desviaciones respecto al plan:
- La cuenta de pago exige además que sea de dinero (Caja/Banco/Billetera, `kind` informado), no cualquier Activo: la tarjeta pide «Caja/Banco» y evitaría pagar con, por ejemplo, Cuentas por cobrar.
- Se añadió `describe_accounts` (fachada de solo lectura) para mostrar código y nombre de las cuentas sin importar infraestructura de Contabilidad.
- Los faltantes de configuración se envían con `module`, `params` y `problem` para reutilizar `issueText` y traducirlos.
- Se eliminaron `ExpenseClassificationError` y sus códigos (ya sin uso).
- Concurrencia: cubierta con prueba de aplicación que simula la carrera (la restricción única y el punto de guardado en el repositorio la resuelven); no hay `TransactionTestCase` multihilo.

Correcciones posteriores al Quality Gate (REV-01..04, resueltos; el Gate no se repitió): prueba multihilo `expenses/tests/test_posting_concurrency.py` (REV-01); INV-03/AC-02 del PLAN v2 y ADR actualizados a «cuenta de dinero» (REV-02); `payment_method` de `posting-options` acotado a 20 caracteres y prueba de aislamiento de categoría ajena (REV-03); el formulario renueva la clave de idempotencia cuando cambian los datos entre intentos (REV-04). Esto elimina la desviación «sin TransactionTestCase multihilo».

Deuda técnica: la pantalla y el endpoint de clasificación de egreso de la categoría se conservan sin uso en el alta (candidatos a retiro en otra tarea). Revisión visual en navegador: no realizada en esta etapa.

UI: pantallas de referencia seguidas = Formulario (`product-form`) y Detalle; sin componentes compartidos nuevos (se reutilizan `MoneyPipe`, ng-select y `issueText` de Contabilidad).


## Review
**Quality Gate: PASS con reservas** (subagente aislado, 2026-11-17). Sin hallazgos Critical/High; abiertos REV-2026-11-17-registrar-gastos-cuenta-gasto-pago-01 (Medium: falta la prueba multihilo de AC-04; la sonda manual con dos hilos dio 1 gasto y 1 asiento), -02 (Low: INV-03/ADR dicen «clase Activo» y el código exige cuenta de dinero), -03 (Low: `payment_method` de posting-options sin límite de longitud) y -04 (Low: la clave de idempotencia del formulario no se renueva tras editar y reintentar un alta ya aceptada).

Nota: el subagente emitió FAIL únicamente por la revisión visual no ejecutada; el procedimiento del proyecto exige marcarla «no verificada» (nunca aprobada), no bloquear.

Evidencia: backend `Ran 2067 tests ... OK`; `makemigrations --check`: No changes detected; frontend `TOTAL: 1601 SUCCESS` (cobertura líneas 88,89 %); `ng lint` sin errores; `i18n:check` 2197 claves, 0 faltantes; `npm run build` OK; bandit sin hallazgos; `npm audit --omit=dev`: 3 high preexistentes (picomatch, tinyglobby, @angular/localize; el diff no toca `package.json`). Revisión visual en navegador: verificada a mano por la persona el 2026-11-17 (flujo de escritorio: registrar un alquiler, detalle «Contabilizado», enlace al asiento, campos bloqueados al editar y reversión al anular); **no verificados** móvil ni tema oscuro.

## Publicación
PR #90 listo para aprobación humana (no se mergea). Cambio sensible: **base de datos** (migración `expenses/0004`) y contrato de `accounting.services`; respaldo: ADR-registrar-gastos-cuenta-gasto-pago-puerto-asiento-y-bloqueo (migración aditiva y reversible). Hacer backup antes de desplegar (el deploy ya lo hace); la base del PR es `accounting`, no `main`.

