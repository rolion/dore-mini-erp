# TASK-odontologia-boton-ver-pacientes: Botón "ver" de la tabla de pacientes (Odontología)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** TRIVIAL_FIX
**Diseño requerido:** NO
**Rama:** task/TASK-odontologia-boton-ver-pacientes
**Pull Request:** _sin abrir todavía_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-26 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-26 | INVESTIGATION → ENGINEERING | TRIVIAL_FIX, sin plan ni PR previo | delivery-start |
| 2026-11-26 | ENGINEERING → REVIEW | Implementación completa | delivery-build |
| 2026-11-26 | REVIEW → PUBLISH | Quality Gate PASS | delivery-publish |

## Investigación

### Requerimiento
En el módulo de odontología, en la tabla de pacientes, el botón de ver se ve gris y el icono no está centrado; debe ser azul y con el icono centrado.

### Hechos encontrados
- `frontend/panel_admin/src/app/features/dentistry/pages/patient-list.component.html:39` — el botón usa `btn btn-tbl-edit btn-tbl-view h-auto`.
- `frontend/panel_admin/src/app/shared/styles/_table-actions.scss:2-18` — define el centrado (inline-flex, padding 0) y el azul `#1677ff` de `.btn-tbl-view`.
- `frontend/panel_admin/src/app/features/dentistry/pages/patient-list.component.ts:17-20` — el componente no declara `styleUrl`, por lo que esos estilos no se aplican (encapsulación de componente); otras listas (p. ej. `services/pages/service-list.component.ts:24`) sí importan la hoja con `@use`.
- `docs/design/design-system.md:64` — las acciones de tabla deben usar `shared/styles/_table-actions.scss`.

### Hipótesis / supuestos no confirmados
- Ninguna relevante.

### Veredicto de complejidad
**TRIVIAL_FIX** — falta enlazar la hoja de estilos compartida al componente; sin lógica, contrato ni modelo.

### Diseño requerido
**NO** — ajuste cosmético que alinea con el sistema de diseño existente.

## Diseño
No aplica.

## Arquitectura
No aplica según veredicto.

## Plan
No aplica — TRIVIAL_FIX. Cambio: crear `patient-list.component.scss` con `@use '../../../shared/styles/table-actions';` y añadir `styleUrl` al componente.

## Implementación
Se añadió `patient-list.component.scss` con `@use` de `shared/styles/table-actions` y `styleUrl` en el componente (mismo patrón que `service-list`). Resultado esperado: botón «ver» azul (`#1677ff`) con icono centrado. Sin desviaciones. El build lo verificó el Quality Gate (ver Review).

## Review
**PASS** (subagente aislado, 2026-11-26): `npm run build` OK (solo avisos de la plantilla), `npm run lint` OK, pruebas de `features/dentistry` 70 OK. Sin hallazgos Critical/High/Medium. Revisión visual **no verificada** (no se levantó la app).

## Publicación
PR #135 listo para aprobación humana. Cambio sin impacto arquitectónico, de auth ni de base de datos.
