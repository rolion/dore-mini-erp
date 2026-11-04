# TASK-mejorar-ux-catalogo-productos-servicios: Mejorar cómo se muestran Productos y Servicios del catálogo

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-mejorar-ux-catalogo-productos-servicios
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/55

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-04 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-04 | INVESTIGATION → DESIGN | Pantallas afectadas, diseño requerido | delivery-start |
| 2026-11-04 | DESIGN → PLANNING | DDR propuesto; Specification READY | delivery-start |
| 2026-11-04 | PLANNING → ENGINEERING | Plan v1 y PR | delivery-start |
| 2026-11-04 | ENGINEERING → REVIEW | Implementación completa | delivery-build |

## Investigación

### Requerimiento
Fase de refinamiento. Las vistas de Catálogo (lista, detalle y formulario de Productos y de Servicios) muestran los datos como filas sueltas y no comunican para qué sirve cada producto: **un producto puede venderse, comprarse o usarse para producir otro producto**. Se pide mejorar UX/UI de esas pantallas. Crítica de diseño previa con capturas de las seis pantallas (sesión del 2026-11-04).

Aclaraciones del usuario (2026-11-04):
- «Usado para producir otro producto» se **deriva de la categoría** (materia prima, empaque, intermedio); no se añade dato nuevo ni cambio de backend.
- Alcance: listas + detalles + formularios, de Productos y de Servicios, en un solo PR.

### Hechos encontrados
- `backend/modules/catalog/domain/product.py:11` — categorías: `raw_material`, `packaging`, `intermediate`, `finished`, `merchandise`.
- `backend/modules/catalog/domain/product.py:76-77` — los usos son solo `can_buy` y `can_sell`; no existe un campo de «uso en producción».
- `docs/adr/ADR-catalogo-usos-del-producto-modelo-migracion-y-contrato.md` — decisión vigente: categoría, `can_buy` y `can_sell` independientes; la categoría solo organiza y filtra; ningún `type` excluyente.
- `docs/tasks/TASK-catalogo-usos-del-producto.md:46` — «Producir» no tiene módulo (Producción fuera del MVP, `CLAUDE.md`, `ddd.md:1257-1290`: Recipe/Ingredient son futuro). No hay receta ni «Se usa en».
- `frontend/panel_admin/src/app/features/products/pages/product-list/product-list.component.html:88-100` — columna «Uso» con badges «Compra» (azul) y «Venta» (verde); no hay insumo.
- `…/product-list.component.html:101-105` — el precio se muestra como texto crudo (`row.salePrice`) sin pipe `money`; en Servicios sí usa `money` (`service-list.component.html:31`).
- `…/product-list.component.html:106-124` — tres columnas de badge outline (Uso, Estado, Controla stock Sí/No) con la misma forma visual.
- `…/product-list.component.html:38-59` — tres `select.form-select.w-auto` en línea; en la captura «Todos los usos» y «Todas las categorías» tienen el chevron encima del texto.
- `…/product-detail.component.html:23-59` — `dl.row` plano de 11 filas; «Se compra/Se vende/Controla stock» como «Sí/No»; precio sin `money`; fechas «Creado»/«Última actualización».
- `…/product-form.component.html:46-92` — `h5` «Usos del producto» con categoría + dos interruptores; la ayuda de cada interruptor queda separada del control.
- `frontend/panel_admin/src/app/features/services/pages/service-list.component.scss:1` — solo contiene la regla móvil; **no hace `@use` de `table-actions`**, por eso los botones de acción aparecen grises (en Productos, `product-list.component.scss:1` sí lo importa). Además usa iconos `material-icons` (`service-list.component.html:36-37`, `service-toggle.component.ts:16`) y Productos usa `fas`.
- `…/service-detail.component.html:18` — etiqueta «Actualizado» (`SERVICES.SERVICE_DETAIL.ACTUALIZADO`) frente a «Última actualización» (`COMMON.ULTIMA_ACTUALIZACION`) en Productos.
- `…/service-list.component.html:12` — el buscador de Servicios no lleva el icono `search` que sí tiene el de Productos (`product-list.component.html:32`); en la captura se ve como un input nativo sin estilo.
- `frontend/panel_admin/src/app/features/inventory/pages/stock-list/stock-list.component.html:141-147` y `stock-detail…:55-61` — Inventario ya muestra los usos con badges de texto («Comprable» azul, «Vendible» verde, «Sin usos» gris) y la categoría «Sin clasificar»; `design-system.md` §5 (lista de solo lectura) lo documenta. Es duplicación de marcado, no un componente compartido.
- `docs/design/design-system.md` §3, §4, §5, §7 — Lista/Formulario/Detalle, badges outline, `money`, accesibilidad mínima.

### Hipótesis / supuestos no confirmados
- El fondo azul claro de los inputs de las capturas proviene del tema/skin o del autocompletado del navegador: no aparece en la plantilla de los componentes. No se toca; se verifica en el build.
- El tooltip negro «Price» fijo en la cabecera de Servicios (captura) es de `ngx-datatable`/CSS del tema; la causa no está confirmada en el código. Se investiga en implementación y, si no es reproducible, se descarta.
- «9 en total» con 8 filas visibles (captura de Productos): puede ser un producto en otra página o un conteo desfasado; no se ha reproducido. Se verifica en el build con datos reales; si es un fallo se registra aparte.

### Módulos y dependencias relacionadas
Solo `catalog` (frontend `features/products`, `features/services`) y `src/assets/i18n/{es,en,pt}.json`. Inventario consume los mismos datos pero no se modifica.

### Implementaciones similares existentes
`features/inventory/pages/stock-detail` (detalle con secciones y badges de uso), `features/customers/pages/*` (perfil de cliente con cifras, TASK-mejorar-perfil-de-cliente, PR #53) para el estilo de resumen por cifras.

### Comportamiento actual
Ver «Hechos encontrados». El administrador no ve de un vistazo para qué sirve un producto y debe leer filas «Sí/No».

### Restricciones
- Sin cambios de API, dominio ni migraciones (decisión del usuario).
- Textos por claves de traducción en las tres lenguas; estilos con clases/variables existentes; dinero con `money`.
- La categoría no restringe usos (ADR vigente): el chip «Insumo» es una **clasificación visual**, nunca una regla.

### Riesgos identificados
- Un negocio que clasifica mal un producto vería un «Insumo» engañoso: el chip lleva explicación «según su categoría».
- Cambiar columnas de la lista rompe pruebas existentes de `product-list` y `stock`; se actualizan en el mismo PR.

### Veredicto de complejidad
**NEEDS_PLAN** — cambio acotado a frontend sin decisión arquitectónica nueva; no toca backend, contrato ni datos.

### Diseño requerido
**SI** — seis pantallas con rediseño de jerarquía y un patrón nuevo reutilizable (chips de uso, resumen por cifras).

## Diseño
`docs/design/DDR-mejorar-ux-catalogo-productos-servicios-lista-detalle-formulario.md` (Propuesto).

## Arquitectura
No aplica según veredicto.

## Plan
`docs/plans/PLAN-2026-11-04-mejorar-ux-catalogo-productos-servicios.md` (v1, COMPLETO, READY).

## Implementación
Solo frontend, sin backend ni migraciones.

- **Componente nuevo** `shared/components/product-uses` (`app-product-uses` + `productUses()`): chips Vendible / Comprable / Insumo / Sin usos; «Insumo» se deriva de la categoría (AC-01, AC-02, EDGE-01, EDGE-02, INV-01).
- **Lista de Productos:** columna Usos, precio con `money` a la derecha, sin «Controla stock», unidad base solo si controla stock, inactivos atenuados, chevron de los filtros sin solape (AC-01, AC-03, AC-04).
- **Detalle de Producto:** cabecera con estado y usos, cifras (precio, categoría, unidad base), secundarios y fechas al pie (AC-05).
- **Formulario de Producto:** venta con su precio debajo, compra, línea «Se mostrará como:» en vivo (`toSignal`), espacio interruptor/etiqueta, ayudas con `aria-describedby` (AC-06, AC-11).
- **Servicios:** lista con `table-actions` importado (causa de los botones grises), iconos `fas`, buscador con icono, precio a la derecha, inactivos atenuados; detalle con cifras y etiqueta común; espaciado del formulario (AC-07 a AC-09).
- **i18n:** claves nuevas `PRODUCTS.PRODUCT_USES.*`, `PRODUCT_LIST.USOS`, `PRODUCT_FORM.ORGANIZA_Y_MUESTRA_INSUMO` en es/en/pt (AC-10).
- **Sistema de diseño:** `design-system.md` §3 (componente) y §5 (Catálogo).

**Pruebas propias** (no es el Quality Gate): specs de products/services/product-uses 87/87 OK; `npm run i18n:check` 0 faltantes; `npm run lint` OK. La suite completa dio 1 fallo distinto y ajeno en cada corrida (specs de idioma/stock, estado global de idioma); el mismo fallo de idioma ocurre en `origin/main`.

**Desviaciones respecto al plan:** ninguna de alcance. Las claves antiguas `PRODUCT_LIST.USO/VENTA/CONTROLA_STOCK` y `SERVICE_DETAIL.ACTUALIZADO` quedan sin uso en los catálogos (limpieza pendiente).

**Verificación pendiente / hipótesis del TASK:** no se pudo reproducir el tooltip «Price» de Servicios ni el conteo «9 en total» (no hay datos reales); revisión visual a 1440/390 px y tema oscuro por hacer en `delivery-publish`. `ng build` no se pudo ejecutar al final por un problema de entorno (ver más abajo).

**Deuda técnica:** Inventario conserva su marcado de badges propio; filtro por «Insumo» y bloques «Hecho con / Se usa en» quedan para cuando exista Producción.

**Pantallas de referencia seguidas:** `product-list`, `product-detail`, `product-form`. **Componentes compartidos reutilizados:** `money`; creado: `app-product-uses`.

## Review
_Pendiente_

## Publicación
_Pendiente_
