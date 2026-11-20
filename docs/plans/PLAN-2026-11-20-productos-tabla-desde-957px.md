# PLAN-2026-11-20-productos-tabla-desde-957px (v1)

**Task:** TASK-productos-tabla-desde-957px · **Modo:** COMPACTO · **Specification readiness:** READY
**DDRs / ADRs:** Ninguno

## Objective
La lista de productos muestra tarjetas solo con ancho de pantalla menor a 957 px; desde 957 px muestra una tabla con las mismas columnas y acciones.

# Specification
- **Expected behavior:** `< 957 px` → vista actual (tarjetas, filtros plegables con «Aplicar»). `≥ 957 px` → tabla (`table-responsive > table.table`) con columnas Nombre (enlace al detalle), Categoría, Usos, Precio (derecha), Estado, Unidad base (solo con Inventario habilitado) y Acciones (ver, editar, activar/desactivar), filtros siempre visibles y aplicados al instante. La vista cambia al redimensionar.
- **Acceptance criteria:**
  - AC-01: con `compact = false` (≥ 957 px) se renderiza la tabla y no hay tarjetas.
  - AC-02: con `compact = true` (< 957 px) se renderizan tarjetas y no hay tabla.
  - AC-03: la tabla muestra los mismos datos que la tarjeta (categoría / «Por revisar», usos, precio con `money` o «—», estado, unidad base solo con Inventario), con filas de productos inactivos atenuadas.
  - AC-04: las acciones de la tabla (ver, editar, activar/desactivar con confirmación) funcionan igual que en la tarjeta.
  - AC-05: el corte es 957 px (`max-width: 956.98px`) tanto para tarjetas como para los filtros plegables.
  - AC-06: paginación y contador «n en total» se conservan en ambas vistas.
- **Edge/error cases:** vacío y error de carga sin cambios; sin texto hardcodeado (claves existentes `COMMON.*`/`PRODUCTS.PRODUCT_LIST.*`; i18n:check debe pasar).
- **Out of scope:** otras listas salvo Servicios (siguen en 992 px), backend, nuevas columnas u ordenamiento.

## Ampliación (v1.1, pedida por el usuario en el chat)
La misma regla aplica a `features/services/pages/service-list` (AC-01..AC-05 sobre Servicios; el botón «Aplicar» se conserva también en escritorio).

# Test Specification
- Unit (Karma, `product-list.component.spec.ts`): AC-01 y AC-02 (alternando `compact`), AC-03 (datos en filas de la tabla, inactivo atenuado, unidad base según Inventario), AC-04 (toggle desde la tabla), AC-05 (`COMPACT_QUERY` vale `(max-width: 956.98px)`), AC-06 (paginación presente). Se adaptan los specs que hoy asumen tarjetas en escritorio.
- **E2E: NO** — cambio de presentación cubierto por pruebas de componente.

# Implementation Plan
- **Files affected:** frontend: `features/products/pages/product-list/product-list.component.{ts,html,scss,spec.ts}`; `docs/design/design-system.md` (nota del corte 957 px en la lista de productos).
- **Steps:**
  1. `ts`: `COMPACT_QUERY = '(max-width: 956.98px)'` y comentario (AC-05).
  2. `html`: envolver las tarjetas en `@if (compact)` y añadir `@else` con la tabla `table-responsive`, reutilizando `ng-template` para categoría, usos, estado y acciones y `data-testid` análogos (AC-01..04, AC-06).
  3. `scss`: `$compact-max: 956.98px`; estilos mínimos de la tabla (acciones circulares como en la tarjeta, fila atenuada).
  4. `spec`: actualizar y añadir pruebas (AC-01..06).
  5. `design-system.md`: indicar que Productos corta en 957 px.
- **Risks / New dependencies:** Ninguna dependencia. Riesgo: entre 957 y 991 px el formulario de filtros usa `col-md-6` (2 columnas); aceptable.
