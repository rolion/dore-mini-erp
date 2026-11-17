# ADR-registrar-gastos-cuenta-gasto-pago-puerto-asiento-y-bloqueo: Puerto de asiento de gastos, cuentas por operación e idempotencia

**Estado:** Propuesto
**Task relacionado:** TASK-registrar-gastos-cuenta-gasto-pago
**Fecha:** 2026-11-17

## Contexto
Gastos debe contabilizar con el evento `EXPENSE_RECORD` (Debe cuenta de gasto / Haber Caja-Banco) dentro de la misma transacción que guarda el gasto. La fachada actual resuelve las cuentas solo por configuración (categoría y método); la tarjeta pide poder elegirlas por gasto con valor por defecto. Además el POST de gastos no es idempotente y un gasto contabilizado no puede cambiar sus datos financieros.

## Decisión
1. **Fachada de Contabilidad (aditiva, retrocompatible):**
   - `post_automatic_entry(..., account_overrides: dict[str, UUID] | None = None)`: claves = códigos de rol (`EXPENSE_BY_CATEGORY`, `MONEY`). Cada cuenta se valida con `account_problem_info` contra el rol (empresa, activa, BOB, con código, clase correcta, clase habilitada); un problema se reporta como `PostingIssue` (`account_invalid`) y el comando lanza `PostingConfigurationMissing`. Sin override rige la configuración.
   - `validate_posting_account(company_id, role, account_id)` → `AccountRef` o `AccountValidationError`, para rechazar con error por campo antes de escribir.
   - `posting_options(company_id, event, accounting_date, method, category_id)` → cobertura, cuentas por defecto resueltas (o faltantes) y cuentas elegibles por rol, para el formulario. Solo lectura.
2. **Gastos (`expenses`):**
   - Puerto `ExpensePostingGateway` en `application/ports.py`; adaptador en `infrastructure/adapters.py` (único lugar que conoce Contabilidad). `CreateExpense` guarda el gasto y llama al puerto en la misma transacción; si Contabilidad lanza, la transacción revierte el gasto.
   - Campos nuevos en `ExpenseModel`: `expense_account_id`, `payment_account_id` (UUID sin FK, instantánea de las cuentas usadas; nulos si no se contabilizó) e `idempotency_key` (UUID nulo, único por empresa). El vínculo gasto↔asiento es `origin_kind=EXPENSE_RECORD`, `origin_id=expense.id` (sin duplicar el id del asiento).
   - Idempotencia: misma clave + misma huella (datos y cuentas) devuelve el gasto existente (200, `replayed`); misma clave con otros datos → 409 `idempotency_key_reused`. La unicidad en base cubre la concurrencia.
   - `Expense.is_posted` (derivado de `expense_account_id`): `update` rechaza monto, categoría, fecha, método y cuentas (`expense_posted_locked`); permite descripción, proveedor y notas.
   - `VoidExpense` llama a `reverse_automatic_entry` (fecha de hoy, motivo fijo) en la misma transacción; si el período está cerrado, falla con 409 y el gasto no se anula. Idempotente: anular dos veces no duplica la reversión.
   - La clasificación de egreso ya no se exige al registrar; se conserva el dato histórico y su pantalla.
3. **API:** `POST /api/expenses/` acepta `expense_account_id`, `payment_account_id` e `idempotency_key` opcionales; `GET /api/expenses/posting-options/` (solo lectura) alimenta el formulario; el detalle expone `posted`, `expense_account`, `payment_account` y `journal_entry_id`.

## Alternativas consideradas
- **Guardar `journal_entry_id` en el gasto:** duplica el vínculo ya garantizado por `origin_id`; descartada.
- **Cuentas solo por configuración:** no cumple la tarjeta (elegir cuenta por gasto); descartada.
- **Llamar a Contabilidad desde la vista:** rompe capas; descartada.
- **Idempotencia solo por huella sin clave:** dos gastos legítimos idénticos serían indistinguibles; descartada.
- **Permitir editar monto y reversar/reasentar:** más estados y riesgo; la tarjeta pide anular y registrar de nuevo.

## Estrategia de rollback / mitigación
Migración aditiva (columnas nulas + índice único parcial): revertible con la migración inversa sin pérdida de gastos. Mientras no haya cobertura o configuración, la conducta no cambia (gastos sin asiento). Si falla en producción, deshabilitar Contabilidad en la empresa devuelve el flujo operativo anterior. Los asientos ya creados solo se revierten por anulación.

## Consecuencias
Compras (COM-01) reutiliza `account_overrides` y `posting_options`. Los gastos anteriores no tienen cuentas ni asiento; son anulables sin reversión. Un asiento de gasto nunca se edita: la corrección es anular y recapturar.
