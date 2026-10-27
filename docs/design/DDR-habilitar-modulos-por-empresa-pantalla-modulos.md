# DDR-habilitar-modulos-por-empresa-pantalla-modulos: Pantalla Configuración → Módulos

**Estado:** Propuesto
**Task relacionado:** TASK-habilitar-modulos-por-empresa
**Fecha:** 2026-10-27

## Contexto
El administrador necesita ver y cambiar qué módulos usa su empresa. El menú lateral debe mostrar solo los módulos habilitados.

## Pantallas/flujos afectados
1. **Menú lateral:** nuevo ítem «Configuración» (submenú «Módulos», `/settings/modules`) al final; los ítems de módulos se filtran por empresa. Aparecen «Compras» (`/purchases`) e «Inventario» (`/inventory`) cuando están habilitados.
2. **`/settings/modules`** (lista de módulos).
3. **Diálogo de confirmación** al habilitar o deshabilitar.
4. **Placeholder «Próximamente»** en `/purchases` e `/inventory`.

## Componentes/patrones elegidos
- **Lista** (design-system §5, referencia `features/expenses/pages/category-list` y `category-dialog`): breadcrumb (`Configuración › Módulos`), una `.card` con título `<h2><strong>Módulos</strong></h2>`. Se usa **tabla Bootstrap simple (`table`)**, no `ngx-datatable`: son ≤8 filas fijas, sin paginación ni búsqueda (desviación menor justificada).
- Columnas: **Módulo** (nombre en negrita + descripción en `<small class="text-muted">`), **Estado** (`badge-outline col-green` «Habilitado» / `col-red` «Deshabilitado»; módulos base: `col-blue` «Base»), **Requiere** (nombres; los faltantes con `text-danger`), **Integra con (opcional)** (nombres; disponible = texto normal con «disponible», no habilitado = `text-muted`), **Acción**.
- **Acción:** botón `btn btn-primary` «Habilitar» / `btn btn-warning` «Deshabilitar». Módulos base: sin botón, texto «Siempre activo». Si faltan dependencias: botón `disabled` con `title` y `aria-label` «Falta habilitar: …» y mensaje visible bajo el nombre en `text-danger` («Requiere habilitar primero: Ventas, Gastos»). Si otros módulos habilitados lo requieren: «Deshabilitar» bloqueado con «Lo requieren: …».
- **Diálogo** (`NgbActiveModal`, patrón de `category-dialog`): título «Habilitar módulo» / «Deshabilitar módulo»; resumen en `<dl>`: Módulo, Empresa (nombre del usuario), Requiere, Se verán afectados (módulos que dependen). Pie: `Confirmar` (primario, se deshabilita mientras guarda) y `Cancelar` (`btn-light`). Aviso en deshabilitar: «Los datos se conservan; la desactivación segura completa llega en una próxima versión.» No hay confirmación de dos pasos.
- **Placeholder:** `.card` con `h4` = nombre del módulo y texto «Próximamente. Este módulo aún no está disponible, pero ya está habilitado para tu empresa.»; botón `btn-light` «Volver al panel».
- Iconos del menú (feather): Configuración `settings`, Compras `shopping-bag`, Inventario `archive`.

## Alternativas consideradas
- **Tarjetas por módulo:** más visual, pero menos comparable (dependencias en columnas) y se aleja del patrón de lista. Descartada.
- **Interruptores (switch) en línea:** el diálogo exige confirmar con resumen; un switch induciría cambios sin confirmación. Descartada.
- **Ocultar módulos no disponibles:** se prefiere mostrarlos con motivo para que el admin sepa qué falta.

## Comportamiento por privilegio/estado
- **Estados:** cargando («Cargando…»), error de servidor (mensaje visible con «Reintentar»), éxito (toast «Módulo habilitado») y recarga del estado + menú sin recargar la página; error 409 del servidor se muestra en el diálogo con los nombres.
- **Privilegio:** solo admin de empresa activa. El frontend no es la barrera: el backend responde 403/409 (`CompanyAdminPermission` y reglas de dependencia). `moduleGuard` redirige a `/dashboard/main` (o a la primera ruta visible) si se entra a un módulo deshabilitado por URL; esto es comodidad, no seguridad (el bloqueo de API llega en PB-MOD-004).
- **Accesibilidad:** `label`/`aria-label` en botones, foco en el diálogo (ng-bootstrap), `table` con `<caption class="visually-hidden">`.

## Consecuencias
Se actualiza `docs/design/design-system.md` §6 (menú dinámico por módulos, ítem Configuración). Deuda: tabla Bootstrap simple en lugar de `ngx-datatable`; en móvil la tabla usa `table-responsive`.
