# DDR-crm-tableros-columnas-configurables-editor-de-etapas: Pantalla CRM → Tablero y editor de etapas

**Estado:** Propuesto
**Task relacionado:** TASK-crm-tableros-columnas-configurables
**Fecha:** 2026-11-24

## Contexto
La persona administradora define las etapas comerciales de su empresa. Debe poder crear/renombrar/ordenar/archivar etapas sin perder tarjetas. No hay pantalla comparable de «tablero»; el patrón más cercano de configuración con listado y diálogo es `features/inventory/pages/inventory-configuration` (`docs/design/design-system.md` §5).

## Pantallas/flujos afectados
- Menú lateral: ítem **Tablero** dentro del submenú **CRM** (`/pocketbiz/crm/board`, módulo `customers`). Si el PR 120 no entró aún, este PR crea el submenú; en merge se unifican.
- Pantalla **CRM → Tablero** (nueva, `features/crm/pages/crm-board`): selector de tablero, acciones de tablero (crear, renombrar, archivar/reactivar) y lista editable de etapas.
- Diálogo **Archivar etapa** con selector de etapa destino cuando la etapa tiene tarjetas.

## Componentes/patrones elegidos
- Plantilla **Configuración con listados en pestañas y diálogo** adaptada sin pestañas: breadcrumb, `.card` con `h4`, `form-select` «Tablero» (solo activos; opción para ver archivados), botones «+ Nuevo tablero» y «Renombrar»/«Archivar» (`btn-light`/`btn-warning`).
- Lista de etapas en tabla Bootstrap simple apilada en móvil (`inventory/components/_inventory-table.scss` como referencia): columnas **Orden**, **Nombre** (edición en línea con confirmar/cancelar) y **Acciones**. Ordenar con botones **Subir/Bajar** (iconos con `title` y `aria-label`; sin arrastrar, accesible por teclado y en móvil). Cada cambio de orden se guarda enseguida con una sola llamada y la lista se recarga con la respuesta.
- Alta de etapa: campo + «Agregar etapa» al pie de la lista. Alta/renombrado de tablero y archivar etapa: diálogo `NgbModal` (patrón `category-dialog`/`movement-reverse-dialog`).
- Archivar etapa **sin** tarjetas: confirmación simple. **Con** tarjetas: el diálogo muestra «Esta etapa tiene N tarjetas» y obliga a elegir una etapa destino activa del mismo tablero; el botón «Archivar y mover» se habilita al elegir.
- Sin desviaciones del sistema de diseño ni patrón nuevo; el arrastre (`cdk`) se descarta (ver alternativas).

## Alternativas consideradas
- Arrastrar y soltar con `@angular/cdk/drag-drop`: más vistoso, peor accesibilidad y más pruebas; los botones cubren el requisito. Descartada para el MVP.
- Vista de columnas tipo Kanban para editar: mezclaría configuración con el tablero de oportunidades (PB-CRM-004). Descartada.
- Guardar el orden con un botón «Guardar»: permite estados intermedios que se pierden al salir; el guardado inmediato evita avisos de salida. Elegido el inmediato.

## Comportamiento por privilegio/estado
- **Cargando:** texto «Cargando…». **Sin tableros:** estado vacío «Aún no hay tableros» con «Crear tablero». **Tablero sin etapas:** «Este tablero no tiene etapas» y el campo para agregar. **Error de servidor:** `alert alert-danger` con «Reintentar». **Errores de validación** (nombre vacío/duplicado/largo): `small.text-danger` junto al campo con el mensaje del servidor. **409** (orden desactualizado, tablero con tarjetas): `alert alert-warning` y recarga de la lista. **Éxito:** la lista refleja el cambio; recargar la página conserva el orden.
- Solo el rol admin accede (único rol hoy); el servidor responde 403 a otros y lo muestra el manejo de errores común. El frontend no es la barrera de seguridad: la empresa sale del token, los ids ajenos devuelven 404.

## Consecuencias
Todo el texto va por claves i18n (es/en/pt). Deuda aceptada: sin arrastre, y sin vista de tarjetas hasta PB-CRM-004. Se agrega al sistema de diseño una línea en §5 que referencia esta pantalla como variante «Editor de lista ordenable con botones Subir/Bajar».
