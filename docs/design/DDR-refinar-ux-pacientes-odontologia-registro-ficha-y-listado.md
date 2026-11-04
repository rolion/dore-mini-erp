# DDR-refinar-ux-pacientes-odontologia-registro-ficha-y-listado: Alta en una pantalla, ficha centrada en lo clínico y guardado por sección

**Estado:** Propuesto
**Task relacionado:** TASK-refinar-ux-pacientes-odontologia
**Fecha:** 2026-11-04

## Contexto
La crítica de diseño de 2026-11-04 halló problemas de modelo mental (el alta habla de «cliente» y «ficha clínica»), de seguridad clínica (alergias y medicación sin jerarquía), y de feedback (un solo mensaje global lejos de la sección editada). Este DDR refina el DDR vigente `DDR-perfil-odontologico-pacientes-ficha-y-listado` (2026-11-02/03) **sin reemplazarlo**: lo que no se menciona aquí se conserva (rutas, permisos, filtros en URL, «nunca "Sin alergias"», regla de menores, archivo sin borrar).

## Pantallas/flujos afectados
1. **Lista** `/pocketbiz/dentistry/patients` — plantilla Lista (§5): se mantiene breadcrumb, título, buscador, filtro de estado `form-select`, botón «Nuevo paciente» y `ngx-datatable`.
2. **Alta** (modal «Nuevo paciente»).
3. **Ficha** `/pocketbiz/dentistry/patients/:id` — plantilla Detalle (§5) con tarjetas y `dl`.
4. **Registro de cambios** (historial dentro de la ficha).

## Componentes/patrones elegidos

### Lista
- Se **mantiene** el select de estado (Activos/Archivados/Todos), la columna Estado con `badge-outline` y la columna Acciones con el botón de ver (`btn-tbl-view`): es la plantilla del sistema; no se introduce control segmentado.
- Columnas nuevas, con datos que ya trae el resumen: **Edad** (años, con badge `col-orange` «Menor» si es menor de 18; «—» si no hay nacimiento) y **Actualizado** (`dd/MM/yyyy`).
- Texto de ayuda bajo el buscador: «Busca por nombre o teléfono. Se ignoran espacios y guiones.»
- «Limpiar filtros» visible siempre que haya búsqueda o estado distinto de Activos (no solo en vacío).
- Vacíos diferenciados: sin pacientes / sin coincidencias (con sugerencia de probar «Todos»).

### Modal de alta
- Una sola pantalla con título «Nuevo paciente» y texto introductorio: «Busca a la persona entre tus clientes o regístrala ahora. Se guardará como cliente y como paciente.»
- Selector `ng-select` etiquetado «Buscar cliente» (nombre o teléfono); enlace-botón «¿No está? Registrar persona nueva» abre el formulario rápido (Nombre*, Teléfono) **dentro del mismo modal**, con «Volver a buscar».
- Botón principal con texto según estado: «Crear paciente» (cliente existente) / «Registrar paciente» (persona nueva, crea cliente y perfil en un clic y abre la ficha). Si el perfil ya existe, el principal pasa a «Abrir ficha» y se muestra un aviso informativo (no error): «{nombre} ya es paciente.»
- Motivo visible cuando el principal está deshabilitado: «Elige o registra a una persona» / «Comprobando si ya es paciente…».
- Fallo del segundo paso: mensaje «Se registró a {nombre} como cliente, pero no se pudo crear su ficha.» con «Reintentar»; el cliente queda seleccionado.
- El duplicado de teléfono conserva el diálogo `Swal` existente del alta rápida.

### Ficha
- Plantilla Detalle (§5). Cabecera: breadcrumb existente, nombre, badges (Activo/Archivado, «Menor · N años»), línea de contacto (teléfono · correo · enlace «Ver cliente») — **sin UUID**.
- Acciones de cabecera: solo «Volver a pacientes» y un menú/botón secundario de estado (**Archivar perfil** / **Reactivar perfil**, `btn-warning` según §3 botones, con confirmación en diálogo `Swal` que explica el efecto). «Editar ficha» global desaparece: cada sección tiene su «Editar».
- Orden: **Resumen clínico** (Alergias y Medicación, texto de mayor tamaño) → **Antecedentes** (médicos, odontológicos, observaciones) → **Datos personales** (nacimiento, edad, responsable) → **Contacto** (solo lectura con nota «Nombre, teléfono y correo se editan en Clientes») → **Registro de cambios**. En lg: columna principal (lo clínico) más columna lateral (datos personales, contacto, estado); en móvil se apila con lo clínico primero.
- Vacío clínico: «Sin registrar» (texto neutro, nunca verde/rojo, nunca «Sin alergias»).
- Edición por sección: etiqueta «Editando» en el encabezado, pie con «Guardar …»/«Cancelar», **línea de estado propia** (`aria-live="polite"`): «Cambios sin guardar» · «Guardando…» · «Guardado ✓» · «No se pudo guardar. Tus cambios siguen aquí. Reintentar». Sin banners globales para resultados de guardado; el banner superior solo para carga de la ficha y para «Perfil creado».
- Textareas: crecen con el contenido, contador «n / 4000» desde el 80 %, placeholder con ejemplo («Ej.: penicilina, látex»), nunca «No informado».
- Menores: edad junto a la fecha («12/03/2014 · 12 años»); al ser menor se muestra el texto «Menor de 18 años: indica quién es responsable» y ambos campos con marcador «Obligatorio» visible; en lectura, si falta el responsable de un menor se avisa «Falta el responsable (obligatorio para menores)».
- Archivada: banner «Perfil archivado — solo lectura. Reactiva el perfil para editarlo.» con acción «Reactivar perfil»; los botones «Editar» se muestran deshabilitados con `title`; todo el contenido sigue legible.
- Foco: al abrir una sección edita el primer campo; tras guardar o cancelar vuelve al botón «Editar» de esa sección; ante error se enfoca el primer campo inválido. Errores con `aria-invalid="true"` y `role="alert"`.
- Salida con cambios: se conserva `unsavedChangesGuard` (`window.confirm` compartido con otras pantallas, sin tocar); se mejora el mensaje de `toggleActive` para nombrar la sección con cambios.

### Registro de cambios
Se conserva el `<details>` bajo la ficha, renombrado «Registro de cambios». Dentro, **pestañas** «Antecedentes» y «Datos personales» (una lista visible a la vez, `nav-tabs` del sistema §5) en lugar de dos columnas. Cada entrada: «{acción} · {autor} · {dd/MM/yyyy HH:mm}»; acciones «Perfil creado», «Datos editados», «Perfil archivado», «Perfil reactivado». Antes/Después apilados; textos largos recortados con «Mostrar texto completo». Sin clave cruda: etiqueta neutra si falta.

## Alternativas consideradas
- **Control segmentado para estado** en la lista: mejora la visibilidad, pero se aparta de la plantilla Lista (select por defecto Activos) y de la que otras listas comparten. Descartada; se compensa con «Limpiar filtros» visible.
- **Quitar la columna Acciones y usar solo el enlace del nombre**: descartada por el mismo motivo (plantilla), aunque el botón de ver se conserva con `title`/`aria-label`.
- **Historial unificado en una línea de tiempo**: exige combinar dos endpoints paginados; se difiere a backend (endpoint combinado). Las pestañas dan una lista a la vez sin tocar la API.
- **Reemplazar la guardia `window.confirm` por un diálogo compartido nuevo**: afectaría otras pantallas; fuera de alcance.
- **Mantener «No informado» como etiqueta**: es la decisión vigente; se cambia a «Sin registrar» solo por claridad (el valor vacío no es un dato «informado» por nadie). La invariante no cambia.

## Comportamiento por privilegio/estado
Sin cambios: el backend verifica permiso clínico y módulos Clientes + Odontología en cada operación y filtra por `company_id`; `clinicalGuard` y la pantalla «Acceso no disponible» se conservan. Un perfil archivado es solo lectura en la UI **y** en el backend (409). El frontend no es la barrera de seguridad.

## Consecuencias
- Desvío del sistema de diseño: el diálogo de confirmación de archivar/reactivar usa `Swal` (ya presente en Clientes) en lugar de un componente compartido que no existe; si un segundo módulo lo necesita, se moverá a `shared/`. Se propone añadir al sistema de diseño §5 el patrón «Edición por sección con línea de estado» una vez implementado.
- Deuda visual aceptada: la guardia de salida sigue usando `window.confirm`; el contraste de los botones deshabilitados se verifica en publish y se corrige solo con tokens existentes.
- Inconsistencia posible: «Sin registrar» difiere de «No informado» usado en otras fichas (Clientes). Se revisa en publish.
