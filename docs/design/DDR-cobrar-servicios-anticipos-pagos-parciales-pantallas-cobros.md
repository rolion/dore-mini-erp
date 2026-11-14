# DDR-cobrar-servicios-anticipos-pagos-parciales-pantallas-cobros: Pantallas de Cobros

**Estado:** Propuesto — **reemplazado parcialmente por** `DDR-simplificar-flujo-proforma-cobro-flujo-y-pantallas` (diálogo de decisión y diálogo de cobro)
**Task relacionado:** TASK-cobrar-servicios-anticipos-pagos-parciales
**Fecha:** 2026-11-04

## Contexto
La persona de caja cobra tratamientos aceptados con anticipos y abonos. Debe ver propuesto, aceptado, cobrado y saldo por separado, repartir el pago entre tratamientos y confirmar con un resumen. No ve diagnósticos (las proformas solo traen descripción del servicio y pieza).

## Pantallas/flujos afectados
1. **Cobros — lista** (`/receivables`, menú «Flujo financiero → Cobros»): obligaciones con cliente, proforma, aceptado, cobrado, saldo y estado de cobro; filtros por cliente, fecha y estado.
2. **Cobro de una proforma — detalle** (`/receivables/:kind/:number`): cabecera (cliente, proforma, versión vigente), tarjetas Propuesto / Aceptado / Cobrado / Saldo, tabla de tratamientos (descripción, pieza, importe aceptado, cobrado, saldo; rechazados y pendientes aparecen atenuados y no seleccionables), historial de pagos con sus imputaciones y botón «Registrar pago».
3. **Registrar pago** (panel/diálogo dentro del detalle): importe, fecha, método, referencia opcional y, por tratamiento con saldo, el importe a imputar; botón «Repartir en orden» como ayuda. Paso de **resumen** antes de confirmar; tras el éxito, comprobante `CB-NNNNNN` y saldo actualizado.
4. **Accesos:** botón «Cobrar» en el detalle de proforma genérica y odontológica (solo si hay líneas aceptadas) y enlace «Cobros» en la ficha del paciente.

## Componentes/patrones elegidos
- Lista: plantilla «Lista de solo lectura con filtros» (referencia `features/inventory/pages/movement-list`).
- Detalle: «Detalle con selección de líneas y registro de decisión» (`features/quotations/pages/proforma-detail`, `features/dentistry/pages/dental-proforma-detail`) y «Detalle con pestañas y acciones de ciclo de vida» para el historial.
- Formulario de pago: «Formulario con líneas y paso de resumen» (`features/inventory/pages/stock-opening`).
- Badges de estado de cobro (pendiente/parcial/pagado) del sistema de diseño §3; tokens y botones existentes. Sin componentes nuevos fuera del sistema; si el resumen de montos se repite, se propone como componente compartido sin cambiar `design-system.md` salvo que surja un patrón reutilizable.

## Alternativas consideradas
- Formulario en página aparte: más navegación sin beneficio; se prefiere diálogo dentro del detalle para conservar el contexto.
- Imputación automática sin edición: contradice «distribuir explícitamente»; queda solo como ayuda.

## Comportamiento por privilegio/estado
Estados: cargando, vacío (sin líneas aceptadas: mensaje y enlace a la proforma), error (con reintento y datos del formulario conservados) y éxito. Botón «Confirmar» deshabilitado mientras se envía y la clave de idempotencia se reutiliza en reintentos. Sin líneas aceptadas o con saldo 0 no se ofrece «Registrar pago». Navegación por teclado y foco gestionado en el diálogo. **El backend decide:** módulos habilitados, empresa de sesión, líneas cobrables, saldos e idempotencia; la UI solo refleja `allowed_actions`.

## Consecuencias
No hay anulación ni corrección de pagos en la UI. Sin profesional por línea. Los textos van en es/en/pt.
