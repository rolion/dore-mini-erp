# DDR-contabilizar-ventas-cobros-sin-duplicar-errores-accionables-en-detalle-de-pedido: Rechazos contables accionables en el detalle del pedido

**Estado:** Propuesto
**Task relacionado:** TASK-contabilizar-ventas-cobros-sin-duplicar
**Fecha:** 2026-11-17

## Contexto
No hay pantallas nuevas. El backend puede rechazar acciones del pedido por motivos contables (409 con `code`/`detail` y, para configuración faltante, `issues`). La configuración de cuentas de Ventas ya existe (pestaña «Asientos automáticos», CONT-12). La persona debe entender qué falta y adónde ir.

## Pantallas/flujos afectados
- `features/sales/pages/order-detail` (acciones Confirmar, Agregar/editar ítems y descuento, Cancelar) y `components/order-payments` (Registrar pago).

## Componentes/patrones elegidos
- Patrón de errores 409 que ya usa el detalle del pedido (alerta tenue sobre las acciones; `design-system.md` §5, «Detalle» y deuda de alerta tenue/contraste AA).
- Para `posting_configuration_missing`: la alerta lista cada `issue.message` y añade un enlace «Ir a Configuración de Ventas» (`RouterLink` a la configuración de Ventas, pestaña Asientos automáticos), como ya enlaza el panel a Cuentas.
- Resto de códigos (`order_not_confirmed`, `order_total_locked`, `order_has_payments_posted`, `payment_date_not_covered`, errores del motor): solo el `detail` del backend en la misma alerta.
- Texto fijo nuevo (etiqueta del enlace, título de la alerta) con claves `translate` en es/en/pt.

## Alternativas consideradas
- **Deshabilitar botones de antemano:** requiere que el detalle conozca la cobertura/configuración de Contabilidad; mezcla módulos en el frontend y duplica reglas. Descartado; el servidor decide y la alerta explica.
- **Endpoint de «preparación» previo a confirmar:** útil pero fuera del alcance de la tarjeta; queda como mejora.

## Comportamiento por privilegio/estado
Sin diferencias por rol (mismo permiso por defecto que Ventas). **El backend es la barrera**: el frontend solo muestra el rechazo. Con Contabilidad deshabilitada o sin cobertura no aparece nada nuevo.

## Consecuencias
Los mensajes de configuración faltante llegan en español desde Contabilidad (deuda declarada en CONT-12 REV-05). Sin patrón nuevo ni cambio en `design-system.md`.

## Actualización 2026-11-17 (PLAN v3)
El reconocimiento pasa de confirmar a **entregar**: los rechazos por configuración incompleta ya no ocurren al confirmar sino al **cobrar por adelantado** (falta Anticipos de clientes o la cuenta del método) y al **entregar** (faltan Cuentas por cobrar, Ingresos o Anticipos). Nuevos rechazos accionables: `order_has_unposted_payments` y `delivery_date_not_covered` (al entregar), además de los ya previstos. Sin pantallas nuevas:
- **Detalle del pedido:** la alerta con `issues` y enlace (ya implementada) cubre el cobro; no cambia.
- **Diálogo de entrega:** muestra el rechazo en su alerta de error existente (`alert-error`) con el mensaje del servidor; para `posting_configuration_missing` el mensaje reúne los faltantes y el diálogo añade el mismo enlace «Ir a la configuración de Ventas».
- **Panel «Asientos automáticos» de Ventas:** muestra por datos del servidor el rol nuevo «Anticipos de clientes» y los eventos «Cobrar un pedido por adelantado», «Reconocer la entrega de un pedido» y «Cobrar una venta» (el reconocimiento al confirmar deja de mostrarse). Sin cambios de componente.
