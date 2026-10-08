# ADR-ciclo-pedido-entrega-cobro-integracion-modulos: Cómo Sales consulta Catalog y Customers

**Estado:** Propuesto
**Task relacionado:** TASK-ciclo-pedido-entrega-cobro
**Fecha:** 2026-10-08

## Contexto
Sales necesita, al agregar un ítem, el nombre y precio vigentes de un producto y saber si está activo (REQ-SAL-002), y, al asignar un cliente, saber si existe y está activo; además necesita el nombre del cliente para mostrarlo en listas y detalle. `ddd.md:757-807` fija la dirección `Sales → Catalog` y `Sales → Customers`, comunicación por servicios de aplicación o interfaces y prohíbe importar `infrastructure.django.models` de otro módulo. Dos ADR previos difirieron explícitamente estos servicios hasta que existiera Sales: `ADR-catalogo-productos-mvp-modelo-dominio` ("get_product_for_sale", sin consumidor aún) y [ADR-clientes-mvp-historial-compras](ADR-clientes-mvp-historial-compras.md) ("get_customer_for_sale"). Hoy `grep for_sale backend/` no devuelve nada. Un servicio de aplicación de otro módulo necesita su repositorio Django; si Sales lo cableara tendría que importar la infraestructura ajena.

## Decisión
- **Fachada pública por módulo:** cada módulo expone un único punto de entrada para otros módulos en `modules/<modulo>/services.py` (archivo en la raíz del módulo). La fachada cablea internamente sus propios repositorios y devuelve **DTO inmutables** (dataclasses congeladas), no entidades ni modelos. Los demás módulos solo pueden importar `modules.<modulo>.services`.
  - `modules/catalog/services.py`: `get_product_for_sale(product_id) -> ProductForSale | None` con `{id, name, sale_price (Decimal), active}`.
  - `modules/customers/services.py`: `get_customer_for_sale(customer_id) -> CustomerForSale | None` con `{id, name, active}` y `get_customer_names(ids) -> dict[UUID, str]` (consulta por lote para la lista).
- **Puertos en Sales:** `modules/sales/application/ports.py` define `ProductCatalog` y `CustomerDirectory` (Protocols). Los casos de uso dependen de los puertos; las pruebas usan fakes en memoria.
- **Adaptadores:** `modules/sales/infrastructure/adapters.py` implementa los puertos llamando únicamente a las fachadas `services.py`.
- **Reglas aplicadas por Sales (no por la fachada):** producto inexistente o inactivo → `OrderValidationError({'product_id': [...]})` (REQ-SAL-002); `customer_id` inexistente o inactivo → `{'customer_id': [...]}`, **solo al crear el pedido o al cambiar de cliente**; los pedidos existentes de un cliente luego desactivado siguen siendo visibles y editables (REQ-CUS-005). El precio y el nombre del snapshot se toman del DTO en el servidor; el cliente HTTP nunca los envía.
- **Customers no importa Sales** (se mantiene la dirección y se evita el ciclo): el historial lo obtiene el frontend de Customers del contrato `GET /api/orders/?customer_id=` (ver [ADR-ciclo-pedido-entrega-cobro-contrato-api](ADR-ciclo-pedido-entrega-cobro-contrato-api.md)), que cumple lo exigido por el ADR de historial. **Reporting** leerá las tablas/consultas de Sales por su propia capa de lectura (otro task).
- **Convención:** se documenta en `ddd.md` sección 10 que `services.py` es la única vía entre módulos; el límite se verifica en review (ningún import de `modules.<otro>.domain|application|infrastructure|models` desde un módulo ajeno).

## Alternativas consideradas
- **Sales importa los casos de uso de Catalog/Customers directamente:** exige construir `DjangoProductRepository` desde Sales (importar infraestructura ajena). Descartado por `ddd.md:801-807`.
- **Lectura directa de modelos ORM de otro módulo:** más rápido pero es exactamente lo prohibido.
- **Consulta HTTP interna a `/api/products/`:** acopla un monolito a su propia API, añade latencia y serialización. Descartado.
- **Snapshot del nombre del cliente en el pedido:** evitaría la consulta por lote, pero el nombre cambiaría de significado histórico y duplicaría datos; se prefiere el nombre vigente.
- **Inyectar un `Protocol` desde la capa API en lugar de `services.py`:** equivalente en acoplamiento, pero obliga a cada vista a cablear dependencias ajenas. La fachada centraliza el cableado.
- **No crear el puerto y llamar a `services.py` desde la aplicación:** más corto, pero las pruebas de Sales necesitarían base de datos de otros módulos. El puerto cuesta un archivo pequeño y sí responde a una necesidad (pruebas aisladas).

## Estrategia de rollback / mitigación
Aditivo: se agregan dos archivos `services.py` y no se modifican APIs ni modelos de `catalog`/`customers`. Rollback = revertir el PR. Mitigación de acoplamiento: DTO congelados y un único módulo importable por dominio; el límite se comprueba en review.

## Consecuencias
- Queda fácil: cumplir los ADR diferidos con la menor superficie; probar Sales sin otros módulos; cambiar la implementación interna de Catalog/Customers sin tocar Sales.
- Queda más difícil: dos consultas a Customers por request de lista (una por lote) y una por ítem agregado a Catalog; la fachada debe mantenerse pequeña y no convertirse en un lugar de lógica de negocio.
- Deuda aceptada: la convención `services.py` se verifica por revisión, no por herramienta automática.
