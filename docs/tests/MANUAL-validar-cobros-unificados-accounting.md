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
_Sin ejecutar en navegador durante la construcción (el worktree no tenía dependencias del frontend ni datos de desarrollo). Cubierto por pruebas de integración de backend; la ejecución visual queda a cargo de quien apruebe o del Quality Gate._
