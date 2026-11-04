# DDR-refinar-ux-pedidos-ventas-lista-y-detalle: Detalle orientado a la siguiente acción y lista compacta

**Estado:** Propuesto
**Task relacionado:** TASK-refinar-ux-pedidos-ventas
**Fecha:** 2026-11-04

## Contexto
El detalle de un pedido es una pila de tarjetas del mismo peso: la información que decide la acción (productos, total, saldo) queda debajo de «Datos del pedido», y «Registrar pago» está al final de la página, lejos del saldo. Un pedido recién creado (sin líneas, total 0) muestra «Sin saldo» en verde, que sugiere «todo cobrado». La lista ocupa dos filas de filtros con un solo pedido y la fila no es clicable.

## Pantallas/flujos afectados
Detalle de pedido (`order-detail`, `order-items`, `order-summary`, `order-payments`) y lista de pedidos (`order-list`). El formulario y el modal de entrega no cambian salvo lo indicado. Sin cambios de rutas ni de API.

## Componentes/patrones elegidos
Base: plantillas Detalle y Lista de `design-system.md` §5, botones de §3, badges existentes. Ningún componente nuevo.

### Detalle
1. **Orden de tarjetas:** Entrega + Cobro → Productos → Importes → Pagos → Salida de inventario (si existe) → **Datos del pedido** al final. Alerta de cancelado y avisos REQ-SAL-016 se conservan encima.
2. **Cobro con acción:** si `order.canRegisterPayment`, la tarjeta Cobro muestra «Registrar pago» (`btn-primary btn-sm`) junto al saldo; al pulsarlo abre el formulario de Pagos y hace scroll hasta él. El botón de la cabecera de Pagos se mantiene (misma acción, mismo método).
3. **Estado sin productos:** con `items.length === 0`, Cobro muestra «Sin productos» en `text-muted` (no «Sin saldo» verde) y no ofrece registrar pago. «Sin saldo» en verde solo con total > 0.
4. **Una acción primaria sólida por vista:** la acción de estado (cabecera) sigue siendo `btn-primary`; «Editar datos», «Aplicar» y «Agregar» pasan a `btn-outline-primary`. «Registrar pago» (Cobro) es la excepción justificada: es la acción siguiente cuando hay saldo y la de estado ya no aplica (Entregado) o convive con ella; se documenta como par en el PR.
3b. **Sin productos → foco:** con pedido editable y sin líneas, el buscador de producto recibe foco al cargar el detalle.
5. **Datos del pedido compactos:** `dl` con Cliente, Canal, Fecha del pedido, Entrega prevista omitida (ya está en Entrega) y Notas; «Creado» y «Última actualización» pasan a una línea `small.text-muted` al pie de la tarjeta.
6. **Fecha de pagos** con `date: 'dd/MM/yyyy'`.
7. **Quitar línea:** confirmación antes de eliminar (mismo patrón de diálogo que «Cancelar pedido»).

### Lista
1. **Identificador:** la columna Pedido muestra el **código** como enlace en negrita y la fecha del pedido como `small.text-muted` debajo.
2. **Fila clicable:** clic en la fila navega al detalle (`ngx-datatable` `(activate)` de tipo `click`); el icono «ojo» y el enlace se mantienen para teclado/lector de pantalla.
3. **Filtros:** visibles siempre los atajos, Estado de entrega, Estado de pago y Cliente; Canal, Fecha de, Desde y Hasta bajo un botón «Más filtros» (`aria-expanded`), abierto por defecto si alguno está activo. «Limpiar filtros» se mantiene.
4. El botón «+» se mantiene icon-only (sistema de diseño §3) con `title`/`aria-label` existentes.

## Alternativas consideradas
- **Alta con líneas en el mismo formulario** (patrón `stock-opening`): descartada aquí; requiere contrato de creación con ítems en el backend. Se mitiga con foco al buscador y estado «Sin productos». Candidata a un task con backend.
- **Fusionar Entrega y Cobro en una barra resumen**: descartada; las dos tarjetas ya funcionan y el cambio es mayor sin ganancia clara.
- **Buscador de texto en la lista:** descartado; la API no lo soporta (ver TASK).

## Comportamiento por privilegio/estado
La interfaz solo refleja `editable`, `allowedTransitions` y `canRegisterPayment` del servidor; no replica reglas. El backend sigue validando (409 y 403). Estados: cargando («Cargando…»), vacío (lista: mensaje existente; detalle: «Sin productos»), error (toast y mensajes por campo existentes), éxito (toasts existentes).

## Consecuencias
- Cambio solo visual: sin migración de datos.
- Deuda aceptada: la edición de líneas en pedidos Listos o ya pagados sigue dependiendo de `editable` del servidor (decisión de negocio pendiente, fuera de alcance); el alta no permite agregar productos en el mismo paso.
- Si el patrón «Cobro con acción» se repite en Compras, moverlo a `shared/`.
