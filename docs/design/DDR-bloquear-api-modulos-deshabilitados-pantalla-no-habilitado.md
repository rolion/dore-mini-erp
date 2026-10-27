# DDR-bloquear-api-modulos-deshabilitados-pantalla-no-habilitado: Pantalla «Módulo no habilitado»

**Estado:** Propuesto
**Task relacionado:** TASK-bloquear-api-modulos-deshabilitados
**Fecha:** 2026-10-27

## Contexto
Hoy `moduleGuard` redirige en silencio a `/catalog/products` cuando se abre un módulo deshabilitado. La historia pide un mensaje claro y una acción para volver, y que un rechazo de la API no deje una tabla vacía que parezca válida.

## Pantallas/flujos afectados
- Nueva ruta `/module-disabled` (con `?module=<key>` opcional), dentro del layout autenticado.
- `moduleGuard` navega a ella en lugar de redirigir en silencio.
- `errorInterceptor` ante un `403` con `code: 'module_disabled'`: recarga los módulos (el menú se actualiza) y navega a la pantalla; el error se propaga para que ninguna lista lo muestre como «sin resultados».
- Sin sesión: 401 → login existente (sin cambios).

## Componentes/patrones elegidos
Pantalla simple de `docs/design/design-system.md` (§5, patrón de `coming-soon`): `section.main-content`, breadcrumb, `.card` con `<h2><strong>Módulo no habilitado</strong></h2>`, texto explicativo (nombra el módulo si llega por query) y botón `btn btn-primary` «Volver al inicio». Sin colores ni fuentes propios. Textos en español.

## Alternativas consideradas
- Redirigir en silencio (actual): no explica nada.
- Toast + redirección: se pierde con la navegación y no sirve al abrir una URL guardada.

## Comportamiento por privilegio/estado
- Estados: solo estático (sin carga ni vacío). «Volver al inicio» lleva a `/dashboard/main` si Reportes está habilitado y a `/catalog/products` si no (siempre válido: Catálogo es base).
- El frontend no es la barrera: el backend rechaza igualmente (ver ADR).

## Consecuencias
Una pantalla nueva y pequeña; se actualiza `design-system.md` §6 con la nota de que un módulo deshabilitado lleva a `/module-disabled`.
