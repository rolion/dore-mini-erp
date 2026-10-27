# TASK-configuracion-por-modulo-y-empresa: Administrar configuración por módulo y empresa (PB-CFG-001)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-configuracion-por-modulo-y-empresa
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/19

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-27 | (nuevo) → INVESTIGATION | Task creado; `main` al día | delivery-start |
| 2026-10-27 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE (nuevo modelo y API por empresa, historial, dependencia Sales→Modularity) | delivery-start |
| 2026-10-27 | PLANNING → ENGINEERING | Specification READY tras respuestas del usuario (ver Plan) | delivery-start |

## Investigación

### Requerimiento
PB-CFG-001 · Administrar configuración por módulo y empresa (Configuración, P0; dependencias PB-MOD-001, PB-MOD-002). Como administrador, quiero una sección de configuración en cada módulo para definir sus reglas sin afectar a otras empresas.

- Menú y vistas: Configuración dentro de Ventas, Inventario y Compras; Configuración → Módulos administra la activación general; cada pantalla con pestañas «General» e «Historial de cambios».
- General: etiqueta, descripción del efecto, valor actual, valor predeterminado cuando corresponda, validación junto al campo; no muestra opciones futuras como disponibles.
- Historial: fecha/hora, usuario, ajuste, valor anterior y nuevo; filtro por fecha y ajuste; sin secretos.
- Acciones: Guardar cambios y Cancelar cambios; aviso al salir con cambios sin guardar; éxito o errores por campo, conservando los datos ante un error.
- Aceptación: solo el administrador de la empresa cambia sus parámetros y la API valida referencias de la misma empresa; cada ajuste con valor inicial documentado y una configuración inválida no se guarda; se registra quién, cuándo y valores anterior/nuevo; los cambios no reescriben documentos históricos. Los ajustes P2 y contables P3 se incorporan con sus historias.

**Aclaraciones del usuario (2026-10-27):**
1. Ajustes de Ventas incluidos: canal de venta predeterminado, método de pago predeterminado y descuento máximo (% del subtotal). (Se descartó «días de entrega prevista».)
2. Compras e Inventario: pantalla con pestañas y aviso «sin ajustes configurables» (el historial funciona y queda vacío).
3. El historial también registra habilitar/deshabilitar módulos (Configuración → Módulos).
4. Canal y método predeterminados son solo sugerencia de la UI; el descuento máximo lo valida la API.

### Hechos encontrados
- `backend/modules/modularity/domain/modules.py:15-31` — catálogo de módulos en código (`access`, `catalog` base; `customers`, `sales`, `expenses`, `reporting`, `purchases`, `inventory`) y `DEFAULT_ENABLED_KEYS`. No existe concepto de ajuste.
- `backend/modules/modularity/infrastructure/django/models.py:6-28` y `repositories.py:10-31` — tablas `modularity_company_settings` (marca de inicialización) y `modularity_company_module`; repositorio con `company_id` en el constructor. No hay historial ni actor.
- `backend/modules/modularity/application/use_cases.py:36-61` — `EnableModule`/`DisableModule` no reciben usuario.
- `backend/modules/modularity/api/views.py:50-68` — vistas finas con `company_id_from(request)` y el permiso por defecto.
- `backend/modules/accounts/models.py:32-41` — `User` con `company` y `role` (solo `admin`); `CompanyAdminPermission` es el permiso por defecto (`backend/config/settings/base.py:86`).
- `backend/modules/sales/domain/order.py:285-292` — `apply_discount`: único tope vigente (descuento ≤ subtotal y total ≥ pagado); `order.py:111-126` canal obligatorio; `domain/enums.py:26-40` `SalesChannel` y `PaymentMethod`.
- `backend/modules/sales/application/ports.py` y `commands.py:129-131` — puertos `ProductCatalog`/`CustomerDirectory`/`Clock`; adaptadores en `sales/infrastructure/adapters.py` consumen fachadas `services.py`.
- `backend/modules/sales/tests/test_boundaries.py:9-20,56-72` — `NON_BUSINESS = {'accounts','modularity'}` y mapa de dependencias permitidas; hoy ningún módulo de negocio puede importar `modularity`.
- `docs/architecture/ddd.md:817-819,844` — convención de fachadas `services.py` de solo lectura con DTO inmutables; nota de `modularity`.
- `frontend/panel_admin/src/app/app.routes.ts:62-93` — rutas con `moduleGuard`; `purchases`/`inventory` apuntan al placeholder `features/settings/pages/coming-soon`; `settings/modules` sin guard de módulo.
- `frontend/panel_admin/src/assets/data/routes.json:111-145` — ítems `purchases`, `inventory` (enlaces simples) y «Configuración › Módulos».
- `frontend/panel_admin/src/app/features/settings/` — `ModuleListComponent`, `ModuleConfirmDialogComponent`, `ComingSoonComponent`; `core/service/modules.service.ts` y `core/guard/module.guard.ts`.
- `docs/design/design-system.md:105-137` — plantillas Lista/Formulario/Detalle y menú; `docs/design/DDR-habilitar-modulos-por-empresa-pantalla-modulos.md` — tabla Bootstrap simple, diálogo, placeholder.

### Hipótesis / supuestos no confirmados
- PB-MOD-002 no figura en el repositorio; se asume cubierta por `TASK-habilitar-modulos-por-empresa` (menú y rutas por módulo habilitado). No bloquea.
- Todos los usuarios son `admin` hoy, por lo que el frontend puede leer los predeterminados de Ventas con la API de ajustes (solo admin) sin otro permiso.
- Los valores iniciales fijados (vacío, vacío, 100) preservan el comportamiento actual de Ventas.

### Módulos y dependencias relacionadas
`modularity` (dueño), `sales` (consume su configuración por fachada), `accounts` (solo identidad del usuario vía `request.user` en la capa API), frontend `features/settings`, `features/sales`, `layout/sidebar`, `app.routes.ts`.

### Implementaciones similares existentes
- Backend: `modularity` completo (dominio puro + casos de uso + repositorio por empresa + vistas finas); fachadas `catalog/services.py` y `customers/services.py` con puertos/adaptadores en Sales.
- Frontend: `features/products/pages/product-form` (formulario), `features/settings/pages/module-list` (tabla simple y estados), `features/expenses/.../category-dialog`.

### Comportamiento actual
Las reglas de Ventas son fijas y no hay historial de cambios; el admin solo puede habilitar o deshabilitar módulos, sin registro de quién ni cuándo.

### Restricciones
`CLAUDE.md`: aislamiento por `company_id` desde el usuario autenticado, módulos de negocio no importan `accounts`, dinero/porcentajes en `Decimal`, no editar migraciones aplicadas, sin dependencias nuevas sin avisar, textos en español, DDD pragmático (catálogo en código, sin abstracciones innecesarias).

### Riesgos identificados
- Nuevo acoplamiento `sales → modularity.services` (acotado con test de frontera).
- Concurrencia al guardar el mismo ajuste (valor anterior correcto en cada registro).
- Regla de descuento máximo solo al aplicar un descuento: no reescribe históricos (INV-06).
- Menú oculto no protege la API de módulos deshabilitados (PB-MOD-004).
- Suite frontend con fallos preexistentes (71 specs demo y `app.component.spec.ts`): comparar contra la línea base.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — nuevo modelo por empresa e historial, contrato API nuevo, autorización (solo admin, empresa), una dependencia nueva entre módulos y cambio de la navegación global.

### Diseño requerido
**SI** — pantallas de configuración con pestañas, historial con filtros, submenús y aviso de salida.

## Diseño
`docs/design/DDR-configuracion-por-modulo-y-empresa-pantallas-configuracion.md`

## Arquitectura
`docs/adr/ADR-configuracion-por-modulo-y-empresa-modelo-y-contrato.md`

## Plan
`docs/plans/PLAN-2026-10-27-configuracion-por-modulo-y-empresa.md` (v1, COMPLETO) · Specification readiness: READY

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
