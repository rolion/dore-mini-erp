# ADR-incorporar-egresos-reversion-libro-direccion-operacion-y-reversion: Dirección, operación y reversión en el libro

**Estado:** Propuesto
**Task relacionado:** TASK-incorporar-egresos-reversion-libro
**Fecha:** 2026-11-15

## Contexto
El libro (`accounting_entry`) solo registra ingresos con unicidad `(empresa, origin_kind, origin_id)`. Gastos y Compras necesitan registrar salidas, y su anulación debe poder revertir el movimiento sin borrarlo. Los ingresos existentes deben seguir intactos.

## Decisión
1. **Dirección derivada del origen.** `catalog.ORIGIN_DIRECTION`: `PRODUCT`, `SERVICE` → `INCOME`; nuevos `EXPENSE` (gasto) y `PURCHASE_PAYMENT` (pago de compra) → `EXPENSE`. El llamante no envía la dirección; el dominio la deriva (no se puede registrar un gasto como ingreso). Se persiste en `direction` para consultar y sumar.
2. **Operación.** Nueva columna `operation` (`RECORD` | `REVERSAL`). La unicidad pasa a `(company_id, origin_kind, origin_id, operation)`: una entrada `RECORD` y como máximo una `REVERSAL` por origen. Es la «unicidad por empresa/origen/tipo de operación en base de datos».
3. **Reversión como movimiento nuevo e inmutable.** La reversión es otra fila con dirección opuesta a la del original, mismo monto, moneda y cuenta, `reverses` (OneToOne autorreferencia, `PROTECT`, único) apuntando al original y la fecha efectiva de la reversión. El original nunca se modifica. El efecto sobre el saldo de una cuenta es `+monto` para `INCOME` y `-monto` para `EXPENSE`, de modo que revertir restaura el saldo y una segunda reversión del mismo origen devuelve la existente (idempotente), sin duplicar.
4. **Clasificación.** `classification_id` (UUID, nullable, sin FK entre módulos de negocio; dentro de `accounting` es opcional). Obligatoria para `EXPENSE`/`PURCHASE_PAYMENT` y validada por la fachada (`validate_classification(..., 'EXPENSE')`); los ingresos existentes quedan sin ella. La reversión copia la clasificación del original (instantánea CONT-03: reclasificar no cambia movimientos).
5. **Fachada** (`accounting/services.py`): `EntryInput` gana `classification_id`; `record_entry` sigue siendo el único punto de inserción (en la transacción del llamante). Nuevas funciones: `reverse_entry(company_id, origin_kind, origin_id, reversal_date, recorded_by…) -> RecordedEntry` (exige transacción; bloquea la cuenta y el original; `EntryNotFound` si no hay original; permite cuentas inactivas porque restituye) y `account_balances(company_id, account_ids) -> dict` (saldo de apertura + Σ efectos; base de las pruebas de saldo y de CONT-04). No se expone endpoint de escritura: los movimientos automáticos no se editan ni se reversan desde la API.
6. **API de lectura** (aditiva): cada entrada incluye `direction`, `operation`, `classification {id,name}|null`, `reversal_of`/`reversed_by` (ids) y `origin.kind` amplía su catálogo; el filtro admite `direction`; `totals` por moneda conserva `count`/`amount`/`by_origin` como ingresos `RECORD` (compatibilidad) y añade `expense` y `by_direction` (`income`, `expense`, `reversed_income`, `reversed_expense`, `net`).
7. **Concurrencia.** Orden de bloqueo uniforme: cuenta (`select_for_update`) → inserción con punto de guardado; ante `IntegrityError` se devuelve la fila existente. `reverse_entry` además bloquea la fila del original.
8. **Migración `0006`:** agrega `direction` (default `INCOME`) y `operation` (default `RECORD`), `classification_id`, `reverses`; sustituye la restricción única; `CheckConstraint` coherencia (`REVERSAL` ⇒ `reverses` no nulo). Todo lo existente se rellena como `INCOME`/`RECORD` (correcto: eran todos ingresos).

## Alternativas consideradas
- **Monto con signo** (negativo para egresos): descartado, rompe `amount > 0` y los totales existentes.
- **Tabla separada de egresos**: duplica consultas, saldos y listado; descartado.
- **Reversión que marca el original como anulado (UPDATE)**: viola la inmutabilidad pedida; descartado.
- **Dirección enviada por el llamante**: permite incoherencias origen/dirección; descartado.

## Estrategia de rollback / mitigación
Migración aditiva más reemplazo de una restricción. Antes de desplegar: backup (ya lo hace el deploy). Reversa: `migrate accounting 0005` restaura la restricción antigua, válida mientras no existan filas `EXPENSE`/`REVERSAL` (el rollback debe ir antes de que Gastos/Compras empiecen a escribir; GAS-01/COM-01 se publican después). La migración inversa borra esas filas solo si el operador lo confirma; no se automatiza.

## Consecuencias
- La lista de Entradas y sus totales dejan de ser «solo ingresos»; el cambio es aditivo para clientes actuales.
- Habrá saldos calculables por cuenta; mostrarlos en UI es CONT-04.
- Compras y Gastos solo dependen de `accounting.services`.
