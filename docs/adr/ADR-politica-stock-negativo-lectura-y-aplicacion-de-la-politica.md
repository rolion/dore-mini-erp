# ADR-politica-stock-negativo-lectura-y-aplicacion-de-la-politica: Dónde vive la política y cómo la aplica Inventario

**Estado:** Propuesto
**Task relacionado:** TASK-politica-stock-negativo
**Fecha:** 2026-10-29

## Contexto
Inventario ya bloquea salidas sin saldo (`allow_negative=False`) bajo el bloqueo del almacén, pero `allow_negative` lo decide quien llama y no existe configuración por empresa. La historia pide un ajuste «Permitir stock negativo» (por defecto bloqueado) en Inventario → Configuración → General, con historial (PB-CFG-001), y que la validación y el cambio de saldo sean atómicos.

## Decisión
1. **El ajuste vive en el catálogo de `modularity`**: `inventory.allow_negative_stock`, nuevo tipo `boolean` (valores normalizados `'true'`/`'false'`, defecto `'false'`; historial legible «Permitido»/«Bloqueado»). Sin migración: se guarda en la tabla genérica existente de ajustes por empresa. Reutiliza API, historial, permisos de administrador y validación de habilitación del módulo.
2. **Lectura por fachada**: `modularity.services.get_inventory_settings(company_id) -> InventorySettings(allow_negative_stock: bool)` (DTO inmutable, solo lectura), como `get_sales_settings`. Se añade `inventory → modularity` al mapa de dependencias permitidas (test de frontera).
3. **Inventario lee la política por un puerto** `InventoryPolicy` (`allow_negative_stock() -> bool`) con adaptador `ModularityInventoryPolicy(company_id)` en `inventory/infrastructure/adapters.py`. `RecordMovement` y `ReverseMovement` lo reciben y lo consultan **dentro del `locked(warehouse_id)`**, justo antes de comparar el saldo; el parámetro `allow_negative` desaparece de casos de uso y fachada (la política deja de ser decisión del llamante). Los ajustes pasan por la misma ruta.
4. **Contrato de error**: `MovementConflict('insufficient_stock')` pasa a llevar un detalle (`product_id`, `warehouse_id`, `requested`, `available`) y el 409 HTTP lo expone como `{detail, code: 'insufficient_stock', product: {id, name}, warehouse: {id, name}, requested, available}` (decimales en texto). Los endpoints actuales que ya traducen el conflicto (apertura de existencias, ajustes) usan el mismo serializador; la reversión y la entrega de otras historias lo reutilizarán.
5. **Atomicidad**: no se agrega mecanismo nuevo. `locked()` (transacción + `select_for_update` del almacén) ya serializa salidas simultáneas; la política, la comprobación del saldo y el `insert` ocurren en esa misma sección crítica. Un rechazo lanza antes del `insert`, así que no deja movimiento.

## Alternativas consideradas
- **Tabla/modelo propio en `inventory`** (`InventoryPolicy`): duplica API, historial y permisos de PB-CFG-001 y exige migración; descartada.
- **Que cada llamante lea la política y pase `allow_negative`** (estado actual): permite olvidar la política o saltársela; descartada.
- **Cachear la política**: ahorra una consulta por salida pero arriesga leer un valor viejo en la sección crítica; no hay necesidad medida.
- **Conectar Ventas a Inventario en esta historia**: fuera de alcance por decisión del usuario.

## Estrategia de rollback / mitigación
Sin migración ni datos nuevos: revertir el PR devuelve el comportamiento actual (bloqueo siempre activo). Las filas `inventory.allow_negative_stock` ya guardadas quedan inertes (clave desconocida ignorada al leer si se revierte el catálogo; confirmar en el test de lectura). Si la política se habilita y luego se deshabilita con saldos negativos existentes, estos permanecen visibles en Existencias (filtro «negativo», PB-INV-005); no hay corrección automática.

## Consecuencias
- `modularity` pasa a ser consumida por `inventory` además de `sales`; `modularity` sigue sin importar módulos de negocio.
- Cambia la firma pública de `inventory.services.record_movement`/`reverse_movement` (sin `allow_negative`); hoy solo la usan tests, sin otros consumidores en el repositorio.
- Cada salida suma una lectura de configuración dentro del bloqueo (consulta por clave, costo despreciable al volumen del MVP).
- Deshabilitar la política no bloquea entradas ni limpia saldos negativos.
