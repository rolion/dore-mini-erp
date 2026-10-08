# ADR-catalogo-productos-mvp-modelo-dominio: Módulo `catalog`, entidad Product y persistencia

**Estado:** Propuesto
**Task relacionado:** TASK-catalogo-productos-mvp
**Fecha:** 2026-10-08

## Contexto
Hoy `backend/modules/` solo tiene `accounts`; `catalog` es el primer bounded context de negocio y fijará el patrón de Customers, Sales y Expenses. `docs/architecture/ddd.md:105-226` define Product (id, name, description, sku, sale_price, active, timestamps), reglas (nombre obligatorio, precio ≥ 0, inactivo no entra a nuevos pedidos), Money/ProductId, commands/queries y un `ProductRepository` con interfaz en dominio e implementación Django en infraestructura; `:910-912` admite no separar modelos si no hay lógica relevante. `CLAUDE.md` exige: dominio sin imports de Django, dinero en `Decimal`, estados por métodos del agregado, no agregar abstracciones sin necesidad real. Los REQ-CAT-001..005 no piden SKU ni moneda.

## Decisión
- **Nuevo módulo** `backend/modules/catalog/` (app Django `modules.catalog`, label `catalog`), registrado en `INSTALLED_APPS`. Capas, creadas solo con contenido real:
  - `domain/`: entidad `Product` (dataclass Python puro, sin Django) con las invariantes y los métodos `rename`, `describe`, `change_price`, `activate`, `deactivate` (idempotentes); excepción de dominio `ProductValidationError` que lleva errores por campo; `ProductRepository` como `Protocol`.
  - `application/`: casos de uso `CreateProduct`, `UpdateProduct`, `ActivateProduct`, `DeactivateProduct` (commands) y `GetProduct`, `ListProducts` (con búsqueda por nombre y filtro de estado) como queries, nombres según `ddd.md:187-205`. `ChangeProductPrice` queda dentro de `UpdateProduct`; `ListActiveProducts` es `ListProducts(active=True)`.
  - `infrastructure/django/`: `ProductModel` (tabla `catalog_product`), `repositories.py` (implementación del Protocol) y `mappers.py` entidad↔modelo.
  - `api/`: serializers, vistas y urls (ver ADR del contrato de API).
- **Entidad / datos:** `id` UUID (generado al crear; Sales lo referenciará como `product_id` sin acoplarse a autoincrementales), `name` (obligatorio, con trim, 1–150 caracteres), `description` (opcional, texto, puede ser vacío), `sale_price` `Decimal` con ≤ 2 decimales y 0 ≤ precio ≤ 9 999 999 999,99 (`DecimalField(max_digits=12, decimal_places=2)`), `active` (default `True`), `created_at`, `updated_at`. **Sin SKU, sin moneda y sin unicidad de nombre** en el MVP: ningún REQ los pide, no hay regla de negocio que los justifique, y agregarlos después es una migración aditiva.
- **Money:** no se crea un value object `Money` ni `shared/domain/money.py` todavía; el dominio valida `Decimal` directamente. Se introduce cuando Sales lo necesite (ahí habrá dos consumidores reales). El dominio rechaza `float`.
- **Invariantes en el dominio** (REQ-CAT-001/002/003): nombre no vacío tras trim; precio ≥ 0; se crea activo; `deactivate()`/`activate()` solo cambian `active`. Los serializers validan solo forma y tipos.
- **Históricos (REQ-CAT-002/003/005):** el módulo nunca elimina productos (no hay `DELETE`) y no almacena nada de ventas. El snapshot de nombre/precio es responsabilidad de `OrderItem` en Sales (`ddd.md:363-376`) y el bloqueo de inactivos en nuevos pedidos se hará cuando exista Sales, consultando a Catalog por un servicio de aplicación (`ddd.md:793-799`); ese servicio **no se construye ahora** (sin consumidor).
- **Migración:** `catalog/migrations/0001_initial.py` generada con `makemigrations`; solo crea la tabla nueva. Sin dependencias nuevas de pip.
- **Pruebas:** tests unitarios de dominio sin base de datos (`SimpleTestCase`) y tests de API con PostgreSQL (`python manage.py test`).

## Alternativas consideradas
- **Modelo Django con métodos (sin entidad de dominio, sin mapper):** menos archivos y válido según `ddd.md:910-912`, pero contradice la regla explícita de `CLAUDE.md` (dominio sin Django, estados por métodos del agregado) y dejaría el primer módulo sin el patrón que los demás deberán seguir. Se rechaza; el costo extra es un mapper y un repositorio pequeños.
- **Repositorio sin `Protocol` (solo clase concreta):** ahorra una abstracción, pero `ddd.md:222-224` fija que la interfaz pertenece al dominio y permite probar los casos de uso con un repositorio en memoria. Se acepta el `Protocol` por ser mínimo.
- **ID autoincremental:** más simple, pero acopla Sales a un entero de BD; UUID es lo sugerido en `ddd.md:172`.
- **Incluir `sku`, moneda y `Money`:** anticipa requisitos hipotéticos; descartado por sobreingeniería (`ddd.md` sección 29).
- **Nombre único:** evitaría duplicados accidentales, pero el negocio no lo declara y variantes con igual nombre son plausibles; se puede añadir un índice único después si surge la regla.

## Estrategia de rollback / mitigación
Cambio aditivo: tabla nueva, ningún dato ni módulo existente depende de ella. Rollback = revertir el PR y, si la migración ya se aplicó, `python manage.py migrate catalog zero` (elimina `catalog_product`; aceptable en este estado del proyecto, sin ventas ni datos productivos). La migración es reversible por construcción (solo `CreateModel`). No se toca `accounts` ni autenticación.

## Consecuencias
- Queda fácil: replicar el patrón en Customers/Sales; probar reglas sin base de datos; evolucionar a SKU/moneda/`Money` con migraciones aditivas.
- Queda más difícil: hay más archivos que un CRUD con `ModelViewSet`; el mapper debe mantenerse sincronizado con el modelo.
- Deuda aceptada: sin servicio de consulta para Sales hasta que exista Sales; precios en una sola moneda implícita; sin unicidad de nombre.
