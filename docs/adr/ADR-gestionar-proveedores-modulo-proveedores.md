# ADR-gestionar-proveedores-modulo-proveedores: Bounded context `purchases`, agregado Proveedor, contrato API y fachada

**Estado:** Propuesto
**Task relacionado:** TASK-gestionar-proveedores
**Fecha:** 2026-10-29

## Contexto
No existe el módulo Compras. PB-COM-001 introduce su primer agregado, `Supplier`, y exige que las compras futuras lo referencien (solo proveedores activos para compras nuevas; históricas conservan la referencia). Referencia estructural: `customers` (`docs/adr/ADR-clientes-mvp-modelo-dominio.md`). Impactos: nueva tabla y migración (no afecta datos existentes), nuevo contrato API consumido por Angular, aislamiento por `company_id`, compuerta de módulo `purchases`.

## Decisión
1. **Módulo** `backend/modules/purchases/` (app Django `modules.purchases`, label `purchases`, igual a la clave de `modularity`) con `domain/ application/ infrastructure/django/ api/ services.py`. Dominio puro.
2. **Agregado `Supplier`**: `id` UUID, `name` (obligatorio, ≤150), `tax_id` (identificación; opcional, ≤50, recortada), `phone` (opcional, ≤30, recortado), `email` (opcional, ≤254, formato validado si se informa), `notes` (opcional, ≤2000), `active` (nace `True`), `created_at`, `updated_at`. Estado solo por `activate()`/`deactivate()` (idempotentes). Los errores de todos los campos se juntan en un solo `SupplierValidationError`. Sin unicidad de `tax_id` ni de nombre.
3. **Persistencia**: `SupplierModel`, tabla `purchases_supplier`, `company_id` UUID indexado sin FK, índice por `(company_id, active)`; `DjangoSupplierRepository(company_id)` filtra siempre por empresa. Búsqueda: nombre `icontains` o `tax_id` `icontains`. Orden por nombre, id. Migración `0001_initial` nueva.
4. **API** `/api/suppliers/` (todas las vistas `required_modules = ('purchases',)`):
   - `GET` lista paginada `{count,next,previous,results}` con `search`, `active=true|false` (ausente = todos; otro valor → 400), `page`, `page_size` (máx. 100); `POST` crea (201).
   - `GET/PATCH /{id}/` (parcial; `active` ignorado; `PUT`/`DELETE` → 405), `POST /{id}/activate/`, `POST /{id}/deactivate/`.
   - Recurso `{id, name, tax_id, phone, email, notes, active, created_at, updated_at}`. 404 `{detail: "Proveedor no encontrado."}`; 400 `{campo: [mensajes]}`.
5. **Fachada** `modules/purchases/services.py` (única vía entre módulos; DTO inmutables): `get_supplier_for_purchase(company_id, supplier_id) -> SupplierForPurchase(id, name, active) | None` (otra empresa o inexistente → `None`; la regla «solo activos en compras nuevas» la aplica quien compra) y `list_active_suppliers(company_id, search=None, limit=…)` para el selector. Las compras futuras guardarán `supplier_id` y un snapshot del nombre, de modo que desactivar nunca toca compras.
6. **Registro**: `INSTALLED_APPS`, `path('api/suppliers/', …)` en `config/urls.py`, `ALLOWED_DEPENDENCIES['purchases'] = set()` en `test_boundaries.py`, `BUSINESS_APPS` en `test_guards.py`, nota en `docs/architecture/ddd.md`.
7. **Frontend**: `features/purchases/` (pages supplier-list/form/detail, `suppliers-api.service.ts`, models, `purchases.routes.ts` con `suppliers`), montado bajo `purchases/suppliers` con `moduleGuard`; la ruta `purchases` (Próximamente) se conserva.

## Alternativas consideradas
- **Poner proveedores dentro de `expenses`** (ya tiene `supplier_name`): descartado, Compras es otro contexto y depende de Gastos solo en lectura; acoplaría ambos.
- **Normalizar el teléfono como Clientes**: descartado, no hay detección de duplicados que lo justifique; añade reglas no pedidas.
- **Unicidad de identificación**: descartado, no está en el requerimiento; se puede añadir con aprobación.
- **Esperar a la task de Compras para la fachada**: descartado, el contrato «solo activos» es parte de este requerimiento y debe quedar probado.

## Estrategia de rollback / mitigación
Cambio aditivo: tabla nueva y rutas nuevas, sin tocar datos existentes. Rollback = revertir el PR; si la migración ya se aplicó, `migrate purchases zero` la elimina (no hay otras tablas que la referencien). El módulo `purchases` sigue deshabilitado por defecto, así que ninguna empresa ve el cambio hasta habilitarlo.

## Consecuencias
Primer contexto de Compras; la task de Compras importará solo `modules.purchases.services` desde un adaptador de infraestructura y deberá registrar `ALLOWED_DEPENDENCIES`. Se acepta duplicación de patrón con `customers`. Pendiente conocido: sin aviso de identificación duplicada.
