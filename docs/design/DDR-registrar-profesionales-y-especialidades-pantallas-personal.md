# DDR-registrar-profesionales-y-especialidades-pantallas-personal: Pantallas de Personal

**Estado:** Propuesto
**Task relacionado:** TASK-registrar-profesionales-y-especialidades
**Fecha:** 2026-11-02

## Contexto
PB-PER-001 actualizada: un consultorio, especialidades y usuario opcionales, ninguna dependencia de Agenda/Sucursales. Seguir `docs/design/design-system.md`, sin patrón visual nuevo.

## Pantallas/flujos afectados
Menú Personal con Profesionales y Especialidades. Propuesta técnica, contrastada con el router existente: `/pocketbiz/personnel/professionals` y `/pocketbiz/personnel/specialties`, cada una con lista, `/new`, `/:id` y `/:id/edit`.

## Componentes/patrones elegidos
- Lista (§5, referencia products/product-list y purchases/supplier-list): breadcrumb, card, buscador por nombre, estado Activos por defecto, ngx-datatable con paginación de servidor. Profesionales añade filtro por especialidad. Nombre enlaza al detalle; estado textual y acciones compartidas `btn-tbl-*`.
- Formulario (§5, referencia product-form y supplier-form): Reactive Forms, labels asociados, nombre obligatorio, contactos y matrícula opcionales; especialidades multiselección por nombre, usuario opcional por nombre/username, opción explícita de desvincular. Guardar/Cancelar; errores por campo; conservar valores al fallar y bloquear doble envío. Un usuario no puede vincularse a más de un perfil; mostrar error del servidor bajo el selector sin perder el formulario.
- Detalle (§5, referencia product-detail y supplier-detail): `dl`, nombre, datos opcionales con «Sin …», especialidades por nombre y usuario vinculado, badge con texto, autoría/fechas; Editar, Activar/Desactivar y Volver.
- Activar/desactivar con confirmación usando los diálogos existentes. Sin campos, filtros ni columnas de sucursal, ni promesas de citas detectadas antes de implementar Agenda.

## Alternativas consideradas
Pantalla unificada en pestañas: menor navegación, pero se aparta de las listas/formularios/detalles pedidos. Se prefieren pantallas separadas, siguiendo el producto existente. No usar el calendario demo como Agenda.

## Comportamiento por privilegio/estado
Usar el permiso admin actual; ocultar acciones administrativas sin autorización y aplicar guard de módulo. El backend es la barrera de seguridad y valida cada petición. Mostrar cargando, vacío, errores de servidor y de campo, éxito, 403 y módulo deshabilitado (§4). Keyboard, foco visible, labels e iconos accesibles (§7). Claro/oscuro, móvil y escritorio; sin HEX, fuentes o tamaños propios.

## Consecuencias
Sin componente compartido nuevo ni desviación del sistema de diseño. El futuro diálogo de citas afectadas pertenece a la integración de Agenda; no mostrar una consulta ficticia en este alcance.

Refinamiento de implementación visual: en móvil ngx-datatable mantiene anchos mínimos de columnas y scroll horizontal nativo del contenedor Bootstrap table-responsive (mínimo de lectura 45rem), con aviso textual y foco de teclado; evita truncar el nombre/estado al forzar cuatro columnas en 390 px. Mantiene plantilla Lista y paginación; acciones importan shared/styles/table-actions con btn-tbl-edit + view/update/toggle. Sin componente nuevo.
