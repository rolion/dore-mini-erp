# DDR-gestionar-atencion-odontologica-desde-citas-listado-y-detalle-de-atencion: Listado clínico de citas y detalle «Atención odontológica»

**Estado:** Propuesto
**Task relacionado:** TASK-gestionar-atencion-odontologica-desde-citas
**Fecha:** 2026-11-27 · **Revisión v2:** 2026-11-27 (crítica de diseño; ver «Revisión v2»)

## Contexto
El odontólogo necesita pasar de la agenda a la atención clínica sin duplicar la agenda: ver las citas de sus pacientes, abrir la atención, iniciarla, registrar odontograma opcional y finalizarla o cancelarla con trazabilidad.

## Pantallas/flujos afectados
1. **Odontología → Citas** (`/pocketbiz/dentistry/appointments`): listado clínico.
2. **Atención odontológica** (`/pocketbiz/dentistry/appointments/:appointmentId`): detalle con acciones.
3. **Odontograma de la atención**: se reutiliza la pantalla existente (`dentistry/patients/:id/odontogram`) con `?encounter=<id>` para precargar el contexto y volver a la atención.
4. **Ficha del paciente**: nueva sección «Atenciones» (lista de solo lectura con enlace a cada atención e indicación de si tuvo odontograma).
5. **Agenda → detalle de cita**: para citas odontológicas el botón «Marcar atendida» se sustituye por un aviso y un enlace «Abrir atención odontológica».
6. **Menú**: subítem «Citas» dentro de Odontología (junto a Pacientes y Presupuestos).

## Componentes/patrones elegidos
- **Listado:** plantilla *Lista de solo lectura con filtros* (`features/inventory/pages/movement-list`) y variante compacta bajo `lg`. Columnas: ID (primeros 8 caracteres), paciente, odontólogo, fecha/horario, estado de cita (badge de Agenda, `STATUS_CLASSES`), estado de atención (badge nuevo con texto: Pendiente, En progreso, Finalizada, Cancelada), acción «Ver cita» (`btn btn-sm btn-primary`). Filtros: rango de fechas (por defecto hoy), odontólogo (`ng-select`), búsqueda de paciente, estado de cita, estado de atención. Paginación de Agenda.
- **Detalle:** plantilla *Detalle de documento en curso con acciones en la cabecera* (`sales/pages/order-detail`) y *Detalle con edición por sección y línea de estado* (`dentistry/pages/patient-detail`). Cabecera con título «Atención odontológica», badges de estado de cita y de atención y botones según `allowed_actions` del servidor. Secciones (`card`): Cita y profesional; Resumen del paciente (nombre, edad si hay dato, contacto, antecedentes y alergias, enlace a expediente e historial); Estado clínico (inicio/fin reales, autor); Odontograma (Agregar / Continuar / Ver); Observaciones (editable mientras está en progreso, un solo envío); Recetas médicas **solo si** `prescriptions_enabled` (hoy no se renderiza, sin botón inoperante).
- **Iniciar:** botón `btn btn-primary` con «Iniciando…» y deshabilitado al enviar (sin doble envío). **Finalizar:** `btn btn-success` con confirmación breve. **Cancelar:** diálogo `NgbModal` con motivo obligatorio (patrón *Diálogo de acción irreversible con motivo*), `alert alert-info` que explica que cancela también la cita y conserva los datos clínicos.
- **Estados (design-system §4):** cargando (spinner), vacío (listado: «No hay citas con estos filtros»), error (`alert alert-danger` con reintentar), éxito (`alert alert-success`). Errores 409 dentro de la pantalla: `draft_pending` («Confirma o descarta el odontograma en borrador antes de finalizar»), cita no elegible, atención ya cerrada.
- Sin patrón nuevo reutilizable: no se propone cambio a `design-system.md`, salvo registrar el badge de atención en la lista de badges si el equipo lo pide en review.

## Alternativas consideradas
- **Añadir columnas clínicas a la pantalla de Agenda:** mezcla agenda con datos clínicos visibles a quien solo agenda. Descartada.
- **Atención en modal desde el listado:** el detalle contiene varias secciones y acciones; una página propia es más clara y enlazable.
- **Editor de odontograma embebido en el detalle:** duplicaría el editor; se reutiliza la pantalla existente por navegación (la tarjeta pide reutilizar el editor).

## Comportamiento por privilegio/estado
- El frontend muestra solo las acciones que el servidor devuelve (`allowed_actions`: `start`, `finish`, `cancel`), pero **la barrera es el backend**: todo endpoint clínico exige `CompanyClinicalPermission` (empresa, módulos y acceso clínico). Quien no tiene acceso clínico no ve el submenú (`clinicalGuard`) ni recibe antecedentes/alergias.
- Pendiente: «Iniciar atención» (si la cita lo permite). En progreso: «Finalizar», «Cancelar», odontograma, observaciones. Finalizada/Cancelada: solo lectura (odontograma consultable; en cancelada se muestra el motivo, autor y fecha).
- Cita cancelada, no asistió o futura: «Iniciar» oculto con texto explicativo.

## Consecuencias
Una pantalla nueva por función y un enlace entre Agenda y Atención. Deuda aceptada: el odontograma se abre en otra pantalla (navegación), no embebido. El texto va por i18n (es/en/pt).

## Revisión v2 (crítica de diseño, aprobada por el usuario en el chat)
Origen: `/design:design-critique` sobre las 4 pantallas del detalle (pendiente, en progreso, con odontograma, finalizada). El usuario pidió aplicar las recomendaciones 1-5. Reemplaza lo indicado del detalle en «Componentes/patrones elegidos»; el resto del DDR sigue vigente.

1. **Franja de alerta clínica.** Bajo el encabezado, si hay alergias, antecedentes médicos o medicación, un `alert alert-warning` (`role="note"`) con una línea «Etiqueta: valor» por dato. Visible en todos los estados; sin datos no se muestra (el resumen sigue diciendo «Sin registrar»).
2. **Estados etiquetados y accesibles.** Dos badges junto al nombre del paciente: «Cita: …» y «Atención: …», con las clases Bootstrap `bg-{tono}-subtle text-{tono}-emphasis` (contraste AA en claro y oscuro). Tonos: Programada/Pendiente `warning`, Confirmada/En progreso `primary`, Atendida/Finalizada `success`, Cancelada `danger`, No asistió `secondary`. Mismo mapeo en el listado y en el historial de la ficha. El título de la tarjeta pasa a ser el nombre del paciente (el título de página ya dice «Atención odontológica»).
3. **Distribución en dos columnas (≥ `lg`).** Izquierda: Estado clínico, **Odontograma** (bloque con borde), Observaciones y la barra de acciones; derecha: Cita y profesional y Resumen del paciente (en móvil el resumen va primero). Barra de acciones junto a las observaciones: «Guardar observaciones» (secundario, solo con cambios), **«Finalizar atención»** (principal, verde oscuro derivado del tema con `color-mix`, texto blanco AA) y, separado a la derecha, «Cancelar atención» como `btn-outline-danger`. El encabezado conserva «Iniciar atención» (deshabilitado con el motivo en un `alert alert-info` + `aria-describedby` cuando aún no procede) y «Volver».
4. **Accesibilidad.** Acciones con `min-block-size: 44px` (`btn-touch`); sin colores HEX nuevos; mensaje de éxito con margen dentro del contenedor.
5. **Vacíos y solo lectura.** «Sin registrar» (antes «Sin dato») y, en alergias, enlace «Registrar» a la ficha; observaciones de solo lectura como texto («Sin observaciones» si no hay); odontograma como «Odontograma de esta atención · versión N» con el número del paciente como texto secundario («N.º 3 del paciente»).

**Deuda aceptada:** el fondo azul claro de los campos de texto es estilo global de la plantilla (afecta a todo el sistema) y no se cambia aquí; el diálogo de finalizar y cancelar sigue siendo `<dialog>` nativo como Agenda.
