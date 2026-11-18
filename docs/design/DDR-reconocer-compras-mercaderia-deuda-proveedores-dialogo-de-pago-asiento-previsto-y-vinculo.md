# DDR-reconocer-compras-mercaderia-deuda-proveedores-dialogo-de-pago-asiento-previsto-y-vinculo: Asiento previsto al pagar y vínculo pago ↔ asiento

**Estado:** Propuesto
**Task relacionado:** TASK-reconocer-compras-mercaderia-deuda-proveedores
**Fecha:** 2026-11-17

## Contexto
El pago de una compra ahora genera asiento (ADR de pagos y anticipos). La persona debe ver, antes de confirmar, qué asientos se crearán (deuda, anticipo, cuentas de Caja/Banco) y, después, a qué asientos corresponde cada pago. Se reutiliza el diálogo y la pestaña existentes y el patrón de alerta accionable de `DDR-reconocer-compras-mercaderia-deuda-proveedores-errores-accionables-y-asiento-en-recepcion.md`.

## Pantallas/flujos afectados
1. **Diálogo «Registrar pago»** (`components/payment-dialog`): bajo Monto/Método aparece un bloque **«Asiento previsto»** con el desglose («Liquida deuda: Bs X», «Anticipo a proveedor: Bs Y») y una tabla Cuenta / Debe / Haber con los nombres de cuenta. Se actualiza al cambiar monto, método o fecha (con *debounce*) leyendo la vista previa del servidor. Faltantes de configuración (cuenta del método o rol sin cuenta, período cerrado) se muestran en la alerta tenue con enlace a Compras › Asientos automáticos o a Métodos de pago; el botón Registrar sigue habilitado solo si no hay faltantes que el servidor ya conoce. Desaparece el aviso de «falta la clasificación de pagos a proveedores».
2. **Pestaña Pagos** (`components/purchase-payments-tab`): cada pago muestra sus asientos («Asiento de deuda», «Asiento de anticipo») como enlaces a `/pocketbiz/accounting/journal/:id`, o «Sin asiento contable» (texto tenue) si no hay; solo con Contabilidad habilitada. Se agrega una columna/etiqueta «Anticipo» cuando el pago incluye parte anticipada.
3. **Detalle de la recepción**: sin cambios respecto al DDR vigente; el asiento puede mostrar «Anticipo aplicado» en la fila de total si procede (texto, no pantalla nueva).
4. **Movimientos (detalle de asiento)**: el campo **Origen** deja de mostrar el código técnico (`PURCHASE_RECOGNITION (módulo deshabilitado)`): muestra la etiqueta del evento (p. ej. «Reconocer una compra de mercadería») y asocia el origen al módulo del evento (Compras, Ventas…).
5. **Configuración de Compras › Asientos automáticos**: el rol «Anticipos a proveedores» y el evento «Pagar por adelantado a un proveedor» aparecen por datos del catálogo, con claves es/en/pt.

## Componentes/patrones elegidos
Plantilla de formulario en diálogo y de detalle de `docs/design/design-system.md` (secciones 3 y 5); tabla pequeña con `MoneyPipe`; alerta de Contabilidad en estilo tenue (contraste AA, SCSS `@use` del parcial `alert-warning`); sin componentes nuevos de Oreva ni colores propios. Textos con claves `translate` en es/en/pt.

## Alternativas consideradas
- Mostrar el asiento solo tras pagar: no evita pagos con cuentas equivocadas. Descartado.
- Selector de cuenta por pago: descartado por la persona (la cuenta sale del método).

## Comportamiento por privilegio/estado
Estados del bloque: cargando (texto «Calculando asiento…»), éxito (tabla), error de configuración (alerta con enlace), sin Contabilidad o sin cobertura (se oculta o dice «Este pago no genera asiento contable»). El servidor valida siempre; la vista previa es informativa y el frontend no es la barrera de seguridad.

## Consecuencias
La pestaña de pagos y el diálogo dependen de dos llamadas más a la API (vista previa y asientos del pago). Deuda visual aceptada: dos pantallas de Compras reutilizan el estilo de alerta duplicado de Ventas.
