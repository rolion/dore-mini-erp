# ADR-numeracion-correlativa-pedidos-venta-contador-por-periodo: Contador de pedidos por empresa y período fiscal

**Estado:** Propuesto
**Task relacionado:** TASK-numeracion-correlativa-pedidos-venta
**Fecha:** 2026-11-25

## Contexto
Los pedidos solo se identifican por UUID y una etiqueta derivada. Se necesita un número correlativo por período fiscal (`NV-000001`), asignado al confirmar, sin duplicados bajo concurrencia, sin huecos por rollback, y que no se reutilice. El período fiscal vive en `accounting`; `sales` no puede importar su infraestructura (`docs/architecture/ddd.md`), pero ya usa su fachada pública (`sales/infrastructure/adapters.py:15`). Decisiones del usuario: sin período → bloquear; período cerrado → bloquear.

## Decisión
1. **Datos en `sales`.** `OrderModel` gana tres columnas nulas: `fiscal_period_id` (UUID, sin FK), `fiscal_period_name` (instantánea del nombre) y `number` (entero positivo). Restricción única parcial `(company_id, fiscal_period_id, number)` donde `number IS NOT NULL`: la base de datos es la última barrera contra duplicados. Tabla nueva `sales_order_number_counter` (`company_id`, `fiscal_period_id`, `last_number`, único por par).
2. **Dominio.** Objeto de valor `OrderNumber(period_id, period_name, number)`. `Order.start_preparation(number)` lo asigna una sola vez (inmutable: nunca se reasigna ni se borra, tampoco al cancelar). `Order.code` devuelve `NV-` + 6 dígitos si hay número, y la etiqueta provisional si no (pedidos NEW y heredados sin número).
3. **Puerto de aplicación `OrderNumbering`** (`sales/application/ports.py`) con `next_number(order_date) -> OrderNumber`; los casos de uso `StartOrderPreparation` y `PlaceOrder` lo invocan **dentro de su transacción**, justo antes de `start_preparation`. Errores de negocio de `sales` (`OrderRuleViolation`): `fiscal_period_missing` y `fiscal_period_closed`, mapeados a 409.
4. **Adaptador** en `sales/infrastructure/adapters.py`: llama a `accounting.services.lock_open_period(company_id, order_date)` (bloquea la fila del período, exige transacción, traduce `DateOutsideFiscalPeriod` y `FiscalPeriodClosed`) y luego incrementa el contador con `select_for_update`. El bloqueo del período serializa las confirmaciones del mismo período y además las serializa frente al cierre del período (un cierre en curso espera; después, la confirmación se rechaza como cerrada). El `get_or_create` inicial del contador queda dentro de ese bloqueo, así que no compite.
5. **Fecha que define el período:** `order_date` del pedido (no la fecha de confirmación). `order_date` es editable solo en NEW, por lo que no puede cambiar tras numerar.
6. **Migraciones:** `0006` (esquema, todo nulo) y `0007` (datos): numera los pedidos ya confirmados (estado ≠ NEW y ≠ CANCELLED) por empresa y período, en orden `created_at, id`, y deja `last_number` en el máximo asignado. Los pedidos fuera de cualquier período y los cancelados heredados quedan sin número. Los períodos cerrados sí se numeran (es histórico). `0007` depende de la migración de `accounting` que crea el período fiscal; es la única dependencia entre apps y es de solo lectura.
7. **No se extrae un contador compartido ahora.** Los contadores de `quotations` y `receivables` son por empresa, y este es por (empresa, período); unificarlos exigiría tocar y migrar dos módulos que funcionan. Se escribe el de ventas con forma elevable a `shared/numbering` para cuando `purchases` (`NC-`) sea el segundo consumidor del mismo molde; esa es la segunda task natural para extraerlo.
8. **Exposición:** el API añade `number` y `fiscal_period {id, name}`; `code` pasa a ser el número formateado cuando existe. El número no es único entre períodos: la identidad es `(empresa, período, número)` y la UI muestra el período junto al código.
9. **Asientos automáticos:** la descripción de la entrega pasa a `Entrega del pedido NV-000001 (2026)` para que el texto contable sea inequívoco entre períodos.

## Alternativas consideradas
- **Año calendario como serie**: descartada por el usuario (rango del período fiscal).
- **Serie de respaldo cuando no hay período**: descartada por el usuario (se bloquea).
- **Numerar al crear**: genera huecos con borradores; descartado.
- **Secuencia de PostgreSQL por período**: las secuencias no hacen rollback (huecos) y no hay un lugar claro para crearlas por período; descartado.
- **`MAX(number)+1` sin tabla de contador**: no serializa de forma fiable sin bloqueo explícito y es más lento; descartado.
- **Sin snapshot del nombre (consultar accounting al listar)**: acopla lecturas de listas a accounting y se rompe si accounting está deshabilitado o el período se renombra; descartado.
- **Extraer contador compartido ya**: ver decisión 7.

## Estrategia de rollback / mitigación
- Las migraciones son aditivas (columnas nulas y tabla nueva); revertir la versión del código deja las columnas sin uso, sin pérdida. `0007` es reversible como no-op (los números ya asignados no se vuelven a derivar).
- Antes del despliegue, el workflow ya hace backup de la base de datos (`docs/deployment/github-actions.md`); la migración de datos se prueba contra una base con pedidos en varios períodos y con pedidos fuera de período.
- Interruptor operativo: ninguno automático; el bloqueo por falta de período se resuelve creando el período en Contabilidad. El mensaje del 409 lo indica.
- Si algo falla al numerar dentro de la confirmación, toda la transacción se revierte (estado y número).

## Consecuencias
- Confirmar un pedido (también por importación de ventas) ahora exige un período fiscal abierto que contenga `order_date`. Las empresas sin período (por ejemplo, con Contabilidad deshabilitada y sin períodos creados) no podrán confirmar hasta crearlo; es decisión explícita del usuario.
- Importaciones de ventas con fechas fuera de período rechazan esas filas con el código `fiscal_period_missing` o `fiscal_period_closed`.
- `sales` queda acoplada a la fachada de `accounting` para confirmar (no a su infraestructura).
- Pedidos heredados sin número seguirán mostrando la etiqueta provisional; es deuda aceptada y visible.
- Las confirmaciones concurrentes de un mismo período se serializan (el costo es una espera de milisegundos por confirmación).
