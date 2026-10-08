# ADR-ciclo-pedido-entrega-cobro-persistencia-consistencia: Tablas de Sales, valores derivados persistidos y control de concurrencia

**Estado:** Propuesto
**Task relacionado:** TASK-ciclo-pedido-entrega-cobro
**Fecha:** 2026-10-08

## Contexto
Sales necesita persistir un agregado con ítems y pagos (cambio importante de base de datos: migración inicial de un módulo nuevo). REQ-SAL-014 exige filtrar, ordenar y paginar por `status`, `payment_status`, canal, cliente, fechas y saldo; `payment_status` y `balance` se derivan de los pagos (REQ-SAL-012/013). Las invariantes "pago ≤ saldo" y "total ≥ pagado" son vulnerables a escrituras concurrentes (dos pagos simultáneos, un pago mientras se edita un ítem). Patrón previo: modelos con UUID como PK, `created_at/updated_at`, `db_table` explícita, mapper entidad↔modelo y lista perezosa paginable (`backend/modules/customers/infrastructure/django/{models,mappers,repositories}.py`); tests contra PostgreSQL real (`config/settings/test.py`). Dominio: [ADR-ciclo-pedido-entrega-cobro-modelo-dominio](ADR-ciclo-pedido-entrega-cobro-modelo-dominio.md).

## Decisión

**Tablas** (modelos Django separados de las entidades; mapper `OrderModel/ItemModel/PaymentModel ↔ Order`):
- `sales_order`: `id` UUID PK; `customer_id` UUID nulo (**sin FK**, indexado); `status` y `payment_status` `CharField` (indexados); `sales_channel` `CharField` (indexado); `order_date` y `expected_delivery_date` `DateField` (indexados), `delivered_date` `DateField` nulo; `subtotal`, `discount`, `total`, `paid_total` `DecimalField(max_digits=12, decimal_places=2)`; `notes` `TextField`; `cancellation_reason` `TextField`, `cancelled_at` `DateTimeField` nulo; `created_at`, `updated_at`. `ordering = ['-order_date', '-created_at', 'id']`.
- `sales_order_item`: `id` UUID PK; `order` FK → `sales_order` (`on_delete=CASCADE`, `related_name='items'`); `product_id` UUID (**sin FK**); `product_name` `CharField(150)`; `unit_price` y `subtotal` `DecimalField(12,2)`; `quantity` `PositiveIntegerField`; **`UniqueConstraint(order, product_id)`**.
- `sales_payment`: `id` UUID PK; `order` FK (`CASCADE`, `related_name='payments'`); `amount` `DecimalField(12,2)`; `payment_method` `CharField`; `payment_date` `DateField`; `reference` `CharField(100)`; `created_at`.
- **`CheckConstraint`** como defensa en profundidad: `discount ≥ 0`, `total ≥ 0`, `paid_total ≥ 0`, `quantity > 0`, `amount > 0`. Las reglas siguen en el dominio; la BD solo impide estados absurdos.
- Los códigos de enumeración se guardan como texto; las opciones no se aplican a nivel de BD (la validación es del dominio).
- Una sola migración `modules/sales/migrations/0001_initial.py` generada con `makemigrations`; solo crea tablas nuevas. `modules.sales` se agrega a `INSTALLED_APPS` y `api/orders/` a `config/urls.py`.

**Valores derivados persistidos (desnormalización controlada).** `subtotal`, `total`, `paid_total` y `payment_status` (y `subtotal` de cada ítem) se **guardan** como columnas para poder filtrar, ordenar y paginar en SQL (`payment_status`, `has_balance = total > paid_total`). Solo los calcula el agregado y solo se escriben desde `repository.save(order)` (nunca por ORM directo ni admin). `balance` **no** se guarda: es `total − paid_total` y se calcula en el dominio y en el filtro SQL (`F('total') > F('paid_total')`). Una prueba verifica que lo persistido coincide con el recalculado por el agregado.

**Repositorio** (interfaz en `domain/repositories.py`, implementación Django): `get(order_id)`, `get_for_update(order_id)`, `save(order)` y `list(filters)` que devuelve una lista perezosa paginable (mismo patrón que `ProductList`/clientes). `save` upsertea el pedido, sincroniza ítems por `id` (crea/actualiza/borra los ausentes) y **solo agrega** pagos nuevos (nunca borra ni modifica los existentes). `get` y la lista de detalle usan `prefetch_related` para ítems y pagos; la lista de resumen no los carga.

**Concurrencia.** Cada comando que modifica un pedido corre en `transaction.atomic()` abierta por la capa API (`_run`) y carga el agregado con `get_for_update` (`SELECT … FOR UPDATE` sobre la fila del pedido). Así dos pagos o una edición y un pago sobre el mismo pedido se serializan, y las invariantes "pago ≤ saldo" y "total ≥ pagado" se evalúan sobre datos actuales. No se usa bloqueo optimista/versión: hay pocos usuarios y el bloqueo de fila es suficiente y más simple. La capa `application` no importa Django: la apertura de la transacción es responsabilidad de `api`.

**Índices:** individuales en `status`, `payment_status`, `sales_channel`, `order_date`, `expected_delivery_date`, `customer_id`; índices compuestos solo si una medición posterior los justifica.

## Alternativas consideradas
- **Calcular `payment_status`/`balance` al leer (anotaciones con `Sum` de pagos):** sin riesgo de divergencia, pero filtrar/paginar por esos valores obliga a agregaciones en cada consulta y complica la lista perezosa. Con columnas persistidas la consulta es trivial; el riesgo de divergencia se acota porque solo el agregado escribe y hay una prueba de coherencia.
- **Vista materializada / tabla de reporting:** sobredimensionada para el MVP; Reporting leerá estas tablas.
- **FK entre apps (`customer`, `product`):** acopla migraciones y modelos entre módulos y contradice `ddd.md:772-779`; se guardan UUID, como ya anticipan los ADR de clientes y catálogo.
- **Bloqueo optimista (campo `version`):** exige reintento/409 en la UI; innecesario con bloqueo de fila.
- **`ATOMIC_REQUESTS` global:** cambia el comportamiento de todo el proyecto; se prefiere una transacción explícita en las vistas de Sales.
- **Guardar JSON de ítems/pagos en el pedido:** impide consultas y constraints. Descartado.

## Estrategia de rollback / mitigación
- **Migración aditiva:** `0001_initial` solo crea `sales_order`, `sales_order_item`, `sales_payment`; no altera tablas existentes. Es reversible (`python manage.py migrate sales zero` elimina las tres tablas) y no hay datos previos que migrar. Antes de aplicarla en un entorno con datos, respaldar la base como en cualquier migración.
- **Rollback de código:** revertir el PR; si ya se registraron pedidos reales, `migrate sales zero` los destruye, así que en producción se prefiere desactivar la ruta (quitar el `include`) y mantener las tablas hasta decidir.
- **Mitigación de divergencia de derivados:** escritura única vía agregado, `CheckConstraint`, prueba de coherencia y, si hiciera falta, un comando de gestión de recálculo (no se construye ahora).
- Nunca editar `0001` una vez aplicada; los cambios van en una migración nueva (regla de `CLAUDE.md`).

## Consecuencias
- Queda fácil: filtros y orden en SQL con paginación perezosa; `Reporting` puede agrupar por canal/estado sobre columnas simples; pruebas de repositorio reales en PostgreSQL.
- Queda más difícil: mantener la coherencia de las columnas derivadas (disciplina: solo el agregado escribe); el `save` de un agregado grande hace sincronización de hijos.
- Deuda aceptada: sin índices compuestos; sin versión optimista; bloqueo de fila puede serializar operaciones sobre un mismo pedido (aceptable a esta escala); sin bitácora de cambios.
