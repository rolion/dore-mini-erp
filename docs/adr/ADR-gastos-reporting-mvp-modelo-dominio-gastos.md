# ADR-gastos-reporting-mvp-modelo-dominio-gastos: Módulo Expenses: agregados, reglas, anulación lógica y persistencia

**Estado:** Propuesto
**Task relacionado:** TASK-gastos-reporting-mvp
**Fecha:** 2026-10-09

## Contexto
`expenses` no existe. `ddd.md:571-662` define `Expense` y `ExpenseCategory`, pero contiene `receipt_url`, `ExpenseType`, "cierre contable" y un `DeleteExpense` que ningún REQ-EXP pide o que contradice REQ-EXP-004 (anulación lógica). El usuario confirmó en esta etapa: **anulación lógica, irreversible, sin motivo**. El patrón de módulo es el de `customers`/`sales` (`domain/ application/ infrastructure/django/ api/`, errores de dominio acumulados por campo, UUID como PK, `db_table` explícita, bloqueo de fila con `get_for_update`, ver [ADR-ciclo-pedido-entrega-cobro-persistencia-consistencia](ADR-ciclo-pedido-entrega-cobro-persistencia-consistencia.md)). En `main` ya existe `backend/shared/domain/money.py` (`parse_money`, `MONEY_MAX`, `InvalidMoney`: `Decimal` 2 decimales, rechaza `float`/`bool`).

## Decisión

**Dos agregados, ambos en `modules/expenses/domain/`, sin imports de Django:**

- **`ExpenseCategory`** (`category.py`): `id`, `name`, `active`, `created_at`, `updated_at`. `create(name)`, `rename(name)`, `activate()`, `deactivate()` (idempotentes, como en Customers). Nombre obligatorio, recortado, máx. 100 caracteres. **El nombre es único sin distinguir mayúsculas** (p. ej. "Empaque" y "empaque" son la misma categoría): evita duplicados en los reportes por categoría; lo comprueba la capa `application` con el repositorio y lo respalda una restricción única en BD.
- **`Expense`** (`expense.py`): `id`, `description`, `amount` (`Decimal`), `category_id`, `expense_date`, `payment_method`, `supplier_name`, `notes`, `status` (`ExpenseStatus`: `ACTIVE`, `VOIDED`), `voided_at`, `created_at`, `updated_at`. Métodos: `Expense.create(...)`, `update(...)` (campos opcionales con `UNSET`, patrón de `Order.update_details`) y **`void(now)`**. El estado cambia solo por `void()`, nunca por asignación.

**Reglas (todas en el agregado, errores acumulados por campo en `ExpenseValidationError`):**
- `description` obligatoria, recortada, máx. 200; `amount` obligatorio, `> 0` y `parse_money` de `shared` (≤ `MONEY_MAX`); `expense_date` obligatoria y sin restricción de rango (se permiten fechas pasadas; una fecha futura no está prohibida por ningún REQ); `category_id` obligatorio; `supplier_name` opcional máx. 150; `notes` opcional máx. 2000.
- **`payment_method`** es un enum propio de Expenses (`CASH, QR, BANK_TRANSFER, CARD, OTHER`, mismos códigos que `sales/domain/enums.py:PaymentMethod`; no se importa Sales: el límite de módulos lo prohíbe y son cinco constantes). **Opcional en la entrada, por omisión `CASH`**, así el dato siempre existe y el detalle puede mostrarlo (REQ-EXP-007) sin estado "sin método".
- **Anulación (REQ-EXP-004):** `void(now)` pasa `ACTIVE → VOIDED` y fija `voided_at`. Es **irreversible**, **sin motivo**. Anular un gasto ya anulado es una violación de regla (`ExpenseRuleViolation('already_voided')` → 409). Un gasto `VOIDED` **no se puede editar** (`ExpenseRuleViolation('expense_voided')`). **No hay borrado físico** de gastos ni de categorías.
- **Categoría de un gasto (reglas de aplicación, porque cruzan dos agregados del mismo módulo):** al crear, la categoría debe existir y estar **activa** (REQ-EXP-006). Al editar, se permite conservar la categoría actual aunque esté inactiva; cambiar a otra categoría exige que sea activa. Una categoría inexistente → error en el campo `category_id`.
- Desactivar una categoría **no** afecta a sus gastos (REQ-EXP-006). Reactivarla la devuelve a la lista de opciones.

**Capa `application`:** un caso de uso por clase con `execute`, como en Customers/Sales: `CreateExpense`, `UpdateExpense`, `VoidExpense`, `GetExpense`, `ListExpenses`, `CreateExpenseCategory`, `RenameExpenseCategory` (edita el nombre), `ActivateExpenseCategory`, `DeactivateExpenseCategory`, `GetExpenseCategory`, `ListExpenseCategories`. Los nombres `ListExpensesByDateRange`/`ByCategory` de `ddd.md` se resuelven como **filtros** de `ListExpenses` (igual que Sales con `OrderFilters`). Puerto `Clock` para `void(now)`/`today` (mismo patrón que `sales/application/ports.py`). `ExpenseFilters` (`date_from`, `date_to`, `category_id`, `status`) y `ExpenseSummary` viven en `domain/repositories.py`.

**Persistencia (`infrastructure/django/`, migración `0001_initial` nueva):**
- `expenses_category`: `id` UUID PK, `name` `CharField(100)`, `active` `BooleanField` (indexado), `created_at`, `updated_at`; `UniqueConstraint(Lower('name'), name='expenses_category_name_ci_unique')`; `ordering = ['name', 'id']`.
- `expenses_expense`: `id` UUID PK; `category` FK → `expenses_category` con **`on_delete=PROTECT`** (FK dentro del mismo módulo; impide el borrado físico de una categoría con gastos, REQ-EXP-006); `description`, `amount` `DecimalField(12,2)`, `expense_date` `DateField` (indexado), `payment_method` `CharField(20)`, `supplier_name` `CharField(150, blank)`, `notes` `TextField(blank)`, `status` `CharField(10)` (indexado), `voided_at` `DateTimeField` nulo, `created_at`, `updated_at`; `CheckConstraint(amount > 0)`; `ordering = ['-expense_date', '-created_at', 'id']`.
- Repositorios con `get`, `get_for_update`, `save`, `list(filters)` (lista perezosa paginable); `update` y `void` corren en `transaction.atomic()` abierta por `api` y cargan con `get_for_update` (sin bloqueo optimista, igual que Sales).
- **No se persisten** `receipt_url` ni `ExpenseType`: no están en ningún REQ; añadirlos después es una migración aditiva.
- Una sola migración generada con `makemigrations`; `modules.expenses` en `INSTALLED_APPS`.

**Fachada para otros módulos:** `modules/expenses/services.py` (ver [ADR-gastos-reporting-mvp-lectura-entre-modulos](ADR-gastos-reporting-mvp-lectura-entre-modulos.md)). Expenses no importa a ningún otro módulo.

## Alternativas consideradas
- **`DELETE /api/expenses/{id}` con borrado físico (`ddd.md:648,966`):** contradice la regla "preferir anulación lógica" y rompería la trazabilidad; descartado y se corrige `ddd.md`.
- **Anulación reversible o con motivo:** el usuario eligió irreversible y sin motivo; menos estados y menos fricción. Es aditivo si luego se pide.
- **Un solo agregado `Expense` con la categoría embebida:** impediría gestionar categorías (REQ-EXP-006) y renombrar sin tocar gastos.
- **Compartir `PaymentMethod` con Sales vía `shared/`:** acopla dos módulos por una enumeración de 5 valores que puede divergir (los gastos podrían querer "débito automático"); duplicar es más barato que el acoplamiento.
- **`payment_method` obligatorio sin valor por omisión / opcional sin valor:** el primero fuerza una elección que el REQ no exige; el segundo obliga a manejar "sin método" en UI y reportes. Se eligió default `CASH`.
- **Estado derivado de `voided_at` sin columna `status`:** una columna de estado indexada filtra con claridad y permite añadir estados; `voided_at` nulo/no nulo duplicaría la verdad. Se guarda `status` y `voided_at`.
- **Unicidad del nombre de categoría solo en la UI / no exigida:** dos "Empaque" repartirían un mismo concepto entre dos filas del reporte (REQ-REP-004). Se exige sin distinguir mayúsculas.

## Estrategia de rollback / mitigación
- **Migración aditiva:** `0001_initial` solo crea `expenses_category` y `expenses_expense`; no toca tablas existentes y es reversible (`python manage.py migrate expenses zero`). Respaldar la base antes de aplicarla con datos reales.
- **Rollback de código:** revertir el PR. Si ya hay gastos reales, no ejecutar `migrate expenses zero` (destruye los datos): basta quitar el `include` de rutas y mantener las tablas.
- **Mitigación:** `CheckConstraint(amount > 0)` y `PROTECT` frente a estados absurdos; las reglas siguen en el dominio.
- Nunca editar `0001` una vez aplicada (regla de `CLAUDE.md`).

## Consecuencias
- Queda fácil: cumplir REQ-EXP-001 a 007 con el patrón ya probado; que los reportes excluyan anulados con un solo filtro (`status = ACTIVE`).
- Queda más difícil: nada irreversible; un gasto anulado por error obliga a registrar uno nuevo.
- Deuda aceptada: `PaymentMethod` duplicado entre Sales y Expenses; `receipt_url`/`ExpenseType`/cierre contable diferidos; la restricción única por `Lower(name)` requiere cuidado con el collation si se cambia de motor.
- `ddd.md` debe actualizarse (sección 7 y endpoints) para reflejar anulación lógica y la ausencia de `DELETE`.
