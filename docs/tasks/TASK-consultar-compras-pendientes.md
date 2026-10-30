# TASK-consultar-compras-pendientes: Consultar compras y sus pendientes (PB-COM-006)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-consultar-compras-pendientes
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/39
**Fuente:** https://trello.com/c/NsnM22Wj/20-pb-com-006-consultar-compras-y-sus-pendientes

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-30 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta de Trello | delivery-start |
| 2026-10-30 | INVESTIGATION → DESIGN | Veredicto NEEDS_PLAN; diseño requerido (lista con filtros) | delivery-start |
| 2026-10-30 | DESIGN → PLANNING | DDR escrito; no hay decisión arquitectónica nueva | delivery-start |
| 2026-10-30 | PLANNING → ENGINEERING | Specification READY; PLAN v1 y PR | delivery-start |

## Investigación

### Requerimiento
Fuente: https://trello.com/c/NsnM22Wj (tarjeta «PB-COM-006 · Consultar compras y sus pendientes», módulo Compras, P1, dependencias PB-COM-004 y PB-COM-005). El contenido de la tarjeta es **insumo**, no una Specification aprobada.

Historia: como usuario, quiero listar y consultar compras para dar seguimiento a proveedores, recepciones y pagos.

- **Vistas:** Compras → Compras, listado principal y detalle con pestañas «Resumen», «Recepciones» y «Pagos» (consolidan PB-COM-002…005).
- **Columnas de la lista:** referencia, fecha, proveedor, total, recibido/pendiente, estado documental, estado de recepción, estado de pago y saldo. El recibido/pendiente se consulta por línea en el detalle; en la lista se resume el estado, **sin sumar cantidades de unidades distintas**.
- **Filtros:** proveedor, rango de fecha de compra, estado documental, estado de recepción y estado de pago; búsqueda por referencia interna/externa. **Acciones:** Nueva compra y Ver detalle.
- **Resumen del detalle:** proveedor y fecha, totales, tres estados separados; Resumen = ítems y notas, Recepciones = seguimiento físico, Pagos = saldo financiero.
- **Interfaz:** combinar «Recepción completa» y «Pago pendiente» devuelve compras recibidas aún por pagar. Sin resultados: mostrar filtros aplicados, «Limpiar filtros» y acceso a Nueva compra.
- **AC de la tarjeta:** (1) la lista filtra por proveedor, fechas, estado documental, recepción y pago; (2) el detalle muestra ítems y totales, cantidades recibidas y pendientes, pagos y saldo; (3) una compra recibida puede estar impaga y una pagada puede estar pendiente de recepción; los estados se muestran separados.
- Sin checklists ni comentarios. Los documentos de Google enlazados no son accesibles desde el conector (no consultados).

### Hechos encontrados
- PB-COM-004 y PB-COM-005 ya están en `main` (merge `382c25a`, PR #38). El **detalle ya cumple casi todo**: pestañas Resumen/Recepciones/Pagos (`frontend/panel_admin/src/app/features/purchases/pages/purchase-detail/purchase-detail.component.html:27-45`), ítems con Recibida/Pendiente por línea y total (misma plantilla, tabla «Productos»), tres estados en filas separadas (`reception-status`, `payment-status`), y la API del detalle expone `reception_status`, `payment_status`, `paid_total` y `balance` (`backend/modules/purchases/api/purchase_serializers.py:70-88`; `application/purchase_queries.py`, `PurchaseDetail.balance`).
- La **lista es lo que falta**: solo tiene columnas Fecha, Proveedor, Referencia (externa), Total, Estado (documental) y Acciones (`purchase-list.component.html:55-90`); no muestra referencia interna, estado de recepción, estado de pago ni saldo. Su único filtro es `?supplierId=` (`purchase-list.component.ts:40-60`).
- API de lista: `GET /api/purchases/` solo acepta `supplier_id` (`backend/modules/purchases/api/purchase_views.py`, `PurchaseListCreateView.get`) y devuelve `PurchaseSummary` con id, fecha, proveedor, referencia externa, total, estado e `items_count` (`domain/repositories.py:13-26`; `api/purchase_serializers.py`, `summary_representation`). Paginación `SupplierPagination` (`api/pagination.py`).
- Repositorio: `DjangoPurchaseRepository.list` devuelve una vista perezosa `PurchaseList` sobre un queryset con `annotate(items_count=Count('items'))` y orden `-purchase_date, -created_at, id` (`infrastructure/django/purchase_repository.py:14-81`). `payment_status` y `reception_status` están **persistidos** en `purchases_purchase` (`infrastructure/django/models.py:40-41`) y el índice `(company_id, purchase_date)` ya existe. El total pagado vive en `purchases_payment` (`PaymentModel`, `models.py:109-126`; `DjangoPaymentRepository.paid_total`, `payment_repository.py:43`).
- La **referencia interna** no está persistida: es `COM-` + 8 primeros hex mayúsculos del id (`domain/purchase.py`, propiedad `reference`). Buscarla exige comparar contra el texto del id en la consulta.
- Precedente de lista con filtros y rango de fechas validado: `parse_order_filters` en Ventas, con `date_from/date_to`, `has_balance` y rechazo de rango invertido (`backend/modules/sales/api/filters.py:36-86`); en el frontend `order-list-filters.ts` y `order-list.component.html:43-96` (formulario de filtros, «Limpiar filtros»). Pantalla de referencia del sistema de diseño: «Lista de solo lectura con filtros» (`docs/design/design-system.md`, sección 5).
- Etiquetas de estados en el frontend: `PAYMENT_STATUS_LABELS` / `RECEPTION_STATUS_LABELS` (`models/purchase.ts:27-37`).
- Todo es de Compras; `test_boundaries` no cambia.

### Hipótesis / supuestos no confirmados
Reversibles con aprobación del usuario; ninguno bloquea:
- **H-01** Los estados de recepción y pago y el saldo solo aplican a compras **confirmadas**. En borrador y canceladas la lista muestra «—» en esas tres columnas (un borrador «Sin pagar» sería engañoso). Consecuencia: filtrar por recepción o por pago devuelve solo compras confirmadas.
- **H-02** El filtro de pago ofrece los tres estados (Sin pagar, Pago parcial, Pagada) y la opción **«Pago pendiente»** = `unpaid` + `partial` (saldo > 0), la combinación citada por la tarjeta. La recepción ofrece los tres estados; «Recepción completa» = `received`.
- **H-03** «Recibido/pendiente» en la lista = una columna con el **estado de recepción** (badge); el detalle por línea ya existe. No se suman cantidades.
- **H-04** Saldo en la lista = total − suma de pagos confirmados, calculado en la consulta (no se persiste). Compra confirmada sin pagos: saldo = total.
- **H-05** El rango de fechas filtra por `purchase_date` (inclusivo); `desde > hasta` → 400.
- **H-06** Búsqueda `q`: coincidencia parcial, sin distinguir mayúsculas, sobre la referencia externa; y, si el texto (con o sin prefijo `COM-`) son 1-8 caracteres hexadecimales, por **prefijo** de la referencia interna. Se recorta; vacío = sin búsqueda.
- **H-07** Los filtros viven en la URL (query params) para conservarlos al volver del detalle; el actual `?supplierId=` se mantiene.
- **H-08** Estado documental: Borrador, Confirmada, Cancelada (valores existentes).

### Módulos y dependencias relacionadas
Solo Compras (`backend/modules/purchases/`, `frontend/panel_admin/src/app/features/purchases/`). Sin Inventario, Gastos ni Catálogo.

### Implementaciones similares existentes
Lista de pedidos de Ventas con filtros (`order-list`), lista de movimientos de Inventario (`movement-list`), badges de estado de pago de Ventas (`app-payment-status-badge`).

### Comportamiento actual
La lista de compras no permite filtrar por nada salvo proveedor, ni ver recepción, pago o saldo; no tiene búsqueda ni estado vacío con filtros. El detalle ya consolida resumen, recepciones y pagos.

### Restricciones
`CLAUDE.md`: aislamiento por `company_id` en toda consulta, dinero en `Decimal`, no editar migraciones aplicadas (esta task no necesita migración), serializers validan forma y tipos, frontend con Reactive Forms y tipos explícitos, sin dependencias nuevas. Contrato de lista **compatible hacia atrás** (solo se añaden campos y parámetros opcionales).

### Riesgos identificados
- Rendimiento del saldo (agregado de pagos por fila): subconsulta correlacionada acotada por `company_id` y `purchase_id`; índice existente `purch_payment_company_purch`.
- Búsqueda por referencia interna sobre `id::text`: sin índice, pero acotada por `company_id`; aceptable en el volumen del MVP.
- Que los filtros de recepción/pago excluyan borradores (H-01) puede sorprender; se explica en la interfaz.

### Veredicto de complejidad
**NEEDS_PLAN** — cambio acotado a un módulo: ampliar el contrato de la lista (campos y filtros opcionales, sin migración) y la pantalla de lista; sin decisión arquitectónica nueva. No hay ADR.

### Diseño requerido
**SI** — la lista cambia de forma visible (columnas nuevas, barra de filtros, estado vacío con filtros aplicados).

## Diseño
`docs/design/DDR-consultar-compras-pendientes-lista-con-filtros-y-estados.md`.

## Arquitectura
No aplica según veredicto.

## Plan
`docs/plans/PLAN-2026-10-30-consultar-compras-pendientes.md` (v1, COMPLETO por tocar el contrato API). Specification readiness: READY.

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
