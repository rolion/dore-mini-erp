# ADR-crm-listado-clientes-contexto-crm-de-solo-lectura: Contexto `crm` de solo lectura que compone Clientes, Ventas e Inventario

**Estado:** Propuesto
**Task relacionado:** TASK-crm-listado-clientes
**Fecha:** 2026-11-24

## Contexto
El listado CRM necesita datos de tres contextos: Clientes (nombre, teléfono), Ventas (pedidos, última compra, saldo) e Inventario (almacén como «sucursal»). `docs/architecture/ddd.md:819-821` fija que la única entrada entre módulos es la fachada `services.py` y que `sales → customers` es una dependencia permitida; lo inverso (`customers → sales`) crearía un ciclo. Hoy no existen sucursales (el pedido guarda `warehouse_id`, `backend/modules/sales/infrastructure/django/models.py:15-16`, nulo en pedidos antiguos) ni segmentos (decisión de negocio: el filtro queda para PB-CRM-007).

## Decisión
1. Nuevo bounded context `backend/modules/crm/` **de solo lectura** (sin modelos ni migraciones), con `application/`, `api/` e `infrastructure/adapters.py`, siguiendo el patrón de `reporting` (puertos en `application/ports.py`, adaptadores sobre fachadas).
2. Endpoint `GET /api/crm/customers/` con `required_modules = ('customers',)`; Ventas e Inventario son **opcionales** (si están deshabilitados, las columnas/filtro correspondientes no aplican y la respuesta lo indica en `meta`). No se añade una clave nueva al catálogo de módulos de `modularity` (evita tocar el snapshot de defaults y la migración de habilitación; se reevaluará cuando PB-CRM-002+ necesite habilitar CRM aparte).
3. Dependencias nuevas permitidas, solo por fachada y solo desde los adaptadores de `crm`: `crm → {customers, sales, inventory}` (la disponibilidad de módulos se lee con `shared.module_gate`, sin importar `modularity`). Nadie importa `crm`. Se actualiza el mapa de `docs/architecture/ddd.md` y el test de fronteras `modules/sales/tests/test_boundaries.py`.
4. Fachadas nuevas (DTO inmutables, `company_id` primer argumento): `customers.services.search_customers_for_crm` (clientes **activos**, búsqueda por nombre/teléfono, filtro opcional por conjunto de ids, orden estable `name, id`, paginable perezosa); `sales.services.get_customer_commercial_summaries` (por cliente: `order_count`, `last_purchase_date`, `outstanding_amount`) y `sales.services.list_customer_ids_with_orders_in_warehouse`. Definiciones de Ventas: «pedido válido» = no cancelado y con ítems; saldo = Σ(`total − paid_total`) de pedidos válidos con saldo > 0 (`sales/services.py:1-10`).
5. Composición: sin filtro de almacén, la página de clientes sale de Clientes y sus agregados se piden a Ventas **solo para los ids de la página** (una consulta agregada). Con filtro de almacén, Ventas entrega los ids con pedidos en ese almacén y Clientes los usa como restricción.
6. Moneda: `currency` es `BOB`, la constante de moneda del producto (`sales/infrastructure/adapters.py:47`); no hay moneda por empresa.

## Alternativas consideradas
- **Ampliar `customers` con datos de ventas:** invierte la dependencia permitida y acopla Clientes a Ventas. Descartada.
- **Ampliar `reporting`:** Reporting es de solo lectura pero orientado a métricas por período; un listado operativo paginado con búsqueda no encaja y mezclaría navegación CRM con reportes. Descartada.
- **Tabla desnormalizada de resumen por cliente:** da SQL único, pero exige sincronizar con cada pedido/pago y migración; innecesario al volumen del MVP. Descartada.
- **Nueva clave de módulo `crm`:** más control de habilitación, pero toca catálogo, snapshot de empresas y migraciones sin necesidad hoy. Pospuesta.

## Estrategia de rollback / mitigación
Sin migraciones ni datos nuevos: revertir el PR elimina el módulo, la ruta y el ítem de menú sin efectos sobre datos. El aislamiento por empresa se asegura con repositorios/fachadas filtrados por `company_id` y un test de fuga entre empresas. Riesgo de rendimiento del filtro por almacén (lista de ids): aceptable al volumen del MVP; si crece, mover la restricción a una subconsulta en una fachada de Ventas.

## Consecuencias
- Un contexto nuevo mínimo y reversible que PB-CRM-002 (ficha 360°) y PB-CRM-007/008 (segmentos) pueden extender.
- El listado depende de las definiciones de Ventas; cualquier cambio de «pedido válido» se refleja solo en un lugar.
- Los pedidos sin `warehouse_id` nunca coinciden con un filtro de almacén (limitación declarada).
- Los clientes desactivados no aparecen en el listado CRM.
