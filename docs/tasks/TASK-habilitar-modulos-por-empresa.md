# TASK-habilitar-modulos-por-empresa: Habilitar módulos por empresa (PB-MOD-001)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-habilitar-modulos-por-empresa
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/15

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-27 | (nuevo) → INVESTIGATION | Task creado; `main` ya estaba al día | delivery-start |
| 2026-10-27 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE (nuevo modelo por empresa, contrato API y navegación) | delivery-start |
| 2026-10-27 | PLANNING → ENGINEERING | Specification READY tras respuestas del usuario (ver Plan) | delivery-start |

## Investigación

### Requerimiento
PB-MOD-001 · Habilitar módulos por empresa (Modularidad, P0). Como administrador, quiero habilitar los módulos que necesita mi empresa. Menú Configuración → Módulos (`/settings/modules`), solo admin de la empresa. Muestra nombre, descripción breve, estado, dependencias obligatorias y disponibilidad de integración opcional. Acciones Habilitar/Deshabilitar; módulos base sin interruptor; diálogo de confirmación con módulo, empresa y dependencias afectadas. Al habilitar Inventario y recargar aparece su menú solo en esa empresa; con dependencias faltantes se muestran sus nombres y la acción queda bloqueada. Cada empresa conserva su selección; Acceso/Empresa y Catálogo son base; Ventas, Clientes, Gastos, Reportes, Compras e Inventario tienen dependencias explícitas; no instala código ni migra por empresa. La desactivación segura se completa en PB-MOD-004.

**Aclaraciones del usuario (2026-10-27):**
1. Mapa de dependencias = propuesta del código: Ventas→Catálogo (opcional Clientes); Clientes→ninguna; Gastos→ninguna; Reportes→Ventas y Gastos (opcional Clientes); Compras→Catálogo y Gastos; Inventario→Catálogo (opcional Ventas, Compras).
2. Compras e Inventario son habilitables y su menú apunta a una pantalla placeholder «Próximamente».
3. Empresas existentes y nuevas arrancan con Catálogo, Clientes, Ventas, Gastos y Reportes habilitados; Compras e Inventario deshabilitados.
4. Esta historia oculta menú y rutas; el bloqueo 403 en la API de negocio y la desactivación segura quedan para PB-MOD-004.

### Hechos encontrados
- `backend/modules/accounts/models.py:9` — `Company` (UUID, `is_active`); `User.company`/`role` en `:34-40`. No existe ningún concepto de módulo habilitado.
- `backend/modules/accounts/api/permissions.py:4` — `CompanyAdminPermission` es el permiso por defecto de DRF (`config/settings/base.py:86`): autenticado, empresa activa y rol admin. Sirve tal cual para «vista exclusiva del administrador».
- `backend/shared/tenancy.py:13` — `company_id_from(request)` obtiene la empresa del usuario autenticado; los módulos de negocio no importan `accounts` (`docs/architecture/ddd.md:842`).
- `backend/config/settings/base.py:20-25` y `backend/config/urls.py:11-19` — un app y un prefijo `/api/...` por módulo (`products`, `customers`, `orders`, `expenses`, `expense-categories`, `reports`).
- `docs/architecture/ddd.md:819` — dependencias permitidas hoy: `sales → {catalog, customers}`, `reporting → {sales, expenses, customers}`; las tablas raíz usan `company_id` UUID indexado sin FK entre módulos (`ddd.md:844`). Migraciones `0002_company_id.py` de cada módulo siguen ese patrón.
- `frontend/panel_admin/src/assets/data/routes.json` — el menú lateral es estático (6 ítems: Dashboard, Catálogo, Cliente, Pedidos, Gastos, Reportes); `layout/sidebar/sidebar.service.ts:17` lo carga por HTTP y `sidebar.component.ts:109` lo asigna sin filtrar. `layout/sidebar/sidebar-menu.spec.ts` fija su contenido.
- `frontend/panel_admin/src/app/app.routes.ts:11-50` — rutas de negocio con `AuthGuard` (`core/guard/auth.guard.ts`), sin noción de módulo ni de rol.
- `frontend/panel_admin/src/app/core/models/user.ts` / `core/service/auth.service.ts:97-120` — el usuario guardado trae `role` y `company {id,name}`; no hay datos de módulos.
- `frontend/panel_admin/src/app/features/expenses/components/category-dialog/` — diálogo modal con `NgbActiveModal`, patrón a seguir para la confirmación.
- `docs/design/design-system.md:5-6` — plantillas Lista/Detalle; sección 6 documenta el menú actual (hay que actualizarla).
- `docs/producto/modulos-implementados.md` — Compras e Inventario no existen en el producto.

### Hipótesis / supuestos no confirmados
- «Deshabilitar» en esta historia solo impide dejar dependientes huérfanos (no se puede deshabilitar un módulo si otro habilitado lo requiere); no valida datos existentes ni bloquea la API: eso es PB-MOD-004 (confirmado por el usuario el alcance, la regla de dependientes es decisión de diseño propia).
- Un usuario sin empresa no llega a esta API (403 por `CompanyAdminPermission`).
- Si Reportes se deshabilita, el Dashboard (`/dashboard/main`) pertenece a Reportes y se oculta; el destino de redirección tras login pasa a ser el primer ítem visible.

### Módulos y dependencias relacionadas
Accounts (identidad, `Company`), todos los módulos de negocio (solo como claves del catálogo de módulos; ninguno se importa), frontend `layout/sidebar`, `app.routes.ts`, `core/`.

### Implementaciones similares existentes
- Backend: vista/casos de uso de `catalog` (`api/views.py`, `application/`, `infrastructure/django/repositories.py` con `company_id` en el constructor).
- Frontend: `features/expenses` (lista de categorías + `category-dialog`, servicio API, modelos).

### Comportamiento actual
Todo usuario admin ve y usa todos los módulos; el menú es idéntico para todas las empresas.

### Restricciones
`CLAUDE.md`: aislamiento por `company_id` desde el usuario autenticado, módulos de negocio no importan `accounts`, no editar migraciones aplicadas, sin dependencias nuevas sin avisar, textos en español, DDD pragmático.

### Riesgos identificados
- Ocultar el menú no protege la API (aceptado hasta PB-MOD-004; el DDR y el ADR lo dejan explícito).
- Condición de carrera al sembrar los valores por defecto de una empresa (mitigada con unicidad y `ignore_conflicts`).
- Deshabilitar Reportes deja sin Dashboard: la redirección post-login debe no apuntar a una ruta oculta.
- Pantalla placeholder para módulos inexistentes: riesgo de confundir al usuario; el texto debe decir «Próximamente».

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — introduce un modelo por empresa nuevo, un contrato API que consume el menú, cambia la navegación global y toca autorización de vistas; afecta a todos los módulos como catálogo.

### Diseño requerido
**SI** — pantalla nueva, diálogo de confirmación y cambio del menú lateral.

## Diseño
`docs/design/DDR-habilitar-modulos-por-empresa-pantalla-modulos.md`

## Arquitectura
`docs/adr/ADR-habilitar-modulos-por-empresa-modelo-y-contrato.md`

## Plan
`docs/plans/PLAN-2026-10-27-habilitar-modulos-por-empresa.md` (v1, COMPLETO) · Specification readiness: READY

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
