# DDR-compras-registrar-pagos-saldo-pestana-y-dialogo-pago: Pestaña «Pagos» y diálogo «Registrar pago»

**Estado:** Propuesto
**Task relacionado:** TASK-compras-registrar-pagos-saldo
**Fecha:** 2026-10-30

## Contexto
PB-COM-005 pide registrar pagos desde el detalle de la compra (pestaña «Pagos» → «Registrar pago»), con resumen (total, pagado, saldo, estado) y tabla de pagos, sin menú propio. El detalle ya tiene pestañas «Resumen» y «Recepciones» (`purchase-detail`) y diálogos `NgbModal` (`purchase-cancel-dialog`).

## Pantallas/flujos afectados
- **Detalle de compra** `/purchases/:id`: nueva pestaña **«Pagos»**.
- **Diálogo «Registrar pago»** (nuevo, `NgbModal`).
- **Pestaña «Resumen»**: el estado de pago pasa a mostrarse con badge y se añaden Total pagado y Saldo cuando la compra está confirmada.

## Componentes/patrones elegidos
Plantilla «Detalle con pestañas y acciones de ciclo de vida» (`docs/design/design-system.md` §5) y su regla para pestañas de documentos relacionados: primero el avance, después la tabla apilada.
- **Pestaña «Pagos»** (`components/purchase-payments-tab`, hermano de `purchase-receipts-tab`): bloque de resumen en `dl.row` con **Total de la compra**, **Total pagado**, **Saldo** (`MoneyPipe`) y **Estado de pago** con badge y texto («Sin pagar» gris, «Pago parcial» `col-orange`, «Pagada» `col-green`). Con saldo cero y compra confirmada con total > 0 se muestra «Pagado» y no hay botón. Debajo, tabla Bootstrap apilada: **Fecha, Referencia (PAG-…), Monto, Método, Registrado por**; monto a la derecha. Vacío explicado («Aún no hay pagos registrados.»), nunca error.
- **Acción «Registrar pago»** (`btn-primary`) visible solo si `allowed_actions` incluye `pay`. Si no aplica se explica con `small.text-muted`: borrador → «Confirma la compra para registrar pagos.»; cancelada → «La compra está cancelada.»; saldo cero con total > 0 → «Pagado»; total 0 → «Sin saldo por pagar.». No hay borrar, reembolsar ni cobrar por QR.
- **Diálogo «Registrar pago»** (`NgbModal`, `backdrop: 'static'`, formulario reactivo): arriba `alert alert-info` con «Saldo actual: Bs X» (`MoneyPipe`); campos **Fecha*** (`input type=date`, hoy por defecto, `max` = hoy), **Monto*** (numérico, 2 decimales, > 0, con el saldo al lado y «Pagar el saldo completo» que lo rellena), **Método*** (`form-select` con Efectivo, QR, Transferencia, Tarjeta, Otro; sin valor por defecto). Botones **Registrar pago** (primario, deshabilitado mientras el formulario es inválido o envía, «Registrando…») y **Cancelar** (`btn-light`). Genera `payment_id` al abrir y lo reutiliza en reintentos.
- **Errores:** de validación del cliente bajo cada campo (`small.text-danger`); los del servidor (monto mayor al saldo, fecha futura, compra no pagable) se muestran bajo el campo o en `alert alert-danger` dentro del diálogo **sin cerrarlo y sin borrar lo escrito**. Si el saldo cambió por otro pago, el mensaje indica el saldo vigente y se recarga el resumen.
- **Éxito:** se cierra el diálogo, `toastr` «Pago registrado» y la pestaña se refresca (saldo, estado, tabla); el detalle de la compra se vuelve a leer para actualizar `allowed_actions` (p. ej. el botón «Cancelar compra» desaparece).
- **Estados** (§4): cargando (`Cargando…`), vacío, error de carga con «Reintentar», acción en curso, éxito.
- Sin entrada nueva en el menú lateral.

## Alternativas consideradas
1. **Formulario en página propia** (`/purchases/:id/payments/new`): innecesario; el pago es de pocos campos, no hay resumen irreversible. Se prefiere el diálogo, como pide la tarjeta («diálogo/formulario»).
2. **Mostrar el saldo solo en el resumen** (no en el diálogo): descartada; la tarjeta pide el saldo junto al monto.
3. **Método por defecto desde configuración**: no existe configuración de Compras (H-02); la persona elige siempre.
4. **Calcular saldo y estado en el cliente**: descartada; manda el servidor (`balance`, `paid_total`, `allowed_actions`), el cliente solo valida forma.

## Comportamiento por privilegio/estado
Solo administradores de empresa con el módulo `purchases` habilitado. `draft` y `cancelled` → sin alta; `confirmed` con saldo → alta; `confirmed` sin saldo → «Pagado». **El frontend no es la barrera:** el backend repite todas las reglas (compra confirmada, monto positivo y ≤ saldo bajo bloqueo, fecha no futura, método válido, empresa del usuario) y responde 400/404/409.

## Consecuencias
Sin componente compartido nuevo; si Ventas y Compras comparten luego un diálogo de pago, se moverá a `shared/` (§3). Deuda aceptada: no se pueden anular pagos (el DDR de esa task decidirá la acción y el estado «Anulado»). Los textos «Pagada» (femenino, por «compra») ya existen en `PAYMENT_STATUS_LABELS` y se conservan.
