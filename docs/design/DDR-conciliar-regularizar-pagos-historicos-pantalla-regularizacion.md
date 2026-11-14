# DDR-conciliar-regularizar-pagos-historicos-pantalla-regularizacion: Pantalla «Regularizar pagos históricos»

**Estado:** Propuesto
**Task relacionado:** TASK-conciliar-regularizar-pagos-historicos
**Fecha:** 2026-11-14

## Contexto
El administrador esperaba hacer la regularización desde la interfaz y no solo con el comando de servidor. La pantalla es una operación excepcional y de riesgo (crea entradas en el libro), por eso exige previsualizar antes de aplicar.

## Pantallas/flujos afectados
Nueva: Contabilidad → «Regularizar pagos históricos» (`/pocketbiz/accounting/regularization`, módulo `accounting` habilitado, solo admin). Nuevo ítem de menú bajo Contabilidad. El libro de entradas no cambia.

## Componentes/patrones elegidos
Plantilla «Formulario con líneas y paso de resumen» (`features/inventory/pages/stock-opening`) con un flujo de dos pasos en la misma pantalla:
1. **Configurar:** `.card` con periodo (Desde/Hasta, opcionales) y, por cada método de pago (Efectivo, QR, Transferencia, Tarjeta, Otro), una lista de reglas «cuenta · desde · hasta» con «+ Añadir periodo»; `ng-select` no hace falta: `select` de cuentas activas en BOB. **Sin valores por defecto ni sugeridos desde el mapeo vigente** (no se infieren cuentas); método sin reglas = queda pendiente. Botón «Previsualizar» (primario).
2. **Resumen:** `alert alert-info` fijo («Los importes son entradas registradas, no saldo bancario ni utilidad»; «Previsualización: no se ha escrito nada»), tabla por **origen × cuenta × moneda** con filas Faltantes, Existentes, Pendientes, Conflictos, Diferencias de destino y No válidos (cantidad e importe con `money`), línea de campos ausentes (p. ej. «Autor ausente: N») y lista de casos que requieren revisión (motivo/campos) en tabla apilada en móvil. Botón «Aplicar regularización» `btn btn-warning` visible solo si hay faltantes, deshabilitado si el formulario cambió después de previsualizar (hay que volver a previsualizar); abre un diálogo `NgbModal` (`backdrop: 'static'`) como «Diálogo de acción irreversible»: resume cuántas entradas y qué importe se crearán, aclara que no modifica pagos, saldos ni entradas existentes y que no se puede deshacer desde la aplicación, y confirma con `btn-danger` («Aplicando…» al enviar).
3. **Resultado:** `alert alert-success` con creadas / ya existentes / con error (lista de errores) y el enlace «Ver entradas» (`/pocketbiz/accounting/entries`).

Estados: cargando (botones deshabilitados con texto «Previsualizando…»/«Aplicando…»), vacío («No hay pagos para regularizar en este periodo» cuando el total es 0), error de validación (mapeo/fechas bajo el campo o `alert alert-danger`), error de servidor visible, 409 «ya hay una regularización en curso» en `alert alert-warning`, éxito.

## Alternativas consideradas
- **Asistente de varias rutas:** más navegación para una operación rara; descartado por la plantilla de un solo formulario con resumen.
- **Aplicar sin previsualizar:** descartado; la tarjeta exige previsualización obligatoria.
- **Precargar el mapeo vigente de métodos:** más rápido pero infiere cuentas; descartado.

## Comportamiento por privilegio/estado
Solo admin de la empresa con `accounting` habilitado (el ítem de menú y la ruta lo ocultan). **El backend es la barrera:** `CompanyAdminPermission`, empresa de la sesión, módulo requerido, `apply` exige `confirm: true`, el autor de la regularización es el usuario autenticado y no un dato del cliente.

## Consecuencias
Nueva ruta, ítem de menú y claves i18n es/en/pt. La regularización queda disponible también por comando. Sin deuda visual aceptada; se añade una nota en `design-system.md` §5/§6.
