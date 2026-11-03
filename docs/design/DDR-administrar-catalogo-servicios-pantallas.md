# DDR-administrar-catalogo-servicios-pantallas

**Estado:** Propuesto
**Task relacionado:** TASK-administrar-catalogo-servicios
**Fecha:** 2026-11-02

## Contexto
PB-SRV-001 exige lista, formulario y detalle. Se aplican las plantillas de sección 5 de design-system.md y componentes de sección 3; referencias leídas: product-list, product-form y product-detail. No requiere un patrón nuevo ni cambios de tokens.
## Pantallas/flujos afectados
- Catálogo → Servicios: lista bajo `/pocketbiz/catalog/services`; alta `/new`, detalle `/:id` y edición `/:id/edit`. Son rutas propuestas contrastadas con app.routes.ts, actualmente libres.
- Lista: breadcrumb, card, título Servicios, búsqueda por nombre, estado inicialmente Activos, filtro de especialidad, alta «Nuevo servicio» y ngx-datatable paginada por servidor. Columnas nombre enlazado, precio, duración, especialidad, estado y acciones. Conservar filtros al volver del detalle.
- Formulario: nombre obligatorio, código opcional, descripción, precio base (Bs), duración (minutos), especialidad opcional y estado visible. Guardar/Cancelar, etiquetas asociadas y errores por campo. La activación/desactivación usa acción explícita como productos. Cancelar vuelve a detalle o lista; advertir cambios sin guardar.
- Detalle: card con nombre y dl.row; código/descripción/especialidad ausentes con texto «Sin …», precio money, duración con «min», estado con texto y fechas dd/MM/yyyy HH:mm. Editar, Activar/Desactivar y Volver.
## Componentes/patrones elegidos
Reactive Forms, money, Page, ngx-datatable, badge-outline col-green/col-red, btn-tbl-view/update/toggle; ng-select para especialidades cuando exista el proveedor. Bootstrap para grilla y tarjetas. Sin colores/tamaños propios ni componentes compartidos nuevos.
## Alternativas consideradas
Extender pantallas de producto mezclaría usos de inventario y duración; se mantiene maestro separado. Modal para todo el mantenimiento no sigue el flujo listado/formulario/detalle solicitado.
Sin Personal habilitado: selector/filtro deshabilitados con explicación; alta/edición sin esa referencia funcionan. Con Personal habilitado: mostrar especialidades activas, además de «Sin especialidad»; el filtro permite «Todas» y «Sin especialidad». Una referencia histórica inactiva se muestra en edición sin permitir nuevas asignaciones. Código se convierte a mayúsculas, también al guardar; backend aplica la misma regla.
## Comportamiento por privilegio/estado
Admin de empresa activa y módulo Servicios habilitado; frontend no es barrera de seguridad: backend valida rol, empresa, módulo y referencias. Acciones no autorizadas no se ofrecen; 403 visible y module_disabled reutiliza pantalla existente.
Carga en tabla/detalle, vacío inicial con alta, búsqueda sin resultados con Limpiar filtros, error con Reintentar, éxito visible. Formularios conservan datos al fallar y bloquean doble envío. Acciones de estado explican efecto sobre nuevos usos conservando historial. Teclado, labels, aria-label/title y foco visible; móvil/escritorio, claro/oscuro. No se ofrecen acciones de borrar.
## Consecuencias
Sin deuda visual adicional prevista. No mostrar cotizar/agendar como funcionalidad disponible antes de implementar sus historias. La selección de especialidades usa el contrato real de Personal; cuando su módulo no está habilitado, la limitación se informa en pantalla.
