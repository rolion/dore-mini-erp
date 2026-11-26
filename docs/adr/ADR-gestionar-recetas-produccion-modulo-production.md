# ADR-gestionar-recetas-produccion-modulo-production: Nuevo módulo `production` con agregado Receta

**Estado:** Propuesto
**Task relacionado:** TASK-gestionar-recetas-produccion
**Fecha:** 2026-11-26

## Contexto
No existe soporte de producción. La tarjeta DORE-PROD-001 abre el menú Producción (Recetas ahora, Órdenes en una tarjeta posterior). Las recetas dependen de productos y unidades del Catálogo (`catalog/services.py` como única vía entre módulos) y deben respetar las reglas de unidad de Inventario (una unidad base por producto, sin conversiones; `inventory/domain/stock.py:59`). `docs/architecture/ddd.md` pide módulos con `domain/ application/ infrastructure/ api/` y fachadas; el registro de módulos opcionales vive en `modularity/domain/modules.py`.

## Decisión
1. **Nuevo módulo Django `modules.production`** (label `production`), registrado en `INSTALLED_APPS` y `config/urls.py` (`api/recipes/`), y como módulo opcional en `MODULE_CATALOG`: `ModuleDefinition('production', 'Producción', 'Recetas y órdenes de producción.', requires=('catalog',), optional=('inventory',))`. No entra en `DEFAULT_ENABLED_KEYS` ni en el snapshot de defaults (se habilita por empresa). Las API devuelven 403 `module_disabled` con el módulo apagado (mecanismo existente `REQUIRED_MODULES`).
2. **Agregado `Recipe`** (dominio puro) con entidad hija `RecipeIngredient`. Estados por métodos (`activate()`, `deactivate()`, `redefine(...)`), sin asignación directa. No se borra: solo desactivar.
3. **Tablas** `production_recipe` (id UUID, company_id, name, result_product_id, yield_quantity, active, timestamps) y `production_recipe_ingredient` (id, recipe FK, product_id, unit_id, quantity, position). Las referencias a producto/unidad son UUID **sin FK a tablas de otro módulo** (consistencia con el aislamiento por módulo); la validez la comprueba la aplicación vía fachada de Catálogo. Cantidades `Decimal(14,4)`. Nombre único por empresa sin distinguir mayúsculas (restricción en dominio/aplicación y índice único funcional).
4. **Fachada de Catálogo `get_product_for_production(company_id, product_id)`** (DTO congelado: id, nombre, activo, id/abreviatura/`allows_fractions` de la unidad base). Production no importa modelos de Catálogo. Un adaptador (`production/infrastructure/adapters.py`) implementa el puerto `ProductCatalog`.
5. **Regla de compatibilidad de unidad:** el ingrediente guarda `unit_id`, que debe ser la unidad base de su producto; cantidades fraccionarias solo si la unidad lo admite. El rendimiento se expresa en la unidad base del producto resultante (se deriva, no se guarda).
6. **Órdenes futuras:** copiarán (snapshot) nombre, producto, rendimiento e ingredientes al crearse; así editar o desactivar una receta no altera órdenes históricas. Esta tarea no crea órdenes.
7. **API** (aditiva, nada existente cambia): `GET/POST /api/recipes/`, `GET/PUT /api/recipes/<id>/`, `POST /api/recipes/<id>/activate/` y `/deactivate/`; lista paginada (20, máx. 100) con filtros `status` (`active` por defecto/`inactive`/`all`) y `q`.

## Alternativas consideradas
- **Ampliar `catalog` con recetas:** menos archivos, pero mezcla producción con catálogo y bloquea las órdenes futuras en el mismo contexto. Descartada.
- **FK reales a producto/unidad:** integridad en BD, pero acopla tablas entre módulos y rompe la regla de no importarse infraestructura. Descartada; se compensa validando por fachada y mostrando aviso si el producto cambió.
- **Conversión de unidades por ingrediente:** fuera del MVP; Inventario no la soporta.
- **Versionado de recetas ahora:** innecesario si las órdenes copian la receta.

## Estrategia de rollback / mitigación
Módulo aditivo y deshabilitado por defecto: revertir el PR deja las tablas sin uso (migración nueva, sin tocar existentes). Para retirarlo sin revertir basta no habilitar el módulo; si se revierte código con tablas ya creadas, una migración inversa elimina `production_recipe*` (sin datos de otros módulos que dependan de ellas).

## Consecuencias
Primer contexto de Producción listo para Órdenes. Hay que actualizar `ddd.md` (módulo `production` → Catálogo), `test_guards.py` (`BUSINESS_APPS`) y `test_boundaries`. Productos desactivados tras guardar la receta no se detectan por BD: la UI avisa y las órdenes futuras validarán.
