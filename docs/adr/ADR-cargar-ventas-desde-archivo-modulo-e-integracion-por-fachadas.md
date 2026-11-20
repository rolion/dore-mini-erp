# ADR-cargar-ventas-desde-archivo-modulo-e-integracion-por-fachadas: Módulo `data_import` y escritura entre módulos por fachadas

**Estado:** Propuesto
**Task relacionado:** TASK-cargar-ventas-desde-archivo
**Fecha:** 2026-11-19

## Contexto
La importación de ventas debe crear clientes, productos, proveedores, compras recibidas, pedidos entregados y cobrados, y dejar los asientos que cada módulo ya genera. Hoy los módulos solo se hablan por `services.py` con DTO y casi todas las fachadas son de lectura (`docs/architecture/ddd.md:793-823`, test `sales/tests/test_boundaries.py`). Importar directamente modelos o repositorios ajenos violaría la regla; duplicar la lógica de venta/compra en el importador rompería invariantes (precios, stock, costo, asientos).

## Decisión
1. **Nuevo bounded context `backend/modules/data_import/`** (`domain/ application/ infrastructure/ api/`), no es un módulo habilitable del catálogo de `modularity` (no cambia el snapshot de «14 módulos»). Sus vistas exigen `required_modules = ('sales', 'catalog')` y el permiso por defecto de administrador de empresa. Dueño de: archivo subido y filas crudas, mapeo, opciones, resultado por venta y claves de idempotencia. **No** es dueño de ventas, productos, etc.
2. **Reutiliza la lógica de cada módulo mediante fachadas de escritura nuevas en su `services.py`** (DTO de entrada/salida, `company_id` primer argumento, ejecutan los casos de uso existentes con sus adaptadores dentro de la transacción de quien llama):
   - `catalog.services`: buscar productos por nombre normalizado y crear los faltantes (precio de la primera fila; `can_sell`; stock controlado solo si se pide y hay Inventario, con unidad por defecto).
   - `customers.services`: buscar por nombre normalizado y crear faltantes (sin confirmación de teléfono duplicado: el importador nunca crea con teléfono).
   - `purchases.services`: buscar/crear proveedor por nombre; `import_received_purchase(...)` = crear + confirmar + recibir una compra (entradas de stock con costo, asiento de reconocimiento), **sin pago**.
   - `sales.services`: `import_delivered_sale(...)` = crear pedido (fecha histórica), agregar líneas **con el precio del archivo** (vía `Order.add_item`, no el precio de catálogo), pasar a preparación/lista, entregar con almacén y registrar el cobro total. Parámetro `post_accounting: bool` para no contabilizar cuando la persona desmarcó «movimientos contables».
   - Lectura: `inventory.services` (saldo por almacén, almacenes activos, política de stock negativo), `accounting.services.coverage_status`, `costing` (costo promedio disponible).
3. **Dependencias permitidas nuevas**, siempre y solo por `services.py`: `data_import → {sales, catalog, customers, purchases, inventory, accounting, costing}` más `module_gate`. Nadie importa `data_import`. Se actualizan `ddd.md` §10 y el test de fronteras.
4. **Precio histórico:** el pedido conserva el precio del archivo; el catálogo no se modifica si el producto ya existía (solo un producto creado toma su precio de venta de la primera fila).
5. **Excel:** se lee `.xlsx` con `openpyxl` en modo solo lectura (`read_only=True`, `data_only=True`, primera hoja); `.xls`/`.xlsm` no se aceptan. CSV con UTF-8 (con o sin BOM) y respaldo Latin-1; delimitador `,` `;` o tabulador detectado. **Nueva dependencia: requiere confirmación antes de instalar.**
6. Contrato API bajo `/api/imports/sales/` (detalle en el PLAN); sin impacto en contratos existentes.

## Alternativas consideradas
- **Importador que escribe directo en los modelos de cada módulo:** más rápido, pero salta invariantes y asientos y rompe la regla de fronteras. Descartada.
- **Poner la importación dentro de `sales`:** `sales` pasaría a depender de `purchases` y escribir en catálogo/clientes; mezcla responsabilidades. Descartada.
- **Llamar a la API HTTP interna de cada módulo:** acopla a serialización y autenticación y pierde la transacción compartida. Descartada.
- **Parsear el archivo en el navegador:** el servidor no puede confiar en lo que llega; habría que revalidar todo igual. Descartada (se parsea en servidor; el cliente solo ve cabeceras y muestra).

## Estrategia de rollback / mitigación
- Cambio **aditivo**: tablas nuevas, endpoints nuevos y funciones nuevas en fachadas; no modifica comportamiento existente (los parámetros nuevos tienen el valor que reproduce el comportamiento actual). Se revierte con el `git revert` del PR y la migración inversa de las tablas nuevas (sin datos de otros módulos).
- Los datos creados por una importación (pedidos, compras, asientos) **no se revierten en bloque** (fuera de alcance); cada fila guarda los ids creados para habilitar una reversa futura. Mitigaciones: vista previa obligatoria, confirmación irreversible, transacción por venta y backup previo al despliegue (pipeline existente).

## Consecuencias
- Mapa de dependencias más ancho con un único orquestador; cualquier regla nueva de ventas/compras se hereda sin tocar el importador.
- Hay que mantener las fachadas de escritura con tests de frontera; una dependencia nueva (`openpyxl`, pura Python).
- Carga síncrona: el tamaño se limita (5 MB / 2 000 filas) hasta que exista una cola de trabajos.
