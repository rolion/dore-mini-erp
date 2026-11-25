# DDR-crm-prospectos-oportunidades-kanban-y-prospectos: Kanban de oportunidades, lista de prospectos y diálogos de cierre/conversión

**Estado:** Propuesto
**Task relacionado:** TASK-crm-prospectos-oportunidades
**Fecha:** 2026-11-24

## Contexto
El vendedor mueve posibles ventas entre etapas, convierte prospectos en clientes y cierra oportunidades vinculando un pedido. El CRM ya tiene «Clientes» (lista) y «Tablero» (editor de etapas, PB-CRM-003). No hay pantalla Kanban en el sistema de diseño.

## Pantallas/flujos afectados
- Menú **CRM**: se agregan **Oportunidades** (`/pocketbiz/crm/opportunities`) y **Prospectos** (`/pocketbiz/crm/leads`), con `moduleGuard` de `customers`.
- **Oportunidades (Kanban)**: breadcrumb y encabezado con selector **Tablero**, filtros **Responsable** y **Prospecto/Cliente** (búsqueda), botón «Nueva oportunidad». Una columna por etapa activa (scroll horizontal; apiladas en móvil). Tarjeta: título, contacto (nombre + teléfono), importe con moneda, siguiente acción (fecha, resaltada si venció) y responsable; menú «Mover a…», «Cerrar», «Editar».
- **Prospectos (lista)**: tabla con nombre, teléfono, email, estado (Nuevo / Convertido a «cliente») y acciones «Editar» y «Convertir en cliente»; búsqueda y paginación.
- **Diálogos** (`NgbModal`): *Prospecto* (alta/edición), *Oportunidad* (alta/edición: título, prospecto o cliente, importe, siguiente acción, responsable, etapa inicial), *Cerrar oportunidad* (Ganada/Perdida; perdida exige motivo; ganada ofrece selector de pedido del cliente, opcional, o aviso «Convierte el prospecto para vincular un pedido» con acción), *Convertir en cliente* (confirmación; con varios coincidentes muestra la lista para elegir; con uno informa que se vinculará).

## Componentes/patrones elegidos
- Lista de prospectos: plantilla **Lista** (§5, `product-list`) con variante compacta bajo `lg` (§5 variante compacta).
- Kanban: no existe plantilla; se añade al sistema de diseño la plantilla **Tablero Kanban de tarjetas con acciones accesibles** (`features/crm/pages/crm-opportunity-board`): columnas `.card` de ancho fijo con encabezado «Etapa · N» y total, tarjetas `.card` compactas con tokens de §2 (sin colores nuevos), badges de §3 para estado (Ganada = éxito, Perdida = secundario/peligro) y botones de §3. Cierre con el patrón **Diálogo de acción irreversible con motivo** (§5).
- **Mover arrastrando** (cambio posterior pedido por el usuario; reemplaza «Mover a…» y la decisión de aplazar el arrastre): la persona arrastra la tarjeta por su asa a la columna de la etapa deseada (`@angular/cdk/drag-drop`, ya instalado). Solo tarjetas abiertas y columnas de etapas activas; la tarjeta se ve en destino al soltar y el tablero se recarga (si el servidor rechaza, aviso y recarga). Trade-off aceptado: sin alternativa de teclado ni de lector de pantalla; el asa lleva `aria-label` y es de 44 px en táctil.
- Formularios de diálogo: Reactive Forms, `form-label`/`form-control`, errores `small.text-danger` del servidor.

## Alternativas consideradas
- **Arrastrar y soltar (`@angular/cdk/drag-drop`)**: más natural en Kanban, peor accesibilidad y más pruebas; aplazado (ya descartado en PB-CRM-003).
- **Detalle de oportunidad en pantalla aparte**: innecesario para el alcance (la tarjeta pide Kanban + formularios); los diálogos bastan y PB-CRM-005 podrá añadir el detalle con actividad.
- **Mezclar prospectos y oportunidades en una sola pantalla**: confunde dos ciclos de vida distintos; se separan en dos ítems de menú.

## Comportamiento por privilegio/estado
- **Cargando:** «Cargando…». **Sin tablero o sin etapas:** estado vacío con enlace a «Tablero» para configurarlo. **Columna vacía:** «Sin oportunidades». **Sin resultados** de filtro: mensaje con «Limpiar filtros». **Error de servidor:** `alert-danger` con «Reintentar». **Validación (400):** mensaje junto al campo. **409** (etapa archivada, cerrada, pedido ya vinculado, varios coincidentes): `alert-warning` en el diálogo y recarga del tablero. **Éxito:** el tablero refleja el cambio.
- Oportunidades cerradas no aparecen en las columnas (filtro de estado «Abiertas» por defecto; opción «Ganadas»/«Perdidas» para consultarlas en modo lectura sin acciones de mover).
- Si Ventas no está habilitado, el selector de pedido no se muestra.
- Solo admin de empresa (único rol); el **backend** valida empresa, tablero, etapa, responsable y pedido; ocultar un botón no es seguridad.

## Consecuencias
Se agrega la plantilla Kanban a `docs/design/design-system.md` §5. Deuda aceptada: sin arrastre, sin ordenamiento manual dentro de la columna, sin detalle de oportunidad ni actividad (PB-CRM-005). Pantalla nueva ligeramente más densa que las listas; se mitiga con la variante apilada en móvil.
