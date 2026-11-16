# TASK-diagnostico-transicion-partida-doble: Diagnóstico y contrato de transición de accounting a partida doble (CONT-07)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** NO
**Rama:** task/TASK-diagnostico-transicion-partida-doble (base: `accounting`)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/78
**Fuente:** https://trello.com/c/uVkvCkVl

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-16 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta CONT-07 | delivery-start |
| 2026-11-16 | INVESTIGATION → ARCHITECTURE | Transición de datos financieros con migraciones y varios módulos | delivery-start |
| 2026-11-16 | ARCHITECTURE → PLANNING | ADR escrito (DDR no aplica: sin pantallas) | delivery-start |
| 2026-11-16 | PLANNING → ENGINEERING | Specification READY | delivery-start |
| 2026-11-16 | ENGINEERING → REVIEW | Implementación completa | delivery-build |
| 2026-11-16 | REVIEW (sin cambio) | Quality Gate sin PASS: REV-01 abierto (verificación no ejecutable aquí) | delivery-publish |
| 2026-11-16 | REVIEW → PUBLISH | REV-01 cerrado con el ensayo en copia; Quality Gate PASS | delivery-publish |

## Investigación

### Requerimiento
Fuente: tarjeta Trello CONT-07 (insumo, no Specification aprobada). La tarjeta indica trabajar sobre la rama `accounting` (lo hecho en CONT-01/03/06 y CONT-02 no está en `main`) y **no mergear a `main`**; las tareas previas del mismo hilo usaron `accounting` como base de PR (PR #77 tiene `baseRefName=accounting`).

Objetivo: definir y ejecutar una transición reproducible al modelo de partida doble sin perder datos. Comportamiento esperado de la tarjeta:
- Comparar `accounting` con `main` e inventariar commits, modelos, migraciones, seeds y datos afectados.
- Revisar `django_migrations`, el esquema real y los datos locales; distinguir registros de prueba de los que deben conservarse; respaldar antes de transformar.
- No borrar migraciones aplicadas, no `--fake`, no reiniciar la base por defecto; preferir migraciones incrementales; toda limpieza destructiva requiere decisión explícita del dueño.
- Documentar el mapeo anterior → nuevo: cuenta de dinero → cuenta de Activo; conceptos de ingreso/egreso → cuentas contables apropiadas (las clasificaciones anteriores no equivalen a las seis nuevas).
- Los movimientos de una sola cuenta requieren contrapartida verificable; no inventar ingresos, patrimonio ni deudas; registrar pendientes y bloquear su conversión.
- Establecer corte, saldos iniciales mediante asiento balanceado, conservación de referencias y exclusión del doble cómputo.
- Entregar procedimiento de migración/recuperación y resultado de conciliación.

Pruebas de aceptación de la tarjeta: (1) base nueva desde `main` aplica la cadena final sin errores; (2) copia de la base local se actualiza y conserva referencias y montos conciliados; (3) reejecutar la conversión no duplica cuentas ni asientos; (4) un registro sin contrapartida se informa y no se convierte en silencio.

Ejecución por etapas (de la tarjeta): primero diagnóstico y contrato de transición; después la migración, cuando el esquema destino exista. CONT-08 (seis clasificaciones), CONT-09 (cuentas con código/clasificación) y siguientes **dependen de esta tarjeta**: el esquema destino aún no existe. CONT-13 valida el resultado integrado.

Alcance acordado para esta tarea (**Etapa 1**): diagnóstico, contrato de transición, herramienta de diagnóstico de solo lectura, procedimiento de respaldo/recuperación y resultado de conciliación. La conversión (**Etapa 2**) queda con su contrato y criterios definidos, y se ejecuta cuando exista el esquema destino.

### Hechos encontrados
**Comparación `accounting` vs `main`** (`git rev-list --left-right --count main...origin/accounting` = `0 29`; `main` no tiene nada que `accounting` no tenga):
- 29 commits: CONT-01 (#74 cuentas de dinero y clasificaciones), CONT-06 (#75 corte, apertura, cobertura), CONT-03 (#76 clasificación de egreso en Gastos/Compras), CONT-02 (#77 egresos y reversión en el libro). 170 archivos; backend: 69 archivos (+3085/−121).
- Migraciones nuevas, todas aditivas (ninguna borra ni renombra): `accounting/0004_account_kind_classification`, `0005_coverage_settings_opening_balance`, `0006_entry_direction_operation_reversal`, `expenses/0003_classification`, `purchases/0008_payment_classification`.
- Excepción en `accounting/0006`: **quita** `accounting_entry_origin_uniq` (company, origin_kind, origin_id) y agrega `accounting_entry_origin_op_uniq` (… + `operation`) y `accounting_entry_reversal_link` (`migrations/0006_entry_direction_operation_reversal.py`).
- No hay seeds ni fixtures de `accounting` (búsqueda en el repo); las cuentas y clasificaciones las crea cada empresa por API.

**Modelo actual** (`backend/modules/accounting/infrastructure/django/models.py` en `accounting`):
- `AccountModel` (`accounting_account`): `name`, `currency`, `is_active`, `kind` (CASH/BANK/WALLET, **nullable**), `opening_balance` (≥ 0), único por nombre sin mayúsculas por empresa. **No tiene código ni clasificación contable.**
- `ClassificationModel` (`accounting_classification`): `name`, `direction` INCOME/EXPENSE — es «por qué se mueve el dinero», **no** una de las seis clasificaciones nuevas.
- `EntryModel` (`accounting_entry`): movimiento de una sola cuenta: `account` (FK PROTECT), `amount > 0`, `direction`, `operation` RECORD/REVERSAL, `reverses` (uno a uno), `classification_id`, `origin_kind` (PRODUCT, SERVICE, EXPENSE, PURCHASE_PAYMENT), `origin_id`, referencias de documento/recibo/autor, `regularized_*`. Único `(company, origin_kind, origin_id, operation)`. Solo se inserta.
- `SettingsModel` (`accounting_settings`, `cutoff_date` por empresa), `CoveragePeriodModel`, `MethodMappingModel` (método de pago → cuenta).
- Contrato ya fijado de corte/apertura (`docs/adr/ADR-modularidad-corte-historicos-contabilidad-ciclo-de-vida-y-corte.md`, decisiones 4-5): saldo = `opening_balance + movimientos con fecha ≥ corte`; lo anterior al corte es histórico y no suma. `account_balances` (`services.py:235`) lo implementa; `coverage_status` (`services.py:113`) decide la cobertura.
- Los orígenes de los movimientos viven en otros módulos por UUID sin FK: `sales_payment`, `receivables_payment`, `expenses_expense`, `purchases_payment` (esta última y `expenses_expense` ya con `classification_id`, hoy siempre `NULL`).
- Reglas de datos: `docs/deployment/activar-accounting.md` ya documenta la regularización de pagos históricos (`regularize_ledger`, `management/commands/regularize_ledger.py`) como herramienta de **solo agregar**, idempotente y con mapeo explícito sin cuenta por defecto: es el patrón a seguir.

**Base local inspeccionada (solo lectura, sin `--fake`, sin transformar nada)** — PostgreSQL `doredb` en `localhost` (nombres de empresa y personas omitidos a propósito):
- `django_migrations` (`accounting`): **0001–0006 ya aplicadas** (0001–0003 el 2026-11-14; 0004–0005 el 2026-11-15; 0006 el 2026-11-16). `expenses` 0001–0003, `purchases` 0001–0008, `sales` 0001–0003, `receivables` 0001, `modularity` 0001–0002 aplicadas. No hay migraciones aplicadas ausentes del código de `accounting`; el esquema real coincide con los modelos (columnas `kind`, `opening_balance`, `direction`, `operation`, `reverses_id`, `classification_id`; tablas `accounting_classification`, `_settings`, `_coverage_period` presentes). Con el código de `main` esa base no arranca coherente (faltan 0004–0006): **la tarea debe verificarse con el código de `accounting`**.
- Datos: 21 empresas (`accounts_company`); 9 cuentas en 5 empresas (3 con `kind`, 6 con `kind` nulo; 1 CASH, 2 BANK; todas BOB y activas); suma de `opening_balance` 1 000,50 repartida en cuentas **sin** movimientos; 9 mapeos método→cuenta (todos activos y con cuenta); 5 clasificaciones en 2 empresas; 2 empresas con `accounting_settings` (cortes 2026-10-30 y 2026-11-15) y un periodo de cobertura abierto cada una.
- `accounting_entry`: **32 filas**, todas `INCOME / RECORD`, sin `classification_id`, sin reversiones; 16 PRODUCT (510,00 + 445,50 + 513,00 = 1 468,50) y 16 SERVICE (850 + 1 400 + 550 + 180 = 2 980,00); total 4 448,50 BOB; 19 son regularizadas; fechas de pago 2026-03-10 a 2026-11-15; ninguna anterior al corte de su empresa.
- Conciliación contra los orígenes: `sales_payment` 27 pagos = 2 554,00; `receivables_payment` 26 pagos = 3 970,00. **11** pagos de ventas (1 085,50) y **10** de cobros (990,00) **no tienen entrada**; **0 entradas huérfanas** (todas apuntan a un pago existente) y 0 entradas con cuenta de otra empresa.
- `purchases_payment`: 12 pagos = 818,50 (3 empresas) y `expenses_expense`: 1 gasto = 270,00, todos **sin movimiento** y sin clasificación (anteriores a CONT-02/03; coherente con «sin cobertura → sin movimiento»).
- 3 de las 5 empresas con entradas **no tienen `accounting_settings`** (sin fecha de corte): 19 de las 32 entradas.
- Lo que ya es dato para decidir: ninguna cuenta con saldo de apertura tiene movimientos; no hay reversiones ni egresos en el libro.

### Hipótesis / supuestos no confirmados
- Los 21 pagos sin entrada corresponden a empresas con Contabilidad deshabilitada o a pagos anteriores a su habilitación/regularización; **no está confirmado** (la regularización decide qué se crea). La herramienta de diagnóstico debe explicarlo por pago.
- Qué empresas y registros locales son de prueba (21 empresas, una con el UUID reservado `…0001`, que parece sembrada) **es decisión del dueño**; la tarea no borra nada.
- La contrapartida de un cobro puede ser Ingreso o, si el pago es un anticipo, Pasivo; el repositorio no distingue anticipo de pago final en el libro. **Decisión de negocio abierta, no bloqueante** (ver ADR): sin mapeo explícito el movimiento queda pendiente.
- El destino del saldo de apertura (cuenta de Patrimonio) y los códigos de las cuentas de dinero son decisiones del dueño; sin ellas, pendiente.

### Módulos y dependencias relacionadas
`accounting` (dueño), lectura de `sales`, `receivables`, `expenses`, `purchases` por sus fachadas/puertos (`accounting/infrastructure/adapters.py` ya lee `sales` y `receivables`). Dependencias permitidas: `sales/tests/test_boundaries.py:13,24-25`. `modularity` no importa módulos de negocio (`shared/module_lifecycle.py`).

### Implementaciones similares existentes
`regularize_ledger` (`management/commands/regularize_ledger.py`, `domain/regularization.py`, `application/regularize.py`, `application/regularization_summary.py`): vista previa sin escribir, `--apply` explícito, mapeo JSON sin valores por defecto, resumen agrupado, exit code ante errores. El diagnóstico y la futura conversión se modelan igual.

### Comportamiento actual
Un movimiento es una línea de una sola cuenta; no existen asiento, debe/haber, código de cuenta ni las seis clasificaciones. La cuenta de dinero existe pero no se distingue de una «cuenta contable».

### Restricciones
`CLAUDE.md`: nunca editar una migración aplicada; `Decimal` para dinero; aislamiento por `company_id`; no tocar `.env`; avisar antes de instalar dependencias; los módulos de negocio no importan `accounts`. Tarjeta: no `--fake`, no reiniciar la base, no borrar migraciones, sin limpieza destructiva sin decisión del dueño, no mergear a `main`.

### Riesgos identificados
- Convertir ingresos «por defecto» a la cuenta Ingresos podría registrar como ingreso un anticipo (pasivo) o un cobro de otra naturaleza.
- La saldo de apertura convertida dos veces (apertura + movimientos anteriores al corte) duplicaría el cómputo.
- 3 empresas con entradas sin corte: sin fecha de corte no se puede decidir qué es histórico.
- La conversión sobre la base compartida de producción sin ensayo previo en copia.
- `0006` ya reemplazó una restricción única: la conversión debe apoyarse en `(company, origin_kind, origin_id, operation)`.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — transición de datos financieros con impacto en varios módulos, contrato de datos y estrategia de rollback (ADR obligatorio).

### Diseño requerido
**NO** — comando de gestión y documentos; sin pantallas nuevas.

## Diseño
No aplica (sin UI).

## Arquitectura
`docs/adr/ADR-diagnostico-transicion-partida-doble-estrategia-y-contrato.md`.

## Plan
`docs/plans/PLAN-2026-11-16-diagnostico-transicion-partida-doble.md` (v1) · Modo: COMPLETO · Specification readiness: READY.

## Implementación
Comando `diagnose_ledger_transition` de solo lectura (AC-01..AC-06, INV-01..INV-06): dominio `domain/transition.py` (clasificación y mapeo), caso de uso `application/transition_diagnosis.py`, lector `DjangoTransitionReader` en `infrastructure/adapters.py` y comando en `management/commands/`. Documento `docs/deployment/transicion-partida-doble.md` (AC-07). Sin migraciones.

**Desviaciones del plan:** (1) Gastos y Compras no se leen por fachada: `sales/tests/test_boundaries.py` hace que `expenses`/`purchases` dependan de `accounting` y no al revés. Las entradas de egreso quedan `pendiente/origen_no_verificable` (sin entradas de egreso locales) y el puerto de verificación se deja para la Etapa 2. (2) El ensayo en copia restaurada de la base local (parte de AC-08) se ejecutó tras la implementación (ver `## Review`).

**Verificación propia:** 15 pruebas de `test_transition_diagnosis` en verde (7 unitarias del dominio y 8 de integración del comando); regresión `modules.accounting` + `test_boundaries`: 181 pruebas OK; `makemigrations --check`: sin cambios. La creación de la base de pruebas aplicó la cadena completa de migraciones desde cero (aceptación 1 de la tarjeta). El ensayo con `pg_dump`/`pg_restore` en copia (aceptación 2, AC-08) se ejecutó después: ver `## Review`.

**Deuda técnica:** puerto de verificación de egresos (Etapa 2).

## Review
**Resultado: PASS.** Quality Gate ejecutado por quien implementó, con aislamiento procedimental (revisión solo desde artefactos y diff `origin/accounting...HEAD`, 9 archivos, todos dentro del plan).
- Pruebas: `test_transition_diagnosis` 15/15 OK; regresión `modules.accounting` + `test_boundaries` 181/181 OK; `makemigrations --check`: sin cambios.
- Seguridad: `bandit` sin hallazgos en los 4 archivos nuevos/modificados; sin secretos en el diff (`backend/.env` está ignorado por git).
- No realizado: `ruff`/`flake8`/`mypy` (no instalados ni configurados); cobertura de backend (sin `coverage.py`; se revisó a mano que cada regla de `classify_entry`, `classify_opening` y `parse_transition_mapping` tiene prueba); frontend no aplica (no hay cambios).
- Límites DDD: `domain/transition.py` sin Django; toda consulta del lector filtra por `company_id` (`company_ids()` es la única global, de solo lectura y necesaria para recorrer empresas); sin imports de infraestructura de otros módulos.
- Hallazgo [REV-2026-11-16-diagnostico-transicion-partida-doble-01](../reviews/REV-2026-11-16-diagnostico-transicion-partida-doble-01.md) (Medium): **cerrado**; el ensayo `pg_dump` → `pg_restore` → `migrate` en copia se ejecutó con éxito (diagnóstico idéntico antes y después).
- Limitación conocida (Low): el diagnóstico sin `--company` solo recorre empresas con datos de Contabilidad; una empresa con pagos y sin datos se consulta con `--company`.

## Publicación
PR #78 (base `accounting`) listo para aprobación humana; no se mergea. Cambio sensible: toca el contrato de datos de la transición contable (ADR `ADR-diagnostico-transicion-partida-doble-estrategia-y-contrato`), aunque esta etapa solo lee datos. La copia `doredb_copia` y el volcado quedan en la máquina local para el ensayo.
