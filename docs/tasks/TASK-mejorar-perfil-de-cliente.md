# TASK-mejorar-perfil-de-cliente: Perfil de cliente accionable con resumen de compras y saldo

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-mejorar-perfil-de-cliente
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/53

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-04 | (nuevo) → INVESTIGATION | Task creado a partir de la crítica de diseño de la pantalla de perfil de cliente | delivery-start |
| 2026-11-04 | INVESTIGATION → DESIGN → PLANNING | Veredicto NEEDS_PLAN, DDR y PLAN v1 escritos; Specification READY | delivery-start |
| 2026-11-04 | PLANNING → ENGINEERING | Plan listo para implementar | delivery-start |
| 2026-11-04 | ENGINEERING → REVIEW | Implementación completa según PLAN v1 | delivery-build |

## Investigación

### Requerimiento
Sin argumento explícito: el requerimiento es la crítica de diseño previa de la página «Perfil del cliente» (captura adjunta por el usuario, etapa de refinamiento). Objetivo: mejorar usabilidad, jerarquía de información y presentación **conservando la funcionalidad y el sistema de diseño**, de modo que el perfil responda: quién es y cómo contactarlo, su actividad de compra, cuándo compró por última vez, cómo encontrar/inspeccionar un pedido y qué acciones hay. Distinguir total, estado de pago y saldo pendiente; cubrir cliente sin compras, historiales largos, responsive y accesibilidad. Textos de cara al usuario en español (con es/en/pt). Solo se recomiendan métricas respaldadas por datos existentes. Esto es insumo, no una Specification aprobada.

### Hechos encontrados
- `frontend/panel_admin/src/app/features/customers/pages/customer-detail/customer-detail.component.html:22-43` — datos en `dl.row` con 7 filas (Nombre duplicado del `h4`, teléfono y correo como texto plano, Creado/Actualizado con el mismo peso que el contacto).
- `customer-detail.component.html:44-50` — acciones (Editar primario, Desactivar `btn-warning`, Volver) bajo los datos; no hay acción para crear un pedido.
- `frontend/panel_admin/src/app/features/customers/components/customer-purchase-history/customer-purchase-history.component.html:11-31` — tabla con Fecha (enlace al pedido), Total, Estado y Pago como texto plano; sin saldo ni código de pedido.
- `customer-purchase-history.component.html:33-37` y `38-40` — nota «Se muestran los N pedidos más recientes de M» y estado vacío de una frase.
- `frontend/panel_admin/src/app/features/customers/services/customer-orders-api.service.ts:10,38-55` — consulta `GET /api/orders/?customer_id=…&page_size=100`; el DTO local solo mapea `id`, `order_date`, `total`, `status`, `payment_status`.
- `frontend/panel_admin/src/app/features/customers/models/customer.ts:45-55` — `CustomerOrderSummary { id, date, total, status, paymentStatus }`.
- **El backend ya entrega lo que falta:** `backend/modules/sales/api/serializers.py:165-175` (`OrderSummarySerializer`) devuelve `paid_total` y `balance`; `serializers.py:64-68` añade `code` (`order_code(obj.id)`); `frontend/.../sales/services/orders-api.service.ts:161-175` ya los mapea para Sales. **No hace falta cambio de backend** (corrige la estimación de la crítica previa, que lo daba por necesario).
- `backend/modules/sales/api/filters.py:53` y `backend/modules/sales/domain/repositories.py:15` — filtro `customer_id` y orden por defecto más reciente primero.
- `backend/modules/sales/infrastructure/django/read_queries.py:17-20` — regla de negocio existente de «pedido válido» para totales: excluye `CANCELLED` (y pedidos sin ítems).
- `frontend/.../sales/pages/order-list/order-list-filters.ts:87,122-128` — la lista de pedidos ya acepta `customer` y `customer_name` por query string.
- `frontend/.../sales/pages/order-form/order-form.component.ts:75-118` — el formulario de pedido no lee query params; el cliente se elige con `ng-select` (solo clientes activos, líneas 76-85).
- `frontend/.../sales/components/{order,payment}-status-badge/*.ts` — badges con texto + icono; su `input` está tipado con `OrderStatus`/`PaymentStatus` de Sales (los usa `order-list`, `order-detail` y el dashboard).
- `frontend/panel_admin/src/app/shared/pipes/money.pipe.ts` — pipe `money` estándar (`Bs 70.00`, vacío → `—`). No existe ninguna utilidad de suma decimal en el frontend ni librería decimal en `package.json`.
- `docs/design/design-system.md` secciones 3 (badges, `money`), 5 (plantilla de Detalle: `dl.row`, acciones bajo los datos, «Sin …») y 4 (estados).
- `docs/adr/ADR-clientes-mvp-historial-compras.md:11-13,19` — Customers no importa Sales en backend; el historial lo consume el frontend desde `/api/orders/`; la alternativa de agregados en servidor se difirió hasta que el perfil «necesite agregados (total comprado, última compra)».
- No hay teléfono con enlace `tel:`/WhatsApp en ninguna plantilla de la app (Grep sin resultados fuera de plantillas de ejemplo).

### Hipótesis / supuestos no confirmados
- El teléfono se guarda normalizado en formato internacional (`+591…`, ver `CUSTOMER_FORM.SE_GUARDARA_NORMALIZADO…`); se asume que quitar todo lo que no sea dígito da un número válido para `wa.me`.
- Los importes de la API son cadenas decimales de 2 posiciones (`_money()`); la suma en el frontend se hará sobre enteros mínimos (sin `float`).
- Con el módulo Pedidos deshabilitado, `GET /api/orders/` fallaría; el historial ya maneja el error sin ocultar el perfil. Se confirmará en build cómo ocultar «Nuevo pedido» (`ModulesService`).

### Módulos y dependencias relacionadas
Frontend `features/customers` (detalle + historial), `features/sales` (formulario de pedido, lista de pedidos, badges), `shared/pipes/money`. Backend: ninguno.

### Implementaciones similares existentes
Detalle de producto (`features/products/pages/product-detail`), tarjetas de cifras del dashboard (`features/reporting`, `app-report-card`) y tabla apilada en móvil (`features/inventory/components/_inventory-table.scss`).

### Comportamiento actual
Ver «Hechos encontrados»: el perfil muestra datos y una tabla básica; no hay acciones de contacto ni de crear pedido, ni resumen, ni saldo.

### Restricciones
`CLAUDE.md`: sin texto hardcodeado (claves es/en/pt + `npm run i18n:check`), `tr()` solo en funciones, dinero sin `float`, sin `any`, Reactive Forms, sin suscripciones colgadas, avisar antes de instalar dependencias (no se instala ninguna).

### Riesgos identificados
- Agregados calculados sobre los 100 pedidos cargados: si el cliente tiene más, serían parciales (se avisa en pantalla).
- Cruce de límites entre `features/customers` y `features/sales` en el frontend (ya hay precedente con Reporting y la lista de pedidos).

### Veredicto de complejidad
**NEEDS_PLAN** — cambio acotado al frontend (customers y un prefill en el formulario de pedido), sin decisión arquitectónica nueva, sin cambios de API, datos ni permisos.

### Diseño requerido
**SI** — reorganiza una pantalla existente (jerarquía, tarjetas de cifras, tabla con estados) y debe seguir el sistema de diseño.

## Diseño
Ver `docs/design/DDR-mejorar-perfil-de-cliente-perfil-accionable.md`.

## Arquitectura
No aplica según veredicto.

## Plan
Ver `docs/plans/PLAN-2026-11-04-mejorar-perfil-de-cliente.md` (v1, COMPLETO: cálculo financiero y frontera entre contextos).

## Implementación

Resumen: perfil de cliente rehecho solo en frontend, según el DDR y el PLAN v1. Sin cambios de backend ni de API.

| Parte | Cubre |
|---|---|
| `shared/utils/decimal-sum.ts` (+spec): suma decimal sobre enteros (`BigInt`), sin `float` | INV-01 |
| `customers/models/customer-purchase-summary.ts` (+spec): `summarizePurchases` (excluye cancelados, última fecha, conteo, total, saldo) y `whatsappUrl` | AC-02, AC-03, INV-01, EDGE-02, EDGE-03 |
| `customer.ts` y `customer-orders-api.service.ts` (+spec): leen `code`, `paid_total`, `balance` del contrato existente | API-01 |
| `customer-purchase-history` (html, ts, nuevo scss, spec): columnas Pedido/Fecha/Total/Pagado/Saldo/Entrega/Pago con badges de Sales, cancelados atenuados con saldo «—», pie «Pedidos mostrados: X de Y», enlace «Ver todos los pedidos», vacío con «Crear primer pedido», tabla apilada en móvil, `caption` y `scope="col"` | AC-04, AC-05, AC-06, AC-09, EDGE-01, EDGE-05 |
| `customer-detail` (html, ts, spec): acciones en la cabecera (Nuevo pedido primario, Editar `btn-light`, Desactivar), contacto con `tel:`/WhatsApp/`mailto:`, «Sin …», tira de 4 cifras con `app-report-card`, aviso de cifras parciales, pie de auditoría, sin «Volver» ni fila «Nombre» | AC-01, AC-02, AC-03, AC-05, AC-07, AC-08, EDGE-04 |
| `order-form.component.ts` (+spec): preselecciona el cliente desde `?customer=&customer_name=` solo en alta y con Clientes habilitado | AC-07 |
| `assets/i18n/{es,en,pt}.json`: claves nuevas en las tres; se retiran `BS` y `SE_MUESTRAN_LOS_PEDIDOS_MAS` del historial por quedar sin uso | AC-10 |

Pantalla de referencia: `product-detail` (plantilla Detalle) y `features/reporting` (cifras con `app-report-card`). Reutilizados: `app-report-card`, `app-order-status-badge`, `app-payment-status-badge`, pipe `money`, patrón de tabla apilada de inventario (copiado en un scss del componente).

### Desviaciones respecto al plan
- «Pedidos mostrados: X de Y» sustituye la nota anterior «Se muestran los N pedidos más recientes de M»; el aviso de cifras parciales vive en el detalle («Calculado con los N pedidos más recientes»), no en el historial.
- Con error del historial se oculta la tira de cifras completa (no se muestran tarjetas en «error»).
- Se añadió `hasOutstandingBalance` al resumen (decide el color/texto del saldo sin comparar con coma flotante).
- No se movió `app-report-card` a `shared/`: se importa desde Reporting (queda como deuda abajo).

### Deuda técnica
- `app-report-card`, `app-order-status-badge` y `app-payment-status-badge` se importan desde `features/reporting` y `features/sales` en `features/customers`; según el sistema de diseño deberían moverse a `shared/`.
- Las cifras usan los pedidos cargados (hasta 100); un agregado en servidor sigue pendiente (ADR historial-compras).
- Estilo de tabla apilada duplicado en dos scss (inventario e historial de clientes).
- `docs/design/design-system.md` no se actualizó: «Nuevo pedido» como acción primaria en detalles queda como desviación del DDR.

### Verificación propia (no es el Quality Gate)
`npm run i18n:check` (0 faltantes), `npm run lint` (limpio), `npm run build` (ok) y `npm test`: 1182 pruebas en verde y 1 fallo ya existente en `origin/main` (`core/i18n/screens-i18n.spec.ts:60`, «labels coming from code follow the active language»; se reproduce aislado en un checkout limpio de `main`, no relacionado con este cambio). No se revisó visualmente en el navegador.

### Incidencia de entorno
Para ejecutar las pruebas en este worktree se enlazó el `node_modules` del checkout principal (junction) y, al borrar un worktree temporal con `git worktree remove --force`, Git borró por el enlace una parte de `E:\dore-mini-erp\frontend\panel_admin\node_modules` (los paquetes `@algolia` a `@angular` y otros). Después `npm ci` en el checkout principal falló al encontrar procesos `esbuild` en uso. Este worktree tiene ahora su propio `node_modules` (`npm ci`). El checkout principal necesita `npm ci` con esos procesos detenidos. No afecta a los archivos versionados.

## Review
_Pendiente_

## Publicación
_Pendiente_
