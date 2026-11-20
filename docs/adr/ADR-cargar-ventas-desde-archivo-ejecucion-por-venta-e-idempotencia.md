# ADR-cargar-ventas-desde-archivo-ejecucion-por-venta-e-idempotencia: Transacción por venta, idempotencia y vista previa sin escritura

**Estado:** Propuesto
**Task relacionado:** TASK-cargar-ventas-desde-archivo
**Fecha:** 2026-11-19

## Contexto
Una venta importada toca varios módulos (cliente, producto, proveedor, compra, stock, pedido, cobro, asientos, costo). El usuario eligió: vista previa antes de cargar, carga **por venta** (todo o nada por venta, sin detener el resto) y que reintentar el mismo archivo **no duplique**. Los hechos de `DeliverOrder`/`RegisterReception` (transacción del llamador, bloqueos por pedido/compra) y la política de cobertura contable (`SalesPostingAdapter`) condicionan el diseño.

## Decisión
1. **Etapas persistidas** (tablas propias de `data_import`):
   - `ImportRun` (empresa, tipo `SALES`, nombre y SHA-256 del archivo, cabeceras, filas crudas normalizadas como JSON, mapeo, opciones, estado `UPLOADED → PREVIEWED → RUNNING → COMPLETED|FAILED`, contadores, usuario, fechas).
   - `ImportRowResult` (run, n.º de fila, clave de venta, estado `CREATED | SKIPPED_DUPLICATE | FAILED | CREATED_WITHOUT_POSTING`, código y mensaje, ids creados: `order_id`, `purchase_ids`, `product_ids`, `customer_id`, sin FKs a otros módulos).
   - `ImportedSale` (empresa, `source_key` único por empresa → `order_id`): garantía de idempotencia.
2. **Vista previa = misma validación sin escribir**: reutiliza las reglas de dominio de cada fila (fechas, cantidades, importes, método) y consulta —solo lectura— existencia de productos/clientes, saldos de stock proyectados en orden cronológico, costo disponible, cobertura contable por fecha, duplicados y módulos habilitados. El servidor **revalida al ejecutar**; la vista previa es informativa (el estado puede cambiar entre ambas).
3. **Ejecución**: se agrupan filas en ventas (por «n.º de venta» mapeado; sin esa columna, una fila = una venta), se ordenan por fecha y orden de archivo y cada venta corre en `transaction.atomic()` propia: cliente → productos → (si inferir inventario) proveedor + compra recibida por el faltante → pedido entregado → cobro total. Un error de dominio hace rollback **solo de esa venta** (incluye lo creado dentro: productos, clientes, compra) y queda en `ImportRowResult` con mensaje accionable; el resto continúa.
4. **Idempotencia**: `source_key` = `n:<n.º de venta>` si hay columna; si no, `h:<sha256 del contenido normalizado de la fila>:<ocurrencia>`. Antes de cada venta se consulta `ImportedSale`; si existe, se marca `SKIPPED_DUPLICATE`. La restricción única protege carreras (el `IntegrityError` de una venta concurrente se traduce a duplicada). Ejecutar de nuevo un `ImportRun` ya `COMPLETED` devuelve su resultado guardado sin escribir.
5. **Concurrencia**: un `ImportRun` en `RUNNING` rechaza otra ejecución (409 `import_running`); la empresa solo puede tener una ejecución activa a la vez (bloqueo transaccional sobre una fila de control por empresa), para no competir por stock y costo promedio.
6. **Fechas históricas y cobertura**: la fecha de la venta rige pedido, entrega y cobro; la compra inferida se recibe en la misma fecha (nunca futura; las fechas futuras se rechazan). Con fecha sin cobertura contable la venta se carga y se etiqueta `CREATED_WITHOUT_POSTING` con aviso; los errores accionables de cobertura/cuentas/costo del motor existente (`inventory_cost_unavailable`, `payment_method_without_account`, etc.) se traducen a mensajes por fila, sin ocultarlos.
7. **Compras inferidas**: solo por el faltante de stock del almacén elegido en el momento de la venta (saldo real + compras ya inferidas del propio archivo en orden cronológico); costo = columna de costo o, si falta, el costo promedio vigente; si no hay ninguno y hay cobertura, error de fila. Quedan **sin pago**.
8. **Límites y seguridad**: 5 MB, 2 000 filas, un solo archivo, primera hoja; se descartan fórmulas (se leen valores), se limpian espacios y caracteres de control y se acotan las longitudes; los textos que empiezan por `= + - @` se guardan tal cual en la base pero se escapan al exportar (no hay exportación en este alcance). Ejecución síncrona dentro de la petición.

## Alternativas consideradas
- **Todo en una sola transacción:** consistente pero una fila mala bloquea todo y mantiene bloqueos largos; contradice la elección del usuario. Descartada.
- **Cola de trabajos asíncrona (Celery):** más escalable, pero no existe infraestructura en el stack y es una dependencia grande. Se difiere; el límite de filas acota el riesgo.
- **Idempotencia solo por hash del archivo:** un archivo corregido y vuelto a subir duplicaría ventas. Descartada a favor de la clave por venta.
- **Vista previa que simula dentro de una transacción con rollback:** reutiliza el código real, pero ejecuta asientos, bloqueos y costos solo para descartarlos. Descartada por costo y riesgo.

## Estrategia de rollback / mitigación
- Migración nueva solo de tablas propias (reversible con `migrate data_import zero`); no toca tablas de otros módulos.
- Si una ejecución falla a mitad, lo ya cargado queda correcto por venta (consistente) y `ImportedSale` evita duplicados al reintentar el mismo archivo; las ventas fallidas se corrigen y se vuelve a subir.
- Sin reversa en bloque (fuera de alcance); los ids guardados por fila permiten construirla después.

## Consecuencias
- Filas crudas guardadas en base (hasta 5 MB por corrida): se documenta política de retención y no se guardan datos sensibles distintos de los del archivo.
- Una venta es la unidad atómica: un pedido con varias líneas no se carga parcialmente.
- La coincidencia de productos/clientes por nombre normalizado (minúsculas, sin tildes, espacios colapsados) puede equivocarse con homónimos; se muestra en la vista previa cuántos se crean y cuántos se reutilizan.
