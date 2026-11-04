# PLAN-2026-11-04-mejorar-ux-catalogo-productos-servicios (v1)

**Task:** TASK-mejorar-ux-catalogo-productos-servicios · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-mejorar-ux-catalogo-productos-servicios-lista-detalle-formulario · ADR vigente: ADR-catalogo-usos-del-producto-modelo-migracion-y-contrato (sin cambios)

## Objective
Que quien administra el catálogo vea de un vistazo para qué sirve cada producto (vendible, comprable, insumo) y tenga pantallas de Productos y Servicios coherentes entre sí, sin cambios de backend.

## Context
Ver `docs/tasks/TASK-mejorar-ux-catalogo-productos-servicios.md`. Alcance acordado: listas, detalles y formularios de Productos y Servicios en un PR.

# Specification

## Domain context
Bounded context `catalog`. Inventario consume los mismos datos pero no se modifica.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Vendible | `can_sell` verdadero | `product.py:77` |
| Comprable | `can_buy` verdadero | `product.py:76` |
| Insumo | Clasificación visual: categoría `raw_material`, `packaging` o `intermediate` (puede usarse para producir otros productos). **No es un dato ni una regla** | Decisión del usuario 2026-11-04; ADR de usos |
| Sin usos | Ni vendible, ni comprable, ni insumo | `stock-list.component.html:147` |

Inconsistencia declarada: Productos usa «Compra/Venta» y Inventario «Comprable/Vendible»; se unifica en «Vendible/Comprable».

## Current behavior
Ver TASK, «Hechos encontrados».

## Expected behavior
Productos y Servicios muestran los datos con la jerarquía del DDR: chips de usos, precio con `money`, resumen por cifras en el detalle, y acciones, buscador, iconos y etiquetas consistentes entre ambos módulos.

## Domain rules / invariants
- INV-01 (existente, ADR de usos): la categoría no restringe usos ni cambia validaciones; el chip «Insumo» es solo presentación y no cambia lo que se puede guardar, vender o comprar.
- INV-02 (existente): precio de venta obligatorio solo si `can_sell`.

## Acceptance criteria
- AC-01: Lista de Productos: columna **Usos** con chips de texto Vendible/Comprable/Insumo según la regla, o «Sin usos»; ya no existen «Compra/Venta».
- AC-02: «Insumo» aparece exactamente cuando la categoría es materia prima, empaque o intermedio, y no con terminado, mercadería ni sin clasificar. Un producto puede mostrar varios chips (p. ej. Queso: Comprable + Vendible + Insumo).
- AC-03: Lista de Productos muestra el precio con `money` alineado a la derecha (vacío «—» si no se vende); desaparece la columna «Controla stock»; «Unidad base» se mantiene con Inventario habilitado.
- AC-04: Los filtros de la lista no solapan el chevron con el texto y siguen funcionando igual (estado, uso, categoría).
- AC-05: Detalle de Producto: cabecera con nombre, badge de estado y chips de usos; fila de cifras (Precio de venta, Categoría y, con Inventario, Unidad base); descripción y fechas como secundarios; sin filas «Sí/No» de Se compra/Se vende; acciones sin cambios.
- AC-06: Formulario de Producto: ayudas pegadas a su control, espacio entre interruptor y etiqueta, y línea «Se mostrará como:» que refleja en vivo canSell/canBuy/categoría; guardar y validaciones iguales que hoy.
- AC-07: Lista de Servicios: botones de acción con los colores estándar (`table-actions`) e iconos `fas`; buscador con icono; precio con `money` a la derecha; inactivos atenuados.
- AC-08: Detalle de Servicio con la misma estructura que el de Producto (cifras: Precio base, Duración, Especialidad) y etiqueta «Última actualización».
- AC-09: Formulario de Servicio con el mismo pie y espaciado que el de Producto; sin cambio de validaciones.
- AC-10: Todos los textos nuevos con claves en `es.json`, `en.json` y `pt.json`; moneda «Bs» y fechas `dd/MM/yyyy HH:mm`.
- AC-11: Accesibilidad: chips con texto (no solo color), `title`/`aria-label` en iconos, ayudas con `aria-describedby`, contraste de texto atenuado ≥ 4,5:1 con las clases existentes.

## Edge cases / Error cases
- EDGE-01: producto sin categoría (por revisar): sin chip «Insumo», «Por revisar» naranja en categoría.
- EDGE-02: producto no vendible, no comprable y categoría terminado: «Sin usos».
- EDGE-03: producto que controla stock sin Inventario habilitado: no se muestran columnas ni cifras de Inventario.
- EDGE-04: lista vacía o con filtros: mensaje de §4 sin cambios; error de servidor con «Reintentar».
- EDGE-05: Servicios sin Personal habilitado: la especialidad se muestra «Sin especialidad» atenuado.

## Authorization / permissions
Sin cambios; el backend sigue validando.

## API contract
Sin cambios (API-01: ninguno).

## UI behavior
UI-01 a UI-05 = secciones Lista, Detalle y Formulario del DDR, sobre las plantillas Lista/Detalle/Formulario de `design-system.md` §5.

## Non-functional requirements
Móvil ≈390 px y escritorio ≈1440 px, tema claro y oscuro; sin dependencias nuevas.

## Out of scope
Backend, migraciones, filtro por «Insumo», bloques «Hecho con / Se usa en», migrar el marcado de Inventario al componente nuevo, rediseño de acciones de fila (menú «⋯»).

## Open questions
Ninguna que bloquee: el tooltip «Price» de Servicios y el conteo «9 en total» de Productos se verifican durante la implementación (TASK, hipótesis).

# Test Specification

## Unit tests / Integration tests
- Karma: función pura `productUses(...)` (AC-01, AC-02, EDGE-01, EDGE-02) y componente `app-product-uses`.
- Specs de `product-list`, `product-detail`, `product-form` actualizados (AC-01 a AC-06, EDGE-03, EDGE-04).
- Specs de `service-pages` actualizados (AC-07 a AC-09).
- Prueba de claves i18n existente y `npm run i18n:check` (AC-10).
- E2E: **NO** — no hay flujo crítico nuevo; verificación visual manual en navegador contra el build.

## Regression tests
Specs de Inventario (`stock-list`, `stock-detail`) deben seguir en verde (no se tocan).

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-02 | Unit `productUses` + spec de lista |
| AC-03, AC-04 | Spec de `product-list` + revisión visual |
| AC-05 | Spec de `product-detail` |
| AC-06 | Spec de `product-form` |
| AC-07, AC-08, AC-09 | `service-pages.spec.ts` + revisión visual |
| AC-10 | Prueba i18n + `npm run i18n:check` |
| AC-11 | Specs (roles/labels) + revisión visual y de contraste |

# Implementation Plan

## Architecture considerations
Solo frontend. Componente presentacional sin servicios en `shared/components/product-uses`, con la regla en una función pura exportada; standalone y `OnPush`. Sin suscripciones nuevas.

## Proposed solution
Ver DDR. Estilos con utilidades Bootstrap/plantilla y clases existentes; sin HEX nuevos.

## Files/components affected
- Nuevo: `frontend/panel_admin/src/app/shared/components/product-uses/` (componente, función y spec).
- `features/products/pages/product-list|product-detail|product-form` (HTML, SCSS, specs) y `models/product.ts` si hace falta un helper.
- `features/services/pages/service-list|service-detail|service-form` (HTML, SCSS), `components/service-toggle.component.ts` (icono `fas`), `service-pages.spec.ts`.
- `src/assets/i18n/{es,en,pt}.json` (claves nuevas bajo `PRODUCTS` y `SERVICES`).
- `docs/design/design-system.md` (§3 componente nuevo, §5 lista/detalle de Catálogo).

## Implementation steps
1. Componente `app-product-uses` + función `productUses` + claves i18n (AC-01, AC-02, EDGE-01/02, AC-10).
2. Lista de Productos: columnas, `money`, filtros y atenuado de inactivos (AC-01, AC-03, AC-04).
3. Detalle de Producto con cifras y chips (AC-05).
4. Formulario de Producto con línea «Se mostrará como» y ajustes de espaciado/ayudas (AC-06, AC-11).
5. Servicios: lista (importar `table-actions`, iconos, buscador, `money`), detalle y formulario (AC-07 a AC-09). Verificar y, si se reproduce, corregir el tooltip «Price» y el conteo «9 en total».
6. Actualizar `design-system.md` y specs; ejecutar `npm test`, `npm run lint`, `npm run i18n:check`, `npm run build`; revisión visual en 1440 px y 390 px, claro y oscuro (AC-11).

## Database / migrations
No aplica.

## Risks
- Cambiar columnas rompe specs de `product-list`: actualizarlas en el paso 2.
- Contraste de texto atenuado en tema oscuro: revisar en el paso 6.

## New dependencies
Ninguna.
