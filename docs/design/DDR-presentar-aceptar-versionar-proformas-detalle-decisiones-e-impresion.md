# DDR-presentar-aceptar-versionar-proformas-detalle-decisiones-e-impresion: Detalle de proforma con decisiones por línea, historial e impresión

**Estado:** Propuesto
**Task relacionado:** TASK-presentar-aceptar-versionar-proformas
**Fecha:** 2026-11-04

## Contexto
El detalle de proforma (`quotations` y `dentistry`) muestra líneas, versiones y «Total aceptado: —». La persona debe registrar qué líneas acepta o rechaza el paciente, ver el resultado y el historial, y entregar una copia impresa de la versión presentada.

## Pantallas/flujos afectados
- `/pocketbiz/quotations/proformas/:id` y `/pocketbiz/dentistry/proformas/:id` (detalle). Sin pantallas nuevas salvo la vista imprimible: `…/proformas/:id/imprimir`.
- **Resumen de la cabecera:** `dl` con tres importes separados y rotulados — *Total propuesto*, *Total aceptado*, *Pendiente de decisión* — y el badge de estado de aceptación con texto (*Pendiente* gris, *Parcialmente aceptada* azul, *Aceptada* verde, *Rechazada* rojo), además del badge existente de estado documental. No se mezcla con saldo financiero: una nota `small.text-muted` indica «El saldo de cobro no se calcula aquí».
- **Tabla de líneas:** columna de casilla (solo en proformas presentadas con líneas pendientes y permiso; con `aria-label` por fila y «Seleccionar todas las pendientes»), servicio (y pieza dental en odontología), cantidad, precio, subtotal y **Decisión**: badge con texto («Pendiente», «Aceptada», «Rechazada») + fecha `dd/MM/yyyy` y, si aplica, «Autorizada para el trabajo» solo en las aceptadas. Etiquetas «Adicional», «Reemplaza a …» y «Conservada de v1» (texto, `badge-outline`) según `line_kind`. Las líneas aceptadas heredadas de una versión anterior muestran un candado con texto «Bloqueada: aceptada».
- **Acción «Registrar decisión»** (visible si `allowed_actions` incluye `decide` y hay líneas seleccionadas): abre un diálogo `NgbModal` (`backdrop: 'static'`) en dos pasos dentro del mismo diálogo — (1) elegir *Aceptan* / *Rechazan*, nombre de quien decide (obligatorio al aceptar), medio (select), referencia opcional y motivo opcional (rechazo); (2) **resumen de confirmación**: tabla con exactamente las líneas seleccionadas, su subtotal y el importe total que se acepta o rechaza, y la frase «Se registrará que … acepta N tratamientos por BOB X. Esta acción no se puede deshacer; solo se puede rectificar con motivo». El botón «Confirmar» se deshabilita y muestra «Registrando…» al enviar; la clave de idempotencia se genera al abrir y se reutiliza en cada reintento. Un error del servidor queda dentro del diálogo sin perder lo escrito.
- **Rectificar** (solo línea decidida, versión presentada vigente y `rectify` permitido): botón secundario por fila → diálogo de acción irreversible con motivo obligatorio (patrón `movement-reverse-dialog`): muestra la decisión actual, la nueva, y exige motivo (máx. 500) y, si pasa a aceptada, nombre y medio.
- **Historial de decisiones:** sección `h5` «Historial de decisiones» (tabla apilada, 10 por página): fecha, línea, decisión, quién aceptó, medio, referencia, registrado por, motivo, y la marca «Rectificación» o «Conservada de vX». Vacío: «Aún no hay decisiones registradas».
- **Versiones:** la tabla existente suma las columnas *Aceptado* y *Estado de aceptación*; las versiones reemplazadas se abren en solo lectura (sin casillas ni acciones) con un `alert alert-info` «Versión anterior: solo lectura». El detalle enlaza «Versión anterior» (`previous_version_id`).
- **Imprimir:** botón «Imprimir / guardar PDF» visible en presentadas y reemplazadas; abre `…/imprimir`, vista limpia (sin menú ni sidebar) con número y versión, fecha, vigencia, cliente/paciente, tabla de líneas (descripción, pieza, cantidad, precio, subtotal, decisión y fecha en texto), totales propuesto/aceptado/pendiente y condiciones comerciales; llama a `window.print()` desde un botón y usa estilos `@media print`. **Excluye** referencia/evidencia, motivos, usuario que registra, ids e historial. Los datos vienen del endpoint `printable` (el backend decide qué es comercial).

## Componentes/patrones elegidos
`docs/design/design-system.md` §5: Detalle con pestañas y acciones de ciclo de vida (diálogos `NgbModal` con `backdrop: 'static'`), Formulario con líneas y paso de resumen (clave de idempotencia al abrir), Diálogo de acción irreversible con motivo y Detalle con historial embebido. Badges de texto (`col-*`). Como hay dos consumidores (`quotations`, `dentistry`), se crean **tres componentes presentacionales compartidos** en `src/app/shared/components/proforma-decisions/`: `decision-dialog`, `rectify-dialog` y `decision-history`, con un modelo mínimo común (`shared/models/proforma-decisions.ts`); los detalles de cada módulo siguen siendo propios. Se propone la entrada correspondiente en `design-system.md` (sección nueva «Detalle con selección de líneas y registro de decisión»). Sin dependencias de paquetes.

## Alternativas consideradas
- Aceptar/rechazar con botones por fila: más clics, no permite registrar varias líneas con un solo resumen ni una sola confirmación; descartado.
- Registrar la decisión en una pantalla aparte: rompe el contexto de la proforma; el diálogo con paso de resumen basta.
- Descargar PDF generado en servidor: requiere dependencia nueva; se usa la impresión del navegador.
- Duplicar los diálogos en cada módulo: más código idéntico; los componentes compartidos son solo de presentación.

## Comportamiento por privilegio/estado
Cargando, vacío, error con «Reintentar» y éxito (`alert alert-success` tras registrar) visibles. Borrador: sin casillas ni decisión (columna «Pendiente» informativa). Presentada: casillas para pendientes. Reemplazada: lectura. Teclado: casillas y diálogos operables, foco al abrir y al cerrar el diálogo, `aria-live` para el resultado. Nada se ejecuta ni cobra al aceptar. **Lo aplica el backend:** estado de la proforma, líneas pendientes, campos obligatorios, rol para rectificar, módulo habilitado, empresa de la sesión, idempotencia y qué campos son imprimibles; ocultar un botón no es la barrera.

## Consecuencias
Tres componentes compartidos nuevos y una entrada en el sistema de diseño. La vista imprimible depende del diálogo de impresión del navegador (sin PDF en servidor). Las pantallas de otros módulos no cambian.
