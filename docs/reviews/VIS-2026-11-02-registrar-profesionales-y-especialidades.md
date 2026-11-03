# Inspección visual — Personal (PB-PER-001)

**Fecha:** 2026-11-02 · **PLAN:** v3 · **Entorno:** datos sintéticos locales; sin despliegue.

Navegador integrado, Angular localhost:4206 y API con PostgreSQL temporal. Viewports 1440×1000 y 390×844; claro/oscuro. Se restauró el viewport al terminar.

## Flujo observado
1. Entrar con admin sintético, Personal habilitado; lista vacía con explicación y carga.
2. Crear especialidad «Ortodoncia de prueba», guardar y consultar detalle.
3. Crear «Profesional sin login» con solo nombre: detalle muestra Sin usuario y Sin especialidades, éxito y autoría.
4. Editar; seleccionar especialidad por nombre con ArrowDown/Enter; vincular usuario sintético por nombre/username; guardar sin cambios de permisos.
5. Desactivar con confirmación; observar Inactivo, vínculo, especialidad y autoría preservados. Filtro Inactivos muestra el registro.
6. Revisar lista/formulario/detalle en móvil y escritorio, claro/oscuro. Labels asociados y controles de teclado; confirmaciones con botones identificables. El control definitivo de unicidad/aislamiento/concurrencia se prueba en integración API, no se infiere de estas capturas.

## Correcciones derivadas
- Chip multiselección en oscuro heredaba texto rgb(51,51,51) sobre fondo rgb(14,14,14). Selector exclusivo de app-personnel-form aplica el token existente $color-font; verificado después con rgb(150,162,180), sin cambiar otros formularios.
- Cuatro columnas forzadas en 390px truncaban nombre/estado. Wrapper Bootstrap table-responsive con foco/aviso textual y mínimo720px (45rem) conserva legibilidad; ancho observado265px/contenido720px. ResizeObserver recalcula cuando el sidebar termina de cambiar el ancho; desconexión al destruir.
- Acciones usan el mixin compartido y clases correctas view/update/toggle; título table-title del producto.

## Evidencia
Todas las imágenes contienen exclusivamente datos sintéticos. Las capturas de listas finales incluyen el ajuste responsive; las de formulario/detalle verifican las mismas plantillas, que no cambian con ese ajuste.

- [Lista escritorio clara](evidence/personnel/desktop-light-list.jpg)
- [Lista escritorio oscura](evidence/personnel/desktop-dark-list.jpg)
- [Lista móvil clara](evidence/personnel/mobile-light-list.jpg)
- [Lista móvil oscura](evidence/personnel/mobile-dark-list.jpg)
- [Formulario escritorio oscuro](evidence/personnel/desktop-dark-form.jpg)
- [Formulario móvil claro](evidence/personnel/mobile-light-form.jpg)
- [Formulario móvil oscuro](evidence/personnel/mobile-dark-form.jpg)
- [Detalle escritorio claro, alta mínima](evidence/personnel/desktop-light-detail.jpg)
- [Detalle móvil claro, desactivado](evidence/personnel/mobile-light-detail.jpg)
- [Detalle móvil oscuro](evidence/personnel/mobile-dark-detail.jpg)

No se prueba Agenda: su integración es alcance futuro explícito de la tarjeta. La deuda visual de layout/login ajena al feature no se modifica.

Nota de captura final: la opción fullPage del navegador provocó un reflow temporal al exportar dos vistas oscuras móviles, distinto de la pantalla inspeccionada. Se reemplazaron mobile-dark-list y mobile-dark-detail por los mismos bytes de la captura real del viewport (getScreenshot), sin modificar imágenes. El revisor independiente reabre los archivos para validar la evidencia persistida.
