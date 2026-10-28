# ADR-inventario-stock-almacenes-unidades-propiedad-y-fronteras: Dónde viven unidades, almacenes y los bloqueos por historial

**Estado:** Propuesto
**Task relacionado:** TASK-inventario-stock-almacenes-unidades
**Fecha:** 2026-10-27

## Contexto
Dos historias comparten datos: el producto (Catálogo) guarda «controla stock» y «unidad base»; las unidades y los almacenes se administran en Inventario → Configuración. Hay reglas que cruzan módulos:
- Una unidad usada por un producto no cambia su significado (Inventario necesita saber si Catálogo la usa).
- Cambiar unidad o control de stock se bloquea con movimientos previos (Catálogo necesita saber si Inventario tiene historial).
- Un almacén con saldo o recepciones pendientes no se desactiva (datos que aún no existen).

`catalog` hoy no depende de nadie y `inventory` solo requiere `catalog` (`modularity/domain/modules.py:24-25`). Si las unidades vivieran en `inventory`, Catálogo consultaría a Inventario (validar unidad) e Inventario a Catálogo (unidad en uso): dependencia mutua entre bounded contexts.

## Decisión
1. **`catalog` es dueño de la unidad de medida** (`UnitOfMeasure`: nombre, abreviatura, admite fracciones, activa, `company_id`) porque es un atributo del producto. La pantalla vive en el menú de Inventario y su API se protege con `required_modules = ('inventory',)`; es solo una clave de texto, no un import. Producto→unidad es una FK real dentro de `catalog` (`PROTECT`). «Unidad en uso» se resuelve con una consulta local.
2. **`inventory` (nuevo módulo) es dueño del almacén** (`Warehouse`: nombre, descripción, activo, predeterminado, `company_id`) y de sus reglas. Dependencias permitidas: ninguna hoy (`ALLOWED_DEPENDENCIES['inventory'] = set()`); `inventory → catalog` queda declarado en `modularity` y se usará con las existencias.
3. **Bloqueo por historial = puerto neutro `shared/stock_history.py`**, mismo patrón que `shared/module_gate.py`: `register(provider)` y `has_history(company_id, product_id) -> bool`. Sin proveedor registrado responde `False` (hoy no hay movimientos; a diferencia del gate, no es un permiso, y denegar bloquearía todo). Catálogo lo consulta en `UpdateProduct`; el módulo que algún día guarde movimientos lo registra. Ninguno importa al otro.
4. **Desactivación de almacén**: puerto `WarehouseActivity` en `inventory/application/ports.py` (`has_nonzero_balance`, `has_pending_receipts`), con adaptador nulo (siempre «no») hoy. Las futuras historias lo sustituyen sin tocar el caso de uso.
5. **Almacén predeterminado**: se siembra perezosamente («Almacén principal») la primera vez que la empresa lista o consulta almacenes, de forma idempotente y bajo bloqueo; un índice único parcial (`company_id` donde `is_default`) garantiza como máximo uno. El predeterminado no se puede desactivar; antes hay que designar otro (`make-default`), que debe estar activo. Nombres únicos por empresa sin distinguir mayúsculas.
6. **Catálogo escribe campos de inventario solo con Inventario habilitado** (`shared.module_gate.is_enabled(company_id, 'inventory')`): activar stock, cambiar unidad. Desactivar stock con el módulo apagado se permite si no hay historial. La API siempre devuelve los campos; ocultarlos es asunto de la UI.
7. `tracks_stock=false` limpia la unidad base (`base_unit=null`); `tracks_stock=true` exige una unidad activa de la misma empresa.

## Alternativas consideradas
- **Unidades en `inventory`** (lectura literal del menú): dependencia catalog⇄inventory o consultas duplicadas; obliga a una fachada en cada sentido. Descartada; el costo es que el código de unidades esté en `catalog` mientras su pantalla está bajo Inventario (documentado en el DDR).
- **Eventos / bus de dominio para el historial**: infraestructura nueva sin necesidad real (fuera del MVP, `CLAUDE.md`). Descartada.
- **Crear ya `StockMovement` y recepciones vacías**: amplía el alcance a historias siguientes; rechazado por el usuario (opción «puertos listos»).
- **Sembrar unidades básicas**: rechazado por el usuario; las empresas arrancan sin unidades.

## Estrategia de rollback / mitigación
- Migraciones solo aditivas: `catalog` agrega tabla `catalog_unit` y dos columnas (`tracks_stock` `default=False`, `base_unit_id` nullable) a `catalog_product`; `inventory` crea `inventory_warehouse`. Rollback: migrar hacia atrás (`migrate catalog 0002`, `migrate inventory zero`) elimina solo lo nuevo; los productos existentes no cambian de comportamiento.
- Si se descarta la función, basta con no habilitar `inventory`: la API de unidades/almacenes responde 403 y los campos de producto quedan en su valor inicial.
- Riesgo de que el proveedor real de `has_history` no se registre cuando existan movimientos: lo cubre una prueba de contrato y la nota «Known limitations» del PR; la historia de movimientos debe incluir esa conexión en sus criterios.

## Consecuencias
- Un solo módulo nuevo y sin dependencias entre módulos de negocio; el test de fronteras se actualiza (`inventory: set()`).
- Si más adelante hay conversiones entre unidades, probablemente se mueva `UnitOfMeasure` a `inventory`; el contrato HTTP (`/api/units/`) no cambiaría.
- El puerto `shared/stock_history` y el de actividad de almacén son contratos listos pero sin datos reales hasta las historias de movimientos y recepciones.
- Hay que actualizar `docs/architecture/ddd.md` (mapa de dependencias, nuevo módulo `inventory`, propiedad de `UnitOfMeasure`).
