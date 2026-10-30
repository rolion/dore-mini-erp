# TASK-confirmar-cancelar-compras: Confirmar o cancelar compras con reglas explícitas (PB-COM-003)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-confirmar-cancelar-compras
**Pull Request:** _se asigna al abrir el PR_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-30 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-10-30 | INVESTIGATION → DESIGN | Veredicto NEEDS_ARCHITECTURE; diseño requerido | delivery-start |
| 2026-10-30 | DESIGN → ARCHITECTURE | DDR escrito | delivery-start |
| 2026-10-30 | ARCHITECTURE → PLANNING | ADR escrito | delivery-start |
| 2026-10-30 | PLANNING → ENGINEERING | Specification READY; PLAN v1 y PR abiertos | delivery-start |

## Investigación

### Requerimiento
PB-COM-003 · Confirmar o cancelar compras con reglas explícitas (Módulo Compras, P1, dependencia PB-COM-002). Como administrador, confirmar o cancelar compras para controlar su ciclo de vida.

- Vista: detalle de Compra, pestaña «Resumen», con cabecera e ítems.
- Datos: referencia interna, proveedor, fecha, referencia externa, estado documental, estado de recepción, estado de pago, ítems, total y notas; si está cancelada, motivo y fecha de cancelación.
- Acciones por estado: Borrador → Editar, Confirmar, Cancelar. Confirmado → Registrar recepción, Registrar pago; Cancelar solo si no hay recepciones ni pagos confirmados. Cancelado → solo lectura.
- Diálogos: confirmar muestra resumen y avisa que precios/cantidades quedan bloqueados; cancelar exige motivo antes de habilitar la confirmación.
- Interfaz: los botones reflejan el estado y el backend valida las mismas reglas; una compra confirmada no ofrece edición de ítems ni muestra aumento de stock por confirmarla.
- AC: (1) confirmar exige proveedor activo y ≥ 1 ítem válido; una confirmada no permite editar cantidades ni precios; (2) cancelar exige motivo y solo sin recepciones ni pagos confirmados; (3) confirmar no incrementa existencias y repetir la acción no duplica documentos.

### Hechos encontrados
- PB-COM-002 está en `main` (PR #28, `5be4232`). Mi rama partía de `a9dd1d4` y se avanzó por fast-forward a `origin/main`.
- `Purchase` es un agregado con `status: PurchaseStatus` y un solo valor, `DRAFT` (`backend/modules/purchases/domain/enums.py:4-5`); `editable` e `ensure_editable()` ya bloquean la edición fuera de borrador (`domain/purchase.py:210-216`) y lanzan `PurchaseNotEditable`, que la vista traduce a 409 «La compra ya no admite cambios.» (`api/purchase_views.py:20-27,54-55`). `PurchaseDetailView.patch` ya depende de ello.
- No hay transiciones: «el estado cambia solo por métodos del agregado (hoy no hay transiciones)» (PLAN PB-COM-002, INV-09). «Confirmar, cancelar o eliminar compras» y «recepción y pagos» quedaron fuera de alcance (PLAN PB-COM-002, Out of scope).
- Reglas entre agregados en la capa de aplicación: `_supplier_errors` valida proveedor existente y activo con el mensaje `SUPPLIER_NOT_ACTIVE` (`application/purchase_commands.py:11-28`); los casos de uso se ejecutan en `transaction.atomic` con `select_for_update` (`api/purchase_views.py:41-50`, `infrastructure/django/purchase_repository.py:46-52`).
- `PurchaseModel` solo tiene `status` (default `draft`), `total`, timestamps (`infrastructure/django/models.py:25-46`); migraciones `0001_initial`, `0002_purchase`. No existen columnas de motivo/fecha de cancelación, ni de recepción ni de pago.
- No existen recepciones ni pagos de compras: Inventario no recibe compras y Gastos no las referencia; `purchases` no importa `inventory` ni `expenses` (`sales/tests/test_boundaries.py:17,24`).
- La detalle actual (`purchase-detail.component.html`) es una sola tarjeta sin pestañas, con «Editar» si `editable` y badge de estado fijo en naranja; `PurchaseStatus = 'draft'` en el frontend (`features/purchases/models/purchase.ts:6-10`). El DDR de PB-COM-002 dejó dicho que «el detalle incorporará la task de confirmación».
- Patrón de ciclo de vida a seguir: `Order.cancel(reason, now)` con motivo obligatorio ≤ 500, `cancellation_reason`, `cancelled_at`, `allowed_transitions` en la API y endpoints `POST /<id>/cancel/` (`sales/domain/order.py:13,179-180,336-344`, `sales/api/urls.py:28`); en la UI, `askCancelReason` con SweetAlert y `DeliveryDialogComponent` con `NgbModal` (`sales/pages/order-detail/order-detail.component.ts:177-262`).
- No hay numeración de documentos en el sistema (compras ni pedidos); PB-COM-002 la dejó fuera de alcance.
- Pestañas existentes con `ngbNav`: `settings/pages/module-list`, `inventory/pages/inventory-configuration`.

### Hipótesis / supuestos no confirmados (decisiones del plan, reversibles)
- H-01 **Referencia interna** = código derivado y estable `COM-` + primeros 8 caracteres hex en mayúsculas del `id`; sin columna ni contador (la numeración correlativa queda para una task propia).
- H-02 **Recepción y pago** no existen todavía: la compra guarda `reception_status` (`not_received`, `partial`, `received`) y `payment_status` (`unpaid`, `partial`, `paid`), siempre `not_received`/`unpaid` en esta task, y la cancelación se bloquea si cualquiera es distinto del inicial. Las tasks de recepción y pago serán quienes los muevan. «Registrar recepción» y «Registrar pago» se muestran deshabilitados («Disponible próximamente») en una compra confirmada.
- H-03 Cancelar se permite desde Borrador y desde Confirmado (si no hay recepciones ni pagos). Cancelado es terminal.
- H-04 Confirmar **no** vuelve a comprobar que los productos de las líneas sigan activos o comprables (un producto desactivado conserva su línea, PB-COM-002 AC-07/EDGE-04); «ítem válido» = línea que ya cumple las reglas de cantidad, precio y snapshot del borrador. El total puede ser 0.00 si hay precios en 0.
- H-05 Una compra confirmada es de solo lectura completa (cabecera y notas también), no solo cantidades y precios.
- H-06 Idempotencia: confirmar una compra ya confirmada y cancelar una ya cancelada responden 200 con el estado actual y **no cambian nada** (ni fecha ni motivo originales); confirmar una cancelada y cancelar con recepciones/pagos responden 409.
- H-07 Motivo: obligatorio, recortado, ≤ 500 caracteres (igual que pedidos).

### Módulos y dependencias relacionadas
Solo `purchases` (dominio, aplicación, infraestructura, API) y el feature Angular `purchases`. Lectura de `suppliers` dentro del mismo contexto. No se toca `inventory`, `expenses` ni `catalog`.

### Implementaciones similares existentes
`Order.cancel`/`OrderCancelView` (Ventas) para motivo, fecha y tratamiento de errores; `DeliveryDialogComponent` (NgbModal) para diálogos con resumen; `ngbNav` de Configuración para pestañas.

### Comportamiento actual
Una compra solo puede crearse y editarse como borrador; no hay forma de cerrarla, bloquearla ni cancelarla.

### Restricciones
`Decimal` para dinero; no editar migraciones aplicadas (`0003` nueva, aditiva); aislamiento por `company_id`; estados solo por métodos del agregado; el dominio no importa Django; no instalar dependencias.

### Riesgos identificados
- Doble clic o dos pestañas confirmando/cancelando a la vez (mitigado con `select_for_update` + idempotencia).
- Los estados de recepción/pago son «preparatorios»: cuando existan sus tasks habrá que definir qué es una recepción o pago «confirmado» (H-02).
- La lista y los badges del frontend asumen un único estado.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — introduce las primeras transiciones de estado del agregado, una migración con columnas de ciclo de vida, tres endpoints/contrato nuevos y reglas financieras-operativas (bloqueo de edición, cancelación condicionada) que otras tasks de Compras extenderán.

### Diseño requerido
**SI** — el detalle gana pestaña «Resumen», acciones por estado y dos diálogos nuevos.

## Diseño
Ver [DDR](../design/DDR-confirmar-cancelar-compras-detalle-y-dialogos.md).

## Arquitectura
Ver [ADR](../adr/ADR-confirmar-cancelar-compras-ciclo-de-vida-y-contrato.md).

## Plan
[PLAN-2026-10-30-confirmar-cancelar-compras](../plans/PLAN-2026-10-30-confirmar-cancelar-compras.md) (v1, COMPLETO). Specification readiness: READY.

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
