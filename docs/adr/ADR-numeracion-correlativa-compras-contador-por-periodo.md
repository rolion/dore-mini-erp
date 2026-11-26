# ADR-numeracion-correlativa-compras-contador-por-periodo: Contador de compras por empresa y período fiscal

**Estado:** Propuesto
**Task relacionado:** TASK-numeracion-correlativa-compras
**Fecha:** 2026-11-26

## Contexto
Las compras solo se identifican por UUID y una etiqueta provisional `COM-XXXXXXXX`. Se necesita la misma numeración que ya existe para ventas (ADR `ADR-numeracion-correlativa-pedidos-venta-contador-por-periodo`, mergeado): `NC-000001` por empresa y período fiscal, asignado al confirmar, sin duplicados ni huecos, con bloqueo cuando no hay período abierto. Este ADR **no reabre** las decisiones del de ventas; solo fija cómo se aplican a `purchases` y resuelve lo que cambia.

## Decisión
1. **Mismo diseño que ventas, módulo propio.** `PurchaseModel` gana `fiscal_period_id` (UUID, sin FK), `fiscal_period_name` (instantánea) y `number`, con restricción única parcial `(company_id, fiscal_period_id, number)` y dos CHECK (número > 0; número y período van juntos). Tabla `purchases_purchase_number_counter` (`company_id` indexado, `fiscal_period_id`, `last_number`, único por par). Dominio: `PurchaseNumber(period_id, period_name, number)` con `code` = `NC-` + 6 dígitos; `Purchase.number`; `confirm(now, number, supplier_active)` lo asigna una sola vez (inmutable, también al cancelar). `Purchase.reference` devuelve el código si hay número y, si no, la etiqueta provisional `COM-XXXXXXXX` (borradores y heredados sin número).
2. **Puerto `PurchaseNumbering`** (`purchases/application/ports.py`) usado por `ConfirmPurchase`, dentro de su transacción y **después** de validar que la compra es confirmable (`Purchase.ensure_confirmable()`, nuevo, con las mismas validaciones que hoy hace `confirm`: borrador, proveedor activo, ≥1 ítem), para no consumir números en confirmaciones inválidas. La confirmación repetida sobre una compra ya confirmada sigue siendo idempotente y **no** numera (devuelve el número existente).
3. **Adaptador `PurchaseNumberingAdapter`** (`purchases/infrastructure/adapters.py`): `accounting.services.lock_open_period(company_id, purchase_date)` + contador con `select_for_update`; traduce `DateOutsideFiscalPeriod` y `FiscalPeriodClosed` a la excepción de dominio `PurchaseNumberingRejected(code, message, extra)` (`fiscal_period_missing` / `fiscal_period_closed`; `extra={'period': nombre}` en el cerrado), que la API traduce a 409 `{code, detail, period?}` y la importación a `ImportRejected(code)`. El período lo define `purchase_date` (editable solo en borrador).
4. **Todos los caminos que confirman numeran:** la API y `import_received_purchase` (compra inferida).
5. **Búsqueda de la lista:** además de `external_reference` y del prefijo hex del id (`com-…`/hex, vigente para borradores y heredados), acepta `NC-000012` o `12` (número), para encontrar por el nuevo código.
6. **Asientos contables:** las descripciones de recepción, pago/anticipo y recepción revertida usan `purchase.reference` (ya `NC-…`) seguido de ` (período)` cuando hay número, igual que la entrega de ventas.
7. **Migraciones:** `purchases/0010` (esquema, todo nulo) y `0011` (datos): numera las compras con `confirmed_at` no nulo (confirmadas y **canceladas que llegaron a confirmarse**) por empresa y período que contiene `purchase_date`, en orden `confirmed_at, created_at, id`; deja `last_number` en el máximo; borradores, canceladas sin confirmar y fechas fuera de período quedan sin número. Los períodos cerrados sí se numeran (histórico). Repetible. `0011` depende de `('accounting', '0009_fiscal_period')` y solo lee tres columnas del período.
8. **No se extrae un contador compartido.** Dos consumidores sí tienen la misma forma, pero lo compartible son ~15 líneas (bloquear período, incrementar contador); lo demás (objeto de valor, excepciones, repositorio, serialización, migraciones, mensajes) es propio de cada agregado. Extraerlo exigiría refactorizar código de ventas ya mergeado y en producción, con una migración de datos para mover la tabla del contador o un modelo compartido nuevo, a cambio de ahorrar poco: riesgo mayor que beneficio, y `CLAUDE.md` pide no añadir abstracciones sin necesidad real. Se duplica el patrón, con la misma forma exacta para que una extracción futura sea mecánica; se revisa cuando aparezca un tercer consumidor.
9. **Componente de UI compartido:** `app-fiscal-period-alert` se mueve de `features/sales/components` a `shared/components/fiscal-period-alert` (segundo módulo que lo usa; regla del sistema de diseño de no copiarlo), con la misma API (`code`, `periodName`). Cambia solo imports y ubicación en ventas; sin cambio de comportamiento.

## Alternativas consideradas
- **Contador compartido en `shared/` ya:** ver decisión 8.
- **Numerar también al reabrir o al cambiar fecha:** innecesario, la fecha no cambia tras confirmar.
- **Copiar el componente de alerta en `purchases`:** duplicaría UI; descartado.
- **Numerar solo las confirmadas vivas (no las canceladas confirmadas):** contradice la regla «las canceladas conservan su número».

## Estrategia de rollback / mitigación
- Migraciones aditivas (columnas nulas, tabla nueva); revertir el código deja las columnas sin uso, sin pérdida. `0011` es reversible como no-op.
- El despliegue ya hace backup antes de `migrate`; `0010`/`0011` se prueban contra una base con compras en varios períodos, canceladas confirmadas, borradores y fechas fuera de período, y se recomienda probarlas contra una copia de producción antes del merge.
- Todo ocurre en la transacción de la confirmación: un fallo revierte estado y número.
- El bloqueo por falta de período se resuelve creando o reabriendo el período en Contabilidad; el 409 lo indica.

## Consecuencias
- Confirmar una compra (también por importación) exige un período fiscal abierto que contenga `purchase_date`: empresas sin período o con Contabilidad deshabilitada y sin períodos no podrán confirmar (misma decisión que ventas).
- La importación de ventas con compras inferidas con fecha sin período/cerrada rechaza esa fila con el código del período.
- Compras heredadas con fecha fuera de todo período siguen con la etiqueta provisional `COM-…`; deuda aceptada y visible.
- Quedan dos implementaciones del contador con la misma forma (deuda controlada, ver decisión 8).
