# Verificación manual: cobros unificados con accounting (PB-ACC-005)

Entorno de desarrollo con datos de prueba; **nunca** producción. Idioma es, usuario admin de una empresa de prueba.

## Preparación
1. Backend (`python manage.py runserver`) y frontend (`npm start`) en marcha; empresa con módulos `sales`, `catalog`, `customers`, `services`, `quotations`, `receivables`, `accounting`.
2. En `/pocketbiz/accounting/settings` crear cuentas «Caja» y «Banco» (BOB) y mapear `CASH` → Caja, `QR` → Banco.

## Recorrido A — productos
- [ ] Crear un pedido de Bs 300 (2 × Bs 150) y cobrar 100 (efectivo) y 200 (QR). Estado de pago: pagado.
- [ ] Reintentar el segundo cobro desde la pantalla (doble clic): sigue habiendo un solo pago de 200.
- [ ] Entradas: dos filas de origen Productos (100 en Caja, 200 en Banco). El stock del producto no cambió.

## Recorrido B — odontología / servicios
- [ ] Desde el perfil del paciente, proforma dental o de servicios de Bs 300 aceptada; cobrar 100, 50 y 150 (el último con dos líneas imputadas).
- [ ] Entradas: tres filas Servicios; el pago con dos líneas es **una** fila. Las notas clínicas no aparecen en ninguna columna ni detalle.
- [ ] Repetir con el módulo **Ventas deshabilitado**: el cobro funciona y el menú Ventas no aparece.

## Libro y totales
- [ ] Total Bs 600; por origen Productos 300 y Servicios 300. Cambiar de página y aplicar filtros (origen, método, cuenta, fechas): totales coinciden con las filas filtradas.
- [ ] Ninguna pantalla presenta las cuentas como saldos bancarios; el texto dice «entradas registradas».
- [ ] Cambiar el mapeo de efectivo a Banco y cobrar de nuevo: la entrada nueva va a Banco; las anteriores siguen en Caja.

## Regularización
- [ ] Con pagos anteriores sin entrada: previsualizar (no escribe), aplicar con confirmación, repetir: «0 por crear» y totales iguales.
- [ ] Reporte ventas − gastos: mismos valores y etiqueta antes y después.
- [ ] Con `accounting` deshabilitado: cobrar un pedido y una proforma funciona como antes, sin entradas.

## Resultado de la corrida
Ejecutada el 2026-11-15 en el navegador integrado (backend y `ng serve` locales, BD de desarrollo, empresas de prueba «ACC005 Productos» y «ACC005 Odontologia», usuarios de prueba, 800×600, tema claro).

**Cómo se hizo:** los cobros y las proformas se crearon por la API autenticada desde la consola del navegador (no con los formularios de Ventas y Cobros); las pantallas de Contabilidad se recorrieron con clics reales.

| Paso | Resultado |
|---|---|
| A. Pedido Bs 300 cobrado 100 (efectivo) + 200 (QR); reintento del cobro de 200 | OK: pedido pagado, un solo pago por clave, 2 entradas Productos (Caja 100, Banco 200) |
| B. Proforma Bs 300 cobrada 100+50+150; reintento del último | OK: `paid`, 3 entradas Servicios, reintento 200 sin entrada nueva |
| Libro | OK: «Bs 600.00 · 5 entradas · Productos Bs 300.00 · Servicios Bs 300.00»; texto «Cobros recibidos. No es saldo de cuenta, utilidad ni devengamiento.»; la nota del pedido no aparece |
| Regularización (4 pagos históricos sin entrada) | OK: sin reglas, 4 «requieren revisión»; con regla Efectivo→Caja, «3 se crearían, 5 ya están registrados, 1 sin regla»; diálogo de confirmación; aplicar creó 3 (libro Bs 660.00); repetir creó 0 y totales iguales |
| Odontología con Ventas deshabilitado | OK: cobro dental 100 (efectivo) y 80 (QR) → 201; `/api/orders/` responde 403; el menú no muestra Ventas, Gastos ni Reportes; libro con 2 entradas Servicios (Bs 180.00) |

**Hallazgo de la preparación (no del producto):** al sembrar la empresa de prueba con `enabled_keys()` se habilitan todos los módulos por defecto; hubo que borrar los módulos sobrantes para probar Ventas deshabilitado.

**No verificado:** filtros del libro en la pantalla (cubiertos por pruebas de backend), cambio de mapeo desde la pantalla de cuentas, tema oscuro y móvil, reporte ventas − gastos en pantalla, módulo accounting deshabilitado en pantalla, usuario no admin.
