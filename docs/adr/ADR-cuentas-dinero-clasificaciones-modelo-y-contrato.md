# ADR-cuentas-dinero-clasificaciones-modelo-y-contrato: Tipo de cuenta y catálogo de clasificaciones en Contabilidad

**Estado:** Propuesto
**Task relacionado:** TASK-cuentas-dinero-clasificaciones
**Fecha:** 2026-11-15

## Contexto
Hoy `accounting` tiene cuentas (`accounting_account`), mapeo método → cuenta y entradas inmutables; no hay tipo de cuenta ni clasificación. `expenses` tiene `ExpenseCategory`, que equivale a una clasificación de egreso pero vive aparte. La tarjeta CONT-01 pide separar tres conceptos y reutilizar Contabilidad sin alterar ingresos existentes.

**Equivalencia del modelo actual con el contrato**

| Concepto del contrato | Modelo actual | Acción |
|---|---|---|
| Cuenta de dinero (Caja/Banco/Billetera) | `AccountModel` (nombre, moneda, activo); sin tipo; sin restricción de dirección | Se reutiliza; se añade `kind` anulable |
| Método de pago | `MethodMappingModel` + códigos de `catalog.py` | Sin cambios |
| Clasificación de ingreso | Implícita en `EntryModel.origin_kind` (PRODUCT/SERVICE) | Nuevo catálogo; el enlace con entradas queda para tareas siguientes |
| Clasificación de egreso | `expenses.ExpenseCategory` | No se migra aquí; coexiste hasta una tarea posterior |
| Histórico | `EntryModel` con FK `PROTECT` a cuenta | Intacto |

## Decisión
1. **Cuenta:** columna nueva `kind` (`CASH`/`BANK`/`WALLET`, anulable) en `accounting_account`. Las cuentas existentes quedan con `kind` nulo. Obligatorio al crear (API y dominio); `PATCH` puede asignarlo. Ninguna regla restringe la dirección: la misma cuenta sirve a cobros y pagos.
2. **Clasificación:** tabla nueva `accounting_classification` (`id`, `company_id` UUID sin FK, `name` ≤80, `direction` `INCOME`/`EXPENSE`, `is_active`, marcas de tiempo). Único `(company_id, lower(name), direction)`. Agregado `Classification` en dominio puro con `create/rename/activate/deactivate`; la dirección no cambia tras crearla (cambiarla alteraría el significado de lo ya clasificado).
3. **API** bajo `/api/accounting/`: `classifications/` (GET con `?direction=` y `?active=`, POST), `classifications/<id>/` (GET, PATCH solo nombre), `…/activate/` y `…/deactivate/`; `accounts/` incorpora `kind` (alta obligatoria, lectura nullable). Mismos permisos y gate que la configuración actual (`CompanyAdminPermission`, `required_modules = ()`).
4. **Fachada** `accounting.services`: `validate_money_account(company_id, account_id)` y `validate_classification(company_id, classification_id, direction)` devuelven un DTO inmutable o lanzan `AccountValidationError` si no existe en la empresa, está inactiva o la dirección no coincide. Es el punto que usarán egresos y compras; nada importa infraestructura de `accounting`.
5. **Desactivar** impide usos nuevos (las validaciones la rechazan) y no toca registros previos: no hay borrado ni cascada. Las cuentas mantienen la regla vigente de bloqueo si métodos activos la usan.
6. `EntryModel` y `record_entry` no cambian: saldos y referencias de ingresos existentes quedan intactos.

## Alternativas consideradas
- **Unificar `ExpenseCategory` ahora** moviéndola a `accounting`: toca otro módulo, sus FK y datos de producción; fuera del alcance acotado de esta tarea.
- **`kind` obligatorio con backfill (p. ej. todo «Banco»):** inventaría un dato de negocio; se prefiere nulo.
- **Una sola tabla de «categorías» con `kind` de cuenta y clasificación:** mezcla conceptos que la tarjeta pide separar.
- **Clasificación con FK desde `EntryModel` ya:** modifica la tabla inmutable; se pospone hasta que haya un consumidor.

## Estrategia de rollback / mitigación
Migración `0004` aditiva (una columna anulable y una tabla nueva), sin tocar filas existentes. Rollback: `migrate accounting 0003` elimina ambas; ningún otro módulo depende de ellas aún. El API sigue aceptando clientes que no envían `kind` en `PATCH`; el alta pasa a exigirlo (único cambio no retrocompatible, aceptado porque el único cliente es el panel, que se actualiza en el mismo PR).

## Consecuencias
- Dos catálogos de egresos conviven (`ExpenseCategory` y clasificaciones `EXPENSE`) hasta la tarea que los una.
- Cuentas antiguas sin tipo se muestran como «Sin tipo» y se piden completar al editarlas.
- Las tareas de egresos tendrán un contrato de validación listo y probado.
