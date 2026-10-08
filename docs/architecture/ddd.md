# DDD del proyecto — Gestión de emprendimientos

## 1. Objetivo

Este documento define una arquitectura basada en **Domain-Driven Design (DDD) pragmático** para una aplicación orientada inicialmente a pequeños emprendimientos que venden productos por canales como WhatsApp, Facebook e Instagram.

El objetivo del sistema es permitir controlar:

- ventas;
- pedidos;
- cobros;
- clientes;
- productos;
- gastos;
- reportes;
- rentabilidad básica.

La implementación propuesta usa:

- **Backend:** Django + Django REST Framework
- **Frontend:** Angular
- **Arquitectura:** Monolito modular
- **Enfoque:** DDD ligero por módulo funcional

La intención no es aplicar DDD de forma académica ni introducir complejidad innecesaria. Cada módulo debe representar una capacidad real del negocio.

---

# 2. Principios arquitectónicos

## 2.1 Monolito modular

El backend será inicialmente una sola aplicación Django y una sola base de datos, pero organizada en módulos de negocio.

```text
backend/
└── modules/
    ├── sales/
    ├── catalog/
    ├── customers/
    ├── expenses/
    └── reporting/
```

Cada módulo tendrá límites claros y no deberá acceder directamente a los detalles internos de otro módulo.

---

## 2.2 Estructura interna de un módulo

```text
module/
├── domain/
│   ├── entities/
│   ├── value_objects/
│   ├── services/
│   ├── repositories/
│   ├── events/
│   └── exceptions/
│
├── application/
│   ├── commands/
│   ├── queries/
│   ├── dto/
│   └── services/
│
├── infrastructure/
│   ├── django/
│   │   ├── models.py
│   │   ├── repositories.py
│   │   └── mappers.py
│   └── integrations/
│
└── api/
    ├── serializers.py
    ├── views.py
    └── urls.py
```

No todos los módulos necesitan todas estas carpetas desde el primer día. Deben crearse cuando exista una necesidad real.

---

# 3. Bounded Contexts iniciales

Los módulos principales del MVP serán:

1. **Sales**
2. **Catalog**
3. **Customers**
4. **Expenses**
5. **Reporting**

En una siguiente fase podrían añadirse:

- Inventory
- Production
- Suppliers
- Marketing
- Integrations
- Accounting

---

# 4. Módulo: Catalog

## 4.1 Responsabilidad

Gestionar los productos que el negocio ofrece.

El catálogo define qué se vende y a qué precio.

No debe encargarse de pedidos ni de pagos.

---

## 4.2 Entidades

### Product

Representa un producto comercializable.

Atributos sugeridos:

```text
id
name
description
sku
sale_price
active
created_at
updated_at
```

Ejemplo:

```text
Pack 10 cuñapés tradicionales
Precio: Bs 35
```

---

## 4.3 Value Objects

### Money

```text
amount
currency
```

Ejemplo:

```text
Money(35, "BOB")
```

Reglas:

- no permitir montos inválidos;
- usar Decimal;
- nunca usar float para dinero.

---

### ProductId

Identificador de producto.

Puede ser UUID para evitar acoplar el dominio a IDs autoincrementales.

---

## 4.4 Reglas de dominio

- El nombre de un producto es obligatorio.
- El precio de venta no puede ser negativo.
- Un producto desactivado no puede agregarse a nuevos pedidos.
- Un producto puede mantenerse históricamente aunque ya no se venda.

---

## 4.5 Casos de uso

### Commands

```text
CreateProduct
UpdateProduct
ActivateProduct
DeactivateProduct
ChangeProductPrice
```

### Queries

```text
GetProduct
ListProducts
SearchProducts
ListActiveProducts
```

---

## 4.6 Repository

```python
class ProductRepository:
    def get(self, product_id):
        ...

    def save(self, product):
        ...

    def list_active(self):
        ...
```

La interfaz pertenece al dominio.

La implementación Django pertenece a infrastructure.

---

# 5. Módulo: Customers

## 5.1 Responsabilidad

Gestionar la información de clientes.

Debe permitir conocer quién compra y facilitar futuras estrategias de retención.

---

## 5.2 Entidad principal

### Customer

```text
id
name
phone
email
notes
created_at
updated_at
```

Campos opcionales futuros:

```text
birthdate
preferred_channel
address
tags
```

---

## 5.3 Value Objects

### PhoneNumber

Permite normalizar números.

Ejemplo:

```text
+591 7xxxxxxx
```

---

### EmailAddress

Valida una dirección de correo.

---

## 5.4 Reglas de dominio

- Un cliente puede existir sin email.
- Para clientes que compran por WhatsApp, el teléfono puede funcionar como identificador práctico.
- No eliminar clientes con historial de ventas.
- Preferir desactivación o anonimización.

---

## 5.5 Casos de uso

### Commands

```text
CreateCustomer
UpdateCustomer
DeactivateCustomer
```

### Queries

```text
GetCustomer
SearchCustomers
ListCustomers
GetCustomerPurchaseHistory
```

---

# 6. Módulo: Sales

## 6.1 Responsabilidad

Gestionar el ciclo completo de:

```text
Pedido → venta → entrega → cobro
```

Es uno de los contextos centrales del sistema.

---

## 6.2 Aggregate Root: Order

Order será el agregado principal.

```text
Order
├── OrderItem
└── Payment references
```

El agregado debe garantizar la consistencia del pedido.

---

## 6.3 Entidad: Order

Campos conceptuales:

```text
id
customer_id
status
payment_status
sales_channel
order_date
delivery_date
subtotal
discount
total
notes
created_at
updated_at
```

---

## 6.4 Entidad: OrderItem

```text
id
product_id
product_name
unit_price
quantity
subtotal
```

Se recomienda guardar un snapshot del nombre y precio del producto.

Esto evita que modificar posteriormente el catálogo cambie históricamente una venta.

---

## 6.5 Entidad: Payment

```text
id
order_id
amount
payment_method
payment_date
reference
status
```

---

## 6.6 Value Objects

### OrderStatus

```text
NEW
IN_PREPARATION
READY
DELIVERED
CANCELLED
```

---

### PaymentStatus

```text
PENDING
PARTIAL
PAID
REFUNDED
```

---

### SalesChannel

```text
WHATSAPP
FACEBOOK
INSTAGRAM
STORE
FAIR
OTHER
```

---

### PaymentMethod

```text
CASH
QR
BANK_TRANSFER
CARD
OTHER
```

---

### Money

Compartido con Catalog.

---

## 6.7 Reglas de dominio

Ejemplos:

- Un pedido debe contener al menos un producto.
- La cantidad de un producto debe ser mayor a cero.
- Un pedido cancelado no puede entregarse.
- Un pedido entregado no debería volver a estado NEW.
- El total se calcula dentro del dominio.
- El total no debe ser introducido manualmente.
- Un pago no puede tener monto negativo.
- La suma de pagos determina el PaymentStatus.
- Entregado y pagado son conceptos independientes.
- Un pedido puede estar entregado y pendiente de pago.
- Un producto desactivado no puede agregarse a nuevos pedidos.
- Cancelar una orden puede requerir una razón.

---

## 6.8 Comportamientos del Aggregate

Ejemplo conceptual:

```python
class Order:

    def add_item(self, product_id, name, unit_price, quantity):
        ...

    def change_quantity(self, item_id, quantity):
        ...

    def apply_discount(self, discount):
        ...

    def mark_in_preparation(self):
        ...

    def mark_ready(self):
        ...

    def deliver(self):
        ...

    def cancel(self, reason):
        ...

    def calculate_total(self):
        ...
```

Se debe evitar que el estado se cambie directamente:

```python
order.status = "DELIVERED"
```

Preferir:

```python
order.deliver()
```

---

## 6.9 Casos de uso

### Commands

```text
CreateOrder
AddOrderItem
RemoveOrderItem
ChangeOrderItemQuantity
ApplyOrderDiscount
ConfirmOrder
StartOrderPreparation
MarkOrderReady
DeliverOrder
CancelOrder
RegisterPayment
RefundPayment
```

### Queries

```text
GetOrder
ListOrders
SearchOrders
ListPendingOrders
ListPendingDeliveries
ListPendingPayments
ListOrdersByCustomer
ListOrdersByDateRange
```

---

## 6.10 Eventos de dominio

No son obligatorios en el MVP, pero algunos eventos útiles serían:

```text
OrderCreated
OrderDelivered
OrderCancelled
PaymentRegistered
OrderFullyPaid
```

En una fase posterior pueden utilizarse para:

- notificaciones;
- actualización de reporting;
- integraciones;
- inventario;
- WhatsApp.

---

# 7. Módulo: Expenses

## 7.1 Responsabilidad

Registrar y clasificar los gastos del negocio.

---

## 7.2 Aggregate Root: Expense

Campos:

```text
id
description
amount
category_id
expense_date
payment_method
supplier_name
notes
receipt_url
created_at
updated_at
```

---

## 7.3 Entidad: ExpenseCategory

Ejemplos:

```text
Materia prima
Empaque
Marketing
Delivery
Transporte
Servicios
Equipamiento
Otros
```

---

## 7.4 Value Objects

### ExpenseType

Opcionalmente puede clasificarse el gasto:

```text
VARIABLE
FIXED
```

Esto puede ayudar posteriormente en reportes.

---

## 7.5 Reglas de dominio

- El monto debe ser mayor a cero.
- Todo gasto debe tener una fecha.
- Todo gasto debe pertenecer a una categoría.
- Categorías utilizadas históricamente no deberían eliminarse físicamente.
- Un gasto puede modificarse mientras no haya sido bloqueado por un cierre contable futuro.

---

## 7.6 Casos de uso

### Commands

```text
CreateExpense
UpdateExpense
DeleteExpense
CreateExpenseCategory
UpdateExpenseCategory
DeactivateExpenseCategory
```

### Queries

```text
GetExpense
ListExpenses
ListExpensesByDateRange
ListExpensesByCategory
ListExpenseCategories
```

---

# 8. Módulo: Reporting

## 8.1 Responsabilidad

Transformar información de otros módulos en indicadores útiles para decisiones.

Reporting no debería ser dueño de las ventas ni de los gastos.

Solo consulta y agrega información.

---

## 8.2 Indicadores iniciales

### Ventas

```text
Total de ventas
Cantidad de pedidos
Ticket promedio
Ventas por día
Ventas por mes
Ventas por canal
Ventas por producto
Ventas por cliente
```

### Gastos

```text
Total de gastos
Gastos por categoría
Gastos por periodo
```

### Rentabilidad

Inicialmente:

```text
Resultado simple = Ventas cobradas - Gastos registrados
```

Debe llamarse explícitamente "resultado simple" o "ganancia estimada" mientras no exista un módulo de costos de producción completo.

---

## 8.3 Casos de uso

### Queries

```text
GetDashboardSummary
GetSalesReport
GetExpenseReport
GetProfitabilityReport
GetSalesByProduct
GetSalesByChannel
GetTopCustomers
GetMonthlyTrend
```

---

## 8.4 Regla arquitectónica

Reporting puede leer información de otros módulos.

No debe modificarla.

Ejemplo:

```text
Reporting → Sales
Reporting → Expenses
Reporting → Customers
Reporting → Catalog
```

Nunca:

```text
Reporting → modificar Order
```

---

# 9. Dependencias entre módulos

Dependencias recomendadas:

```text
Customers
    ↑
Sales ───→ Catalog
  │
  └────→ Payments

Expenses

Reporting ──→ Sales
          ├─→ Expenses
          ├─→ Customers
          └─→ Catalog
```

Sales puede referenciar:

```text
customer_id
product_id
```

pero no debería manipular directamente los modelos internos de Customers o Catalog.

---

# 10. Comunicación entre módulos

Inicialmente pueden utilizarse Application Services.

Ejemplo:

```python
catalog_service.get_product(product_id)
```

o interfaces:

```python
class ProductQueryService:
    def get_product_for_sale(self, product_id):
        ...
```

Evitar:

```python
from modules.catalog.infrastructure.django.models import ProductModel
```

desde el módulo Sales.

---

# 11. Shared Kernel

Debe ser muy pequeño.

Ejemplo:

```text
shared/
└── domain/
    ├── money.py
    ├── ids.py
    ├── date_range.py
    └── exceptions.py
```

No convertir shared en un lugar para lógica genérica de negocio.

---

> **Nota:** `backend/modules/accounts/` contiene solo el modelo de usuario propio (`AUTH_USER_MODEL`). Es infraestructura de identidad, no un bounded context de negocio: sin `domain/` ni `application/`, y los módulos de negocio no lo importan (se refieren al actor por id).

# 12. Estructura sugerida del backend Django

```text
backend/
├── manage.py
│
├── config/
│   ├── settings/
│   ├── urls.py
│   └── wsgi.py
│
├── modules/
│
│   ├── catalog/
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── api/
│   │
│   ├── customers/
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── api/
│   │
│   ├── sales/
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── api/
│   │
│   ├── expenses/
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── api/
│   │
│   └── reporting/
│       ├── application/
│       ├── infrastructure/
│       └── api/
│
└── shared/
    └── domain/
```

---

# 13. Django Models vs Domain Entities

El dominio no debería depender directamente de Django.

Ejemplo:

```python
@dataclass
class Order:
    id: UUID
    customer_id: UUID
    status: OrderStatus
    items: list[OrderItem]
```

Mientras que infrastructure puede contener:

```python
class OrderModel(models.Model):
    id = models.UUIDField(...)
    customer_id = models.UUIDField(...)
    status = models.CharField(...)
```

Se puede utilizar un mapper:

```text
OrderModel ↔ Order
```

Sin embargo, para mantener el MVP pragmático, no es obligatorio separar absolutamente todos los modelos Django desde el primer día.

Conviene hacerlo especialmente en dominios con lógica relevante como Sales.

---

# 14. API REST

Ejemplos de endpoints:

## Catalog

```text
GET    /api/products
POST   /api/products
GET    /api/products/{id}
PATCH  /api/products/{id}
POST   /api/products/{id}/activate
POST   /api/products/{id}/deactivate
```

## Customers

```text
GET    /api/customers
POST   /api/customers
GET    /api/customers/{id}
PATCH  /api/customers/{id}
POST   /api/customers/{id}/activate
POST   /api/customers/{id}/deactivate
```

## Sales

```text
GET    /api/orders
POST   /api/orders
GET    /api/orders/{id}

POST   /api/orders/{id}/items
DELETE /api/orders/{id}/items/{item_id}

POST   /api/orders/{id}/prepare
POST   /api/orders/{id}/ready
POST   /api/orders/{id}/deliver
POST   /api/orders/{id}/cancel

POST   /api/orders/{id}/payments
```

## Expenses

```text
GET    /api/expenses
POST   /api/expenses
PATCH  /api/expenses/{id}
DELETE /api/expenses/{id}

GET    /api/expense-categories
POST   /api/expense-categories
```

## Reporting

```text
GET /api/reports/dashboard
GET /api/reports/sales
GET /api/reports/expenses
GET /api/reports/profitability
```

---

# 15. Frontend Angular

Angular también debería organizarse por funcionalidad.

```text
src/app/

├── core/
│   ├── auth/
│   ├── interceptors/
│   └── layout/
│
├── shared/
│   ├── components/
│   ├── pipes/
│   └── directives/
│
└── features/
    ├── dashboard/
    ├── sales/
    ├── products/
    ├── customers/
    ├── expenses/
    └── reporting/
```

---

# 16. Angular: módulo Sales

```text
features/sales/
├── pages/
│   ├── order-list/
│   ├── order-detail/
│   └── order-create/
│
├── components/
│   ├── order-form/
│   ├── order-items/
│   ├── order-status/
│   └── payment-form/
│
├── services/
│   └── sales-api.service.ts
│
├── models/
│   ├── order.ts
│   └── payment.ts
│
└── sales.routes.ts
```

---

# 17. Angular: módulo Products

```text
features/products/
├── pages/
│   ├── product-list/
│   └── product-form/
├── components/
├── services/
│   └── products-api.service.ts
└── models/
```

---

# 18. Angular: módulo Customers

```text
features/customers/
├── pages/
│   ├── customer-list/
│   └── customer-detail/
├── components/
├── services/
└── models/
```

---

# 19. Angular: módulo Expenses

```text
features/expenses/
├── pages/
│   ├── expense-list/
│   └── expense-form/
├── components/
├── services/
└── models/
```

---

# 20. Angular: Reporting y Dashboard

```text
features/dashboard/
├── pages/
│   └── dashboard/
├── components/
│   ├── sales-summary/
│   ├── expense-summary/
│   ├── profit-summary/
│   └── pending-orders/
└── services/
```

---

# 21. Flujo ejemplo: Crear pedido

Frontend:

```text
OrderCreatePage
    ↓
SalesApiService
    ↓
POST /api/orders
```

Backend:

```text
API View
    ↓
CreateOrderCommand
    ↓
CreateOrderHandler
    ↓
Order Aggregate
    ↓
OrderRepository
    ↓
Django ORM
```

---

# 22. Flujo ejemplo: Registrar pago

```text
POST /api/orders/{id}/payments
```

Application:

```text
RegisterPayment
```

Dominio:

```text
Order / Payment
```

Reglas:

```text
payment.amount > 0
payment.amount <= saldo permitido
actualizar estado del pago
```

Resultado:

```text
PENDING
   ↓
PARTIAL
   ↓
PAID
```

---

# 23. MVP recomendado

## Fase 1

### Catalog

- crear producto;
- editar producto;
- listar productos;
- desactivar producto.

### Customers

- crear cliente;
- buscar cliente;
- editar cliente;
- historial básico.

### Sales

- crear pedido;
- agregar productos;
- cambiar estado;
- registrar pago;
- listar pedidos;
- filtrar pedidos.

### Expenses

- registrar gasto;
- categorías;
- filtros.

### Reporting

- ventas del periodo;
- gastos del periodo;
- ganancia estimada;
- pedidos pendientes;
- productos más vendidos.

---

# 24. Funcionalidades que NO deberían entrar inicialmente

Evitar en el MVP:

```text
Microservicios
Event Sourcing
CQRS completo
Kafka
Sagas
Contabilidad completa
Inventario avanzado
Producción avanzada
Facturación electrónica
WhatsApp automático
IA generativa
Multiempresa compleja
```

Estas capacidades pueden incorporarse cuando el producto haya validado su uso.

---

# 25. Evolución futura: Production

Cuando el sistema necesite controlar el costo real de fabricación de cuñapés, crear un nuevo bounded context:

```text
production/
```

Entidades posibles:

```text
Recipe
Ingredient
ProductionBatch
RecipeIngredient
```

Ejemplo:

```text
Recipe: Pack cuñapé tradicional

4 kg almidón
2 kg queso
20 huevos
2 litros leche
```

Production podrá calcular:

```text
Costo por lote
Costo unitario
Costo por producto
```

Reporting podrá consumir esa información para obtener margen real.

---

# 26. Evolución futura: Inventory

Nuevo bounded context:

```text
inventory/
```

Conceptos:

```text
StockItem
StockMovement
Warehouse
InventoryAdjustment
```

Production podrá consumir materias primas del inventario.

Sales podrá descontar productos terminados.

---

# 27. Evolución futura: Integrations

Nuevo bounded context:

```text
integrations/
```

Responsabilidades:

```text
WhatsApp
Facebook
Instagram
QR / pagos
notificaciones
```

Un mensaje de WhatsApp podría generar un:

```text
OrderDraft
```

que el usuario confirme antes de convertirlo en Order.

---

# 28. Convenciones

## Commands

Nombrar usando verbos:

```text
CreateOrder
DeliverOrder
CancelOrder
RegisterPayment
CreateExpense
```

## Queries

```text
GetOrder
ListOrders
SearchCustomers
GetDashboardSummary
```

## Domain Events

Pasado:

```text
OrderCreated
OrderDelivered
PaymentRegistered
ExpenseCreated
```

---

# 29. Regla principal del proyecto

DDD debe ayudar a expresar el negocio.

Si una abstracción no representa una necesidad real del negocio, no debe introducirse todavía.

La prioridad del proyecto será:

```text
claridad del dominio
    >
separación modular
    >
testabilidad
    >
velocidad de evolución
    >
pureza arquitectónica
```

---

# 30. Arquitectura objetivo del MVP

```text
Angular
   │
   │ REST
   ▼
Django REST Framework
   │
   ├── Catalog
   ├── Customers
   ├── Sales
   ├── Expenses
   └── Reporting
           │
           ▼
       PostgreSQL
```

Todo desplegado inicialmente como un monolito modular.

---

# 31. Resumen

La arquitectura recomendada es:

```text
Monolito modular
+
DDD pragmático
+
módulos por capacidad de negocio
+
Django REST Framework
+
Angular
+
PostgreSQL
```

Bounded Contexts del MVP:

```text
Catalog
Customers
Sales
Expenses
Reporting
```

Posteriormente:

```text
Production
Inventory
Suppliers
Marketing
Integrations
Accounting
```

El sistema debe comenzar resolviendo las necesidades reales del emprendimiento y evolucionar gradualmente hacia un SaaS genérico para pequeños negocios.
