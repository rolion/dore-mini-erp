# DDR-perfil-odontologico-pacientes-ficha-y-listado: Pacientes y ficha separada

**Estado:** Propuesto
**Task relacionado:** TASK-perfil-odontologico-pacientes
**Fecha:** 2026-11-02

## Contexto
PB-ODO-001 extiende Clientes; solo Administrador tiene acceso clínico en v1, por decisión explícita del usuario. Odontograma, Planes, Evolución y Documentos pertenecen a historias futuras y no se muestran como capacidades disponibles.
## Pantallas/flujos afectados
- Odontología → Pacientes (`/pocketbiz/dentistry/patients`): plantilla Lista del sistema §5, buscador, Activos/Archivados/Todos, tabla ngx-datatable paginada por servidor, enlace al cliente, estado y acciones. Conservar filtros al volver.
- Alta (`/pocketbiz/dentistry/patients/new`): buscar y seleccionar cliente con nombre/teléfono. Reutilizar alta rápida existente; una coincidencia se puede seleccionar. Un cliente con perfil abre su ficha en lugar de duplicarlo. Crear perfil no crea Customer. Datos administrativos se editan en ficha, con acción de edición separada.
- Ficha (`/pocketbiz/dentistry/patients/:id`, id del cliente): patrón Detalle con pestañas de Compras y datos en dl del detalle de Clientes. Perfil muestra identidad/contacto de Clientes y nacimiento/responsable; Antecedentes contiene formulario clínico y auditoría paginada. Sin campos clínicos en Clientes.
## Componentes/patrones elegidos
Sistema §2/3/5: breadcrumb, card, Reactive Forms, ngx-datatable, badges, botones btn-tbl, alertas y nav-tabs. Alta rápida `CustomerQuickCreateService`. Ningún patrón compartido nuevo; se añade navegación al sistema de diseño. Fechas locales y etiquetas en español; móvil y tema oscuro con clases existentes.
## Alternativas consideradas
Extender la ficha de Clientes con antecedentes filtraría responsabilidad clínica hacia otro contexto. Una ficha paralela que copie nombre/contacto duplicaría identidad. Se elige ficha propia que lee los datos administrativos vigentes.
## Comportamiento por privilegio/estado
Backend verifica permiso clínico en cada operación, incluso URL directa. La interfaz consulta capacidades antes de mostrar la sección; no es la barrera de seguridad. Solo admin autorizado en v1; no se simula recepción con admin sin acceso. Sin módulo se usa la pantalla existente de módulo no habilitado.

Carga visible, vacío con alta, búsqueda sin resultados con limpiar filtros, error visible y reintento. Formularios conservan entradas ante error y bloquean doble envío; advertencia al salir con cambios. Cada campo tiene label, foco y errores asociados. Antecedentes vacíos se muestran «No informado» y nunca «Sin alergias». Nombre/teléfono del responsable exigidos para nacimiento conocido menor de 18; a los 18 dejan de ser obligatorios. Nacimiento desconocido se muestra «No informado», sin deducir edad.

Archivar requiere confirmación que explica que conserva historia y no desactiva al cliente; perfil archivado queda solo lectura hasta reactivar. El historial es solo lectura y muestra autor, fecha, acción y cambios; las notas clínicas solo se cargan con autorización.
## Consecuencias
Sin nuevas fuentes, HEX o componentes de plantilla. No se ofrecen pestañas futuras vacías ni acciones de agenda que todavía no existen. No queda deuda visual deliberada.
