# DDR-conciliar-regularizar-pagos-historicos-pantalla-regularizacion: Pantalla «Regularizar pagos históricos»

**Estado:** Propuesto
**Task relacionado:** TASK-conciliar-regularizar-pagos-historicos
**Fecha:** 2026-11-14 (revisado el 2026-11-15 tras la crítica de diseño y las pruebas en navegador; ver «Revisión del resumen»)

## Contexto
El administrador esperaba hacer la regularización desde la interfaz y no solo con el comando de servidor. La pantalla es una operación excepcional y de riesgo (crea entradas en el libro), por eso exige previsualizar antes de aplicar.

## Pantallas/flujos afectados
Nueva: Contabilidad → «Regularizar pagos históricos» (`/pocketbiz/accounting/regularization`, módulo `accounting` habilitado, solo admin). Nuevo ítem de menú bajo Contabilidad. El libro de entradas no cambia.

## Componentes/patrones elegidos
Plantilla «Formulario con líneas y paso de resumen» (`features/inventory/pages/stock-opening`) con un flujo de dos pasos en la misma pantalla:
1. **Configurar:** `.card` con periodo (Desde/Hasta, opcionales) y una lista de reglas (fila «método · cuenta · desde · hasta» con «Quitar regla») con «+ Añadir regla»; `select` nativos de métodos y de cuentas activas en BOB (`ng-select` no hace falta). **Sin valores por defecto ni sugeridos desde el mapeo vigente** (no se infieren cuentas); método o fecha sin regla = queda pendiente. Botón «Previsualizar» (primario).
2. **Resumen:** un solo `alert alert-info` tenue (`bg-info-subtle text-info-emphasis border-info-subtle`, contraste AA; el azul pleno de la plantilla da texto blanco ~2,2:1) con «Previsualización: no se ha escrito nada» y, debajo en negrita, el **titular de resultado** («Se revisaron N pagos: X se crearían, Y ya están registrados, Z ya tienen entrada en otra cuenta y W requieren revisión»). Bajo la alerta, la **lista de alcance** (`small.text-muted`): periodo revisado (o «sin filtro»), una línea por regla aplicada («Efectivo → Banco BCP (rango)») y los métodos sin regla, cuyos pagos quedan pendientes. Después, la tabla por **origen × cuenta × moneda** con columnas «Qué pasa» (`app-status-badge`: verde «Se creará»; gris/ámbar «… no se toca»), Origen, Cuenta, Pagos e Importe (con `money`), y la nota «cada fila agrupa pagos, no es una lista de ingresos; importes = entradas registradas, no saldo ni utilidad». Sigue la línea de campos ausentes («Pagos sin dato original: Autor: N») y la tabla de casos que requieren revisión (fecha `dd/MM/yyyy`, motivo/campos). El botón `btn btn-warning` dice «Aplicar: crear N entradas» (o «Aplicar regularización» deshabilitado cuando no hay nada que crear) y se deshabilita si el formulario cambió después de previsualizar (hay que volver a previsualizar); abre un diálogo `NgbModal` (`backdrop: 'static'`, alerta tenue igual) como «Diálogo de acción irreversible»: resume cuántas entradas y qué importe se crearán, aclara que no modifica pagos, saldos ni entradas existentes y que no se puede deshacer desde la aplicación, y confirma con `btn-danger` («Aplicando…» al enviar).
3. **Resultado:** `alert alert-success` con creadas / ya existentes / con error (lista de errores) y el enlace «Ver entradas» (`/pocketbiz/accounting/entries`).

Estados: cargando (botones deshabilitados con texto «Previsualizando…»/«Aplicando…»), vacío («No hay pagos para regularizar en este periodo» cuando el total es 0), error de validación (mapeo/fechas bajo el campo o `alert alert-danger`), error de servidor visible, 409 «ya hay una regularización en curso» en `alert alert-warning`, éxito.

## Revisión del resumen (2026-11-15)
La primera versión mostraba solo la tabla de grupos y la persona la leyó como «6 ingresos no ingresados» y creyó que la regla filtraba por método. Cambios: titular de resultado, columna «Qué pasa» con badges (el estado va en el texto, nunca solo en color), lista de alcance (el periodo y las reglas no filtran por método: la regla solo elige cuenta) y alertas tenues para cumplir contraste. La clase tenue es un patrón admitido para alertas informativas con texto de lectura; el resto del producto conserva `alert-info` hasta que se toque (deuda visual aceptada, ver Consecuencias).

## Alternativas consideradas
- **Asistente de varias rutas:** más navegación para una operación rara; descartado por la plantilla de un solo formulario con resumen.
- **Aplicar sin previsualizar:** descartado; la tarjeta exige previsualización obligatoria.
- **Precargar el mapeo vigente de métodos:** más rápido pero infiere cuentas; descartado.

## Comportamiento por privilegio/estado
Solo admin de la empresa con `accounting` habilitado (el ítem de menú y la ruta lo ocultan). **El backend es la barrera:** `CompanyAdminPermission`, empresa de la sesión, módulo requerido, `apply` exige `confirm: true`, el autor de la regularización es el usuario autenticado y no un dato del cliente.

## Consecuencias
Nueva ruta, ítem de menú y claves i18n es/en/pt. La regularización queda disponible también por comando. Deuda visual aceptada: el resto de pantallas sigue con `alert-info` de la plantilla (texto blanco sobre azul claro, bajo contraste) y debería migrar al estilo tenue cuando se toque. Se añade una nota en `design-system.md` §5/§6.
