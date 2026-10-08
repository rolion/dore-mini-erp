# ADR-clientes-mvp-historial-compras: Historial de compras y vínculo con pedidos sin acoplar Customers a Sales

**Estado:** Propuesto
**Task relacionado:** TASK-clientes-mvp
**Fecha:** 2026-10-08

## Contexto
REQ-CUS-004 pide que el perfil muestre fecha, total y estado de los pedidos del cliente, y aclara que "Customers no modifica pedidos; solo consulta información provista por Sales". REQ-CUS-001 pide poder asociar el cliente recién creado a un pedido, y REQ-CUS-005 que los pedidos históricos de un cliente desactivado sigan accesibles. Sales (REQ-SAL-001) **no existe**: no hay `backend/modules/sales`. `ddd.md:757-779` fija la dirección de dependencia (`Sales → Customers`; Sales referencia `customer_id` pero no toca modelos internos de Customers), `ddd.md:543` prevé `ListOrdersByCustomer` como consulta de Sales y `ddd.md:308` lista `GetCustomerPurchaseHistory` como query de Customers. `ddd.md:783-807` permite comunicación entre módulos por servicios de aplicación o interfaces, y el ADR del catálogo ya difirió su servicio de consulta hasta que Sales exista.

## Decisión
- **El historial lo provee Sales; Customers no lo implementa ni lo consulta desde el backend.** Customers no importa nada de Sales (ni se crea un endpoint `/api/customers/{id}/…` que lo proxee). Esto preserva `Sales → Customers` y evita un ciclo.
- **Contrato que Sales deberá cumplir** (REQ-SAL-001, otro task): `GET /api/orders/?customer_id=<uuid>` con paginación estándar, orden por fecha descendente, que devuelva por pedido al menos `id`, la fecha del pedido, el total (string decimal) y el estado. Debe seguir funcionando para clientes inactivos (REQ-CUS-005). Queda registrado en este ADR como requisito para el diseño de Sales, no se implementa aquí.
- **Alcance en este task:** el perfil del cliente en el frontend incluye la sección "Historial de compras" (DDR) con un modelo tipado `CustomerOrderSummary { id, date, total, status }` y su estado vacío "Este cliente aún no tiene pedidos"; **no se hace ninguna petición a un endpoint inexistente**. Cuando exista Sales, conectar la sección es un cambio acotado en el frontend (un método de servicio y el binding), sin tocar el backend de Customers. Por tanto REQ-CUS-004 queda **entregado solo a nivel de interfaz y contrato**; su criterio de aceptación completo se cierra con Sales.
- **Vínculo cliente↔pedido:** Sales almacenará `customer_id` como UUID (sin FK entre apps). Para validar el cliente al crear un pedido (existe y está activo) Sales usará un servicio de aplicación de Customers (`get_customer_for_sale`, estilo `ddd.md:793-799`); **no se construye ahora** (sin consumidor), igual que en el catálogo. La creación rápida desde un pedido reutiliza `POST /api/customers/` (ver contrato) y entrega el `id` devuelto al formulario del pedido.
- **Integridad histórica:** Customers no tiene borrado (ver ADRs de dominio y contrato), por lo que ningún pedido puede quedar apuntando a un cliente inexistente. Si luego se requiere anonimización, será una decisión posterior que conserve el `id`.

## Alternativas consideradas
- **Endpoint `GET /api/customers/{id}/purchase-history/` que llame a Sales:** coincide con el nombre de query de `ddd.md:308`, pero obliga a Customers a importar Sales, invirtiendo la dependencia recomendada y creando un ciclo (Sales ya depende de Customers).
- **Puerto `PurchaseHistoryProvider` (Protocol) en Customers, implementado por Sales:** respeta la dirección de dependencia mediante inversión, pero hoy tendría un único adaptador vacío (endpoint que siempre devuelve `[]`), código sin consumidor real que puede inducir a error; se reevalúa si el perfil necesita agregados (total comprado, última compra) calculados en servidor.
- **Fingir datos o un endpoint temporal:** presenta historial inexistente como real. Descartado.
- **Ocultar la sección hasta que exista Sales:** evita una vista vacía, pero obliga a un cambio de UI después; se prefiere mostrar el estado vacío explícito del DDR.
- **Reporting como fuente del historial:** Reporting solo lee y está pensado para agregados, no para el perfil operativo.

## Estrategia de rollback / mitigación
No aplica rollback propio: no hay cambios de BD, API ni infraestructura en esta decisión; solo una sección de UI con estado vacío y un contrato escrito para Sales. Si Sales adopta otro contrato, se actualiza este ADR (marcándolo como reemplazado) y se ajusta el servicio del frontend.

## Consecuencias
- Queda fácil: Customers y Sales evolucionan sin importarse; la sección del perfil no necesita cambios en el backend de Customers al llegar Sales.
- Queda más difícil: REQ-CUS-004 y el criterio "se asocia inmediatamente a un pedido" no son verificables de extremo a extremo hasta el task de Sales; el perfil hará una llamada adicional (a Sales) en vez de una sola.
- Deuda aceptada: sin agregados en el perfil (total comprado, última compra); sin servicio `get_customer_for_sale` hasta que haya consumidor.
