# TASK-landing-pocketbiz-rutas: Landing pública de PocketBiz en "/" y aplicación bajo "/pocketbiz"

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** `task/TASK-landing-pocketbiz-rutas`
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/13

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-13 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-10-13 | DESIGN → ARCHITECTURE | DDR de landing y pantallas de entrada propuesto; veredicto NEEDS_ARCHITECTURE | delivery-design |
| 2026-10-13 | ARCHITECTURE → PLANNING | 2 ADR: una sola SPA con prefijo `/pocketbiz` en el router (base href sin cambios) y redirecciones temporales de URLs antiguas | delivery-architect |
| 2026-10-13 | PLANNING → ENGINEERING | Plan v1 COMPLETO, Specification READY; rama creada desde `origin/main` (1071dc7); PR abierto | delivery-plan |

## Investigación

### Requerimiento
Tal como se recibió:

> Landing pública de PocketBiz en "/" y mover la aplicación bajo "/pocketbiz" (login: /pocketbiz/login, registro: /pocketbiz/signup, resto: /pocketbiz/**).

Decisiones del usuario (2026-10-13, registradas en `docs/design/ux-brief.md`):
- **Q7:** la raíz carga la landing; `/pocketbiz/login`, `/pocketbiz/signup` y `/pocketbiz/**` para todo lo demás.
- **Q13 y Q21 (planes, límites, contratación): ignorar.** La sección "Planes" es informativa; Pro sin botón de compra.
- **Q4 (términos y privacidad): no definidos.** Sin enlaces legales ni de contacto.

Documentos de entrada ya existentes (no se repiten aquí): `docs/design/ux-brief.md`, `docs/design/design-system.md`, `docs/design/specs/landing-pagina-principal.md`, `docs/design/screens.md`, `docs/design/visual-review.md`, capturas en `docs/design/exports/landing/`.

### Hechos encontrados

**Rutas actuales del frontend (Angular 21, standalone)**
- `frontend/panel_admin/src/app/app.routes.ts:8-13` — la ruta raíz `''` carga `MainLayoutComponent` con `AuthGuard`; su hija `''` redirige a `/authentication/signin` (`:13`).
- `app.routes.ts:14-128` — 15+ rutas hijas bajo la raíz: `dashboard`, `catalog/products`, `customers`, `sales/orders`, `expenses`, `reports` (las de negocio) y las de la plantilla (`advance-table`, `advanced`, `calendar`, `email`, `apps`, `widget`, `ui`, `forms`, `charts`, `icons`, `extra-pages`, `maps`, `multilevel`, `tables`, `data-tables`).
- `app.routes.ts:131-136` — `authentication` con `AuthLayoutComponent` y `AUTH_ROUTE`; `app.routes.ts:137` — `**` → `Page404Component`.
- `app/authentication/auth.routes.ts:8-38` — `''` → `signin`; rutas `signin`, `signup`, `forgot`, `reset`, `page404`, `page500`.
- `app/app.config.ts:20` — `provideRouter(APP_ROUTE)` sin `withHashLocation` ni `APP_BASE_HREF` (`grep` sin resultados).
- `src/index.html:7` — `<base href="/">`. `angular.json` no define `baseHref` ni `deployUrl`; el build es `@angular/build:application` con `outputPath.base = dist/oreva` (`angular.json:20-22`); sin SSR/prerender (grep sin resultados).
- `frontend/panel_admin/proxy.conf.json` — solo `/api` → `http://127.0.0.1:8000`; el proxy aplica a la configuración `development` del serve (`angular.json:105`).

**Referencias a rutas que cambiarían (no `spec`)**
- `/authentication/signin`: `core/guard/auth.guard.ts:17`, `core/interceptor/error.interceptor.ts:19`, `layout/header/header.component.ts:180`, `app.routes.ts:13`, `authentication/signup/signup.component.html:101`, `authentication/page404/page404.component.html:28`, `authentication/page500/page500.component.html:28`.
- `/authentication/signup`: `authentication/signin/signin.component.html:68`. `/authentication/forgot`: `signin.component.html:39`.
- `DEFAULT_ROUTE_AFTER_LOGIN = '/dashboard/main'`: `authentication/signin/signin.component.ts:10` (usado en `:58`); `DEFAULT_ROUTE_AFTER_SIGNUP = '/dashboard/main'`: `authentication/signup/signup.component.ts:15` (usado en `:135`).
- Menú lateral: `src/assets/data/routes.json` — 9 entradas con `path` absoluto (`/dashboard/main`, `/catalog/products`, `/customers`, `/sales/orders`, `/expenses`, `/expenses/categories`, `/reports`, etc.).
- Enlaces y navegaciones absolutas (`routerLink="/…"`, `navigate(['/…'])`) por área, conteo con `grep` sobre `app/` excluyendo specs: `features/expenses` 19, `features/sales` 16, `features/customers` 16, `features/products` 15, `features/reporting` 8, `layout/header` 3, `authentication/signin` 2, más ≈ 25 en páginas demo de la plantilla (`email`, `ui`, `widget`, `multilevel`).
- Pruebas: 19 archivos `*.spec.ts` mencionan rutas absolutas (`/dashboard`, `/catalog`, `/customers`, `/sales`, `/expenses`, `/reports`, `/authentication`); por ejemplo `signin.component.spec.ts:66` espera `'/dashboard/main'`.
- Documentación que cita las rutas: `CLAUDE.md:15` ("Las personas se registran desde `/authentication/signup`").

**Backend**
- `backend/config/urls.py:9-17` — solo `admin/` y `api/*`; el backend no sirve el frontend ni define rutas de SPA. La API (`environment.ts`: `apiUrl: '/api'`) y el proxy son independientes de las rutas del cliente.
- No hay archivos de despliegue versionados (sin Dockerfile, nginx, compose ni CI: `git ls-files` sin coincidencias relevantes).

**Activos y diseño disponibles**
- `src/assets/images/main-logo.png`, `simple-logo.png`, `pocketbiz.ico` (de `TASK-pocketbiz-branding-logos`).
- Layouts existentes: `layout/app-layout/main-layout` y `auth-layout`; no existe un layout público/de marketing.
- Estilos: Bootstrap 5 + SCSS de la plantilla; tokens en `assets/scss/_variable.scss` (primario `#1677ff`, `:4`).
- Tarea previa relacionada: `docs/tasks/TASK-registro-usuarios-empresa-multitenant.md` (registro con empresa en `/authentication/signup`, entrada directa al dashboard).

### Hipótesis / supuestos no confirmados
- **Base href vs. prefijo en el router:** no se confirmó cuál de las dos formas de montar la app bajo `/pocketbiz` es viable con el servidor de producción que se vaya a usar (no hay configuración de despliegue en el repo).
- **Landing dentro o fuera de la app Angular:** no se decidió si la landing es una ruta de la misma app o una página estática/otra entrada de build.
- **Redirecciones de URLs antiguas:** no se definió si `/authentication/signin`, `/dashboard/main`, etc. deben redirigir a las nuevas rutas (marcadores de usuarios actuales) o dejar de existir.
- **Destino de `/pocketbiz` sin subruta:** no definido (¿login, dashboard según sesión?).
- **Destino de `/pocketbiz/forgot`, `/pocketbiz/reset` y páginas demo de la plantilla:** se asume que quedan bajo `/pocketbiz/**`; no confirmado.
- **Persistencia de sesión:** se asume que el token en `localStorage` (`core/service/auth.service.ts`) es independiente de la ruta; no se verificó con un cambio de base href (el origen sigue igual).
- **SEO/indexación de la landing:** al ser una SPA sin SSR (`angular.json` sin configuración SSR) el contenido se renderiza en cliente; no se evaluó el impacto ni si es un requisito.
- **Sin cobertura visual de la app:** la landing no existe en la aplicación; la revisión visual realizada (`docs/design/visual-review.md`) fue solo contra referencias de Stitch.

### Módulos y dependencias relacionadas
- **Frontend (`frontend/panel_admin/`):** `app.routes.ts`, `app.config.ts`, `index.html`, `angular.json`, `proxy.conf.json`; `authentication/*`; `core/guard`, `core/interceptor`; `layout/header`, `layout/sidebar` y `assets/data/routes.json`; todas las features (`products`, `customers`, `sales`, `expenses`, `reporting`) por enlaces absolutos; páginas demo de la plantilla; 19 specs.
- **Backend:** sin cambios de código previsibles (API y admin no dependen de las rutas del cliente).
- **Infra/despliegue:** servidor que sirva `/` y `/pocketbiz/**` con fallback de SPA; no definido en el repo.
- **Documentación:** `CLAUDE.md:15`, `docs/design/*`.

### Implementaciones similares existentes
- Rutas anidadas con layout propio y `loadChildren` por feature (`app.routes.ts:14-128`) y un layout público para autenticación (`auth-layout`, `app.routes.ts:131-136`): son el patrón actual para añadir una ruta pública con su propio layout.
- Constantes de ruta tras login/registro (`DEFAULT_ROUTE_AFTER_LOGIN`, `DEFAULT_ROUTE_AFTER_SIGNUP`) ya centralizan parte de los destinos; las demás rutas absolutas están dispersas.
- No existe ningún mecanismo central de rutas (constantes o helpers) para los ~140 enlaces.

### Comportamiento actual
- `/` redirige (tras `AuthGuard`) a `/authentication/signin`; un usuario autenticado que visita `/` también es enviado a esa ruta (`app.routes.ts:13`).
- Login y registro: `/authentication/signin` y `/authentication/signup`; tras éxito se navega a `/dashboard/main`.
- Ante 401, el interceptor limpia sesión y navega a `/authentication/signin` (`error.interceptor.ts:17-19`).
- No existe landing pública ni ruta `/pocketbiz`.

### Restricciones
- `CLAUDE.md`: cambios acotados a un objetivo; **proponer un plan y esperar confirmación antes de tocar varios archivos**; una rama y un PR por task (`task/TASK-<slug>`); frontend por `src/app/features/<modulo>/`, tipos explícitos sin `any`, Reactive Forms, sin suscripciones colgadas; avisar antes de instalar dependencias.
- `frontend/panel_admin_doc/` es referencia y no se edita.
- Decisiones de producto: sin límites ni cobro (Q13/Q21 ignoradas), sin enlaces legales ni de contacto (Q4).
- Contenido de la landing: sin testimonios, cifras ni funcionalidades inventadas; "Planes" solo informativa (`docs/design/ux-brief.md` §4, §6).
- El registro público sigue abierto con throttle `5/hora` y el interruptor `REGISTRATION_ENABLED` (según `TASK-registro-usuarios-empresa-multitenant`).

### Riesgos identificados
- **Alcance transversal:** ≈ 140 enlaces absolutos y 19 specs dependen de rutas sin prefijo; un cambio de prefijo en el router toca todas las features, menú, guards, interceptor y tests.
- **Cambio de infraestructura:** montar la app bajo `/pocketbiz/` implica decisiones de build (`base href`, `serve`) y de servidor/proxy que el repo no tiene definidas; riesgo de rutas rotas al recargar páginas profundas (fallback de SPA).
- **Compatibilidad:** URLs antiguas (marcadores, correos futuros) dejarían de funcionar si no hay redirecciones.
- **Bucles de redirección:** guard e interceptor redirigen a login; con el nuevo prefijo un destino mal escrito puede producir ciclos o 404.
- **Tests existentes:** specs fijan rutas literales (p. ej. `signin.component.spec.ts:66`); fallos masivos si no se actualizan juntos.
- **Plantilla:** páginas demo (`email`, `ui`, `widget`, etc.) quedarían expuestas bajo `/pocketbiz/**` igual que hoy; no se evaluó si deben seguir accesibles.
- **Promesas de la landing no respaldadas por el producto:** límites de plan gratuito y precios descritos sin aplicación en backend (decisión aceptada por Q13/Q21).
- **Legal:** registro público sin términos ni privacidad (Q4 pendiente); el pie de la landing no puede enlazarlos.
- **SEO:** SPA sin SSR para una página pública de marketing (no verificado como requisito).
- **Documentación:** `CLAUDE.md` y los documentos de diseño citan rutas antiguas.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — Hay un cambio estructural de ruteo que afecta a toda la aplicación y un posible cambio de build/despliegue (base href, servidor y proxy), con decisiones con trade-offs claros (prefijo en el router frente a `base href`, landing dentro o fuera de la app) y riesgo de deuda técnica; coincide con los indicadores de cambio estructural, de infraestructura e impacto en múltiples módulos.

### Diseño requerido
**SI** — Se agrega una pantalla pública nueva (landing) con layout propio y varias secciones, y cambian las pantallas de entrada (login y registro) de ruta. Ya existen artefactos de diseño (`ux-brief.md`, `design-system.md`, `specs/landing-pagina-principal.md`, `screens.md`, `visual-review.md`) pero **no hay un DDR** formal para esta tarea; `delivery-design` puede formalizarlo apoyándose en ellos y en la elección de componentes de la plantilla.

## Diseño
- [DDR-landing-pocketbiz-rutas-landing-y-entradas](../design/DDR-landing-pocketbiz-rutas-landing-y-entradas.md) — Propuesto. Landing nueva en `features/landing` con cabecera y pie propios (sin `main-layout`), Bootstrap 5 + `ngbAccordion` + `btn-group` Mensual/Anual + marco de teléfono en CSS puro; Pro sin botón de compra; login y registro reutilizados sin rediseño (solo enlaces y destino post-acción; el logo enlaza a `/`); `/pocketbiz` sin subruta resuelve según sesión; 401 → `/pocketbiz/login`; 404/500 → `/pocketbiz`. Pendiente de arquitectura: base href vs. prefijo en el router, landing dentro/fuera de la app, redirecciones de URLs antiguas, fallback de servidor.
- Insumos previos (sin repetir): `docs/design/ux-brief.md`, `docs/design/design-system.md`, `docs/design/specs/landing-pagina-principal.md`, `docs/design/screens.md`, `docs/design/visual-review.md`.

## Arquitectura
- [ADR-landing-pocketbiz-rutas-esquema-rutas-montaje](../adr/ADR-landing-pocketbiz-rutas-esquema-rutas-montaje.md) — Propuesto. Una sola SPA con `<base href="/">` sin cambios; prefijo `/pocketbiz` en el router (`''` = landing pública lazy; `pocketbiz` = login/signup/forgot/reset/page404/page500 con `AuthLayout` + el panel con `MainLayout` + `AuthGuard` con los mismos paths relativos). Constantes de destino (`APP_BASE`, `LOGIN`, `SIGNUP`, `DASHBOARD`) para guard, interceptor, header y auth; reemplazo mecánico en plantillas y `routes.json`. `/pocketbiz` sin subruta → dashboard, o login por el guard. Sin cambios en backend, proxy ni almacenamiento. Rollback: revertir commits (rutas y landing en commits separados). Descartadas: `--base-href /pocketbiz/` + landing aparte, `UrlSerializer` personalizado, hash routing, dos apps.
- [ADR-landing-pocketbiz-rutas-compatibilidad-urls-antiguas](../adr/ADR-landing-pocketbiz-rutas-compatibilidad-urls-antiguas.md) — Propuesto. Redirecciones `redirectTo` (función) temporales de `/authentication/*` y de los prefijos de negocio (`dashboard`, `catalog`, `customers`, `sales`, `expenses`, `reports`) a `/pocketbiz/…`; sin redirección para demos de la plantilla; `/` no redirige.
- **Requisito de servidor (fuera del repo):** fallback de SPA para `/` y `/pocketbiz/**`; `/api` y `/admin/` a Django.
- Sin dependencias nuevas (`npm`/`pip`). Sin cambios de autenticación/autorización en el backend.
- **Para PLAN:** actualizar `CLAUDE.md:15` y documentos de diseño con las rutas nuevas; actualizar 19 specs con rutas literales; añadir spec de rutas y de redirecciones; copiar `dashboard-movil-403-positivo.png` a `assets/images/`; mantener `grep` de rutas antiguas como criterio de aceptación.

## Plan
- [PLAN-2026-10-13-landing-pocketbiz-rutas](../plans/PLAN-2026-10-13-landing-pocketbiz-rutas.md) — **v1**, Modo COMPLETO, Specification readiness: **READY**. 17 AC (AC-01..AC-17), 6 casos borde; E2E: NO (humo manual obligatorio en 1440 y 390 px). Base verificada en `origin/main` `1071dc7`: **103** archivos no-spec y **20** specs con rutas antiguas (68 de los no-spec son demos de la plantilla). Dos commits de código: rutas y landing. Sin dependencias nuevas.
- Preguntas abiertas no bloqueantes: F-01 (color/tamaño del texto del CTA), logo y captura reales sustituyen las recreaciones de Stitch, fallback de SPA en el servidor (fuera del repo).

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
