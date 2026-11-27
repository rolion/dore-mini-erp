# DDR-registrar-diagnostico-odontograma-inicial-pantalla-odontograma: Pantalla de Odontograma del paciente

**Estado:** Propuesto
**Task relacionado:** TASK-registrar-diagnostico-odontograma-inicial
**Fecha:** 2026-11-26

## Contexto
PB-ODO-002 añade a la ficha del paciente el registro de evaluaciones (odontogramas) por pieza FDI y superficie. El catálogo de condiciones es una **propuesta técnica pendiente de validación clínica** (decisión del usuario, 2026-11-26: usar la lista inicial y modificarla luego); la UI lo recibe del backend y nunca lo duplica.

## Pantallas/flujos afectados
- Ficha del paciente (`/pocketbiz/dentistry/patients/:id`): botón «Odontograma» en la cabecera (`btn btn-primary`, junto a «Volver»); el menú lateral no cambia.
- Nueva pantalla `/pocketbiz/dentistry/patients/:id/odontogram` (guard clínico, `unsavedChangesGuard`).
  1. **Cabecera**: migas «Odontología › Pacientes › nombre», título «Odontograma», selector de evaluación (`form-select`: «#n · fecha clínica · Borrador/Confirmada · autor») y botones según `allowed_actions` del servidor: «Nueva evaluación», «Guardar borrador», «Confirmar evaluación», «Corregir (enmienda)», «Descartar borrador».
  2. **Datos de la evaluación** (`card`): tipo de dentición (Permanente / Temporal / Mixta), fecha clínica, profesional (opcional, de Personal), badge de estado con texto, autor y fecha de registro, y enlace «Corrige a #n» / «Reemplazada por #m» cuando exista.
  3. **Vista** con `nav-pills` accesible «Gráfico» / «Tabla» (misma información).
     - *Gráfico*: arcadas superior e inferior en SVG; cada pieza es un `button` con su código FDI, abreviatura del hallazgo principal y color; piezas **sin evaluar** en gris punteado con texto «Sin evaluar»; **Sano** se registra de forma explícita y se muestra «Sano». En dentición mixta la temporal lleva borde discontinuo y la insignia «T» (permanente «P»). Debajo, **leyenda textual** (color + abreviatura + nombre).
     - *Tabla*: `table table-sm` con Pieza, Dentición, Superficies, Condición, Diagnóstico, Notas; hallazgos generales en tabla aparte. En pantallas < `lg` usa la variante compacta apilada de §5.
  4. **Panel de la pieza seleccionada** (`card` lateral en ≥ `lg`, debajo en móvil): título «Pieza 16 · molar permanente», hallazgos existentes y formulario de hallazgo (condición `form-select`, superficies como checkboxes con nombre completo y abreviatura, diagnóstico, notas con contador desde 80 %). «Otro» exige nota. Solo editable si la evaluación es borrador.
  5. **Hallazgos generales** (`card`): lista y alta (diagnóstico requerido, notas) sin pieza.
- Diálogos `NgbModal` (`backdrop: 'static'`): **Confirmar** (resume cantidad de hallazgos, avisa de que será inmutable y de que corregir crea una nueva evaluación) y **Corregir** (motivo obligatorio, máx. 500, `btn-warning` deshabilitado hasta que el motivo recortado no esté vacío), según «Diálogo de acción irreversible con motivo».

## Componentes/patrones elegidos
- Plantilla «Detalle con pestañas y acciones de ciclo de vida» (§5): badge de estado con texto (`col-orange` borrador, `col-green` confirmada), acciones desde `allowed_actions`, diálogos de confirmar/corregir con motivo.
- «Detalle con edición por sección y línea de estado» (§5) para la línea de estado por sección (`role="status"`, «Cambios sin guardar» · «Guardando…» · «Guardado ✓» · «No se pudo guardar. Tus cambios siguen aquí.» con «Reintentar»).
- «Lista de solo lectura con filtros»/variante compacta (§5) para la tabla.
- **Patrón nuevo (se propone para `design-system.md`)**: «Odontograma» — SVG propio sin dependencia nueva, pieza = `button` con `aria-pressed` y `aria-label` («Pieza 16, molar permanente, caries en O»), color siempre acompañado de abreviatura/texto, navegación por flechas dentro de la arcada y Enter/Espacio para seleccionar, tabla equivalente obligatoria. Colores solo con tokens/clases de estado existentes (`success`, `warning`, `danger`, `info`, `secondary`), sin HEX nuevos.
- Estados: cargando (`role="status"`), vacío («Este paciente aún no tiene evaluaciones» con botón «Registrar evaluación inicial»), error con «Reintentar», éxito con `alert-success` / línea de estado.

## Alternativas consideradas
1. Pestaña «Odontograma» dentro de la ficha: descartada, la ficha ya agrupa edición por sección y el gráfico necesita ancho completo.
2. Librería de odontograma de terceros: descartada (dependencia nueva, accesibilidad no controlada). SVG propio, esfuerzo moderado.
3. Solo tabla, sin gráfico: descartada, la tarjeta pide vista gráfica.

## Comportamiento por privilegio/estado
- Solo administrador con módulos `dentistry` y `customers` (política clínica existente `CompanyClinicalPermission`); el frontend oculta/inhabilita por `allowed_actions`, pero **el backend decide** y responde 403/404/409.
- Paciente archivado: lectura de evaluaciones permitida; sin crear, editar, confirmar ni corregir (mensaje «Reactiva el perfil…»).
- Evaluación confirmada: campos de solo lectura; los cambios solo vía «Corregir».
- Doble envío: botones deshabilitados mientras se guarda; ante error se conserva lo escrito.

## Consecuencias
Se introduce un componente visual nuevo (gráfico dental) a documentar en `design-system.md` §5/§6 en este PR. Deuda aceptada: sin impresión/PDF del odontograma ni imágenes/radiografías; el catálogo y sus colores pueden cambiar tras la validación clínica.
