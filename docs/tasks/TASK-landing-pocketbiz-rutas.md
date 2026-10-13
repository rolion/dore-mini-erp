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
| 2026-10-13 | ENGINEERING → ARCHITECTURE | `ARCHITECTURE_REVIEW_REQUIRED`: la app usa `HashLocationStrategy` (`app.config.ts:23`); las URLs reales son `/#/pocketbiz/…`, no `/pocketbiz/…`; pasar a URLs limpias exige fallback de SPA en el servidor. Rutas y landing implementadas y verificadas | delivery-engineer |
| 2026-10-13 | ARCHITECTURE → PLANNING | ADR `url-sin-hash`: pasar a `PathLocationStrategy` con arranque de compatibilidad para `/#/…`; requisito de fallback de SPA en servidor. Requiere `PLAN_UPDATE_REQUIRED` (v2) | delivery-architect |
| 2026-10-13 | PLANNING → ENGINEERING | Plan v2 COMPLETO (Fase 2b URLs sin hash; AC-18/AC-19 aprobados por el usuario); Specification READY; mismo PR | delivery-plan |

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
- [ADR-landing-pocketbiz-rutas-url-sin-hash](../adr/ADR-landing-pocketbiz-rutas-url-sin-hash.md) — Propuesto (2026-10-13, por `ARCHITECTURE_REVIEW_REQUIRED`). Corrige la premisa de los ADR anteriores: la app usa `HashLocationStrategy` (`app.config.ts:23`). Decisión: pasar a `PathLocationStrategy` (quitar el provider; `<base href="/">` igual) para cumplir Q7 con URLs reales `/pocketbiz/login`; arranque de compatibilidad que convierte `/#/<ruta>` en `<ruta>` (reutiliza las redirecciones del ADR de compatibilidad); fallback de SPA en el servidor como requisito de despliegue documentado en `CLAUDE.md`; sin flag por entorno. Rollback: reponer el provider de hash (una línea). Descartadas: mantener hash, hash + reescritura en servidor, flag `useHash`, SSR/prerender.
- **Requisito de servidor (fuera del repo):** fallback de SPA para `/` y `/pocketbiz/**`; `/api` y `/admin/` a Django. Con la decisión de URLs limpias pasa de "deseable" a **obligatorio** antes del primer despliegue.
- Sin dependencias nuevas (`npm`/`pip`). Sin cambios de autenticación/autorización en el backend.
- **Para PLAN:** actualizar `CLAUDE.md:15` y documentos de diseño con las rutas nuevas; actualizar 19 specs con rutas literales; añadir spec de rutas y de redirecciones; copiar `dashboard-movil-403-positivo.png` a `assets/images/`; mantener `grep` de rutas antiguas como criterio de aceptación.

## Plan
- [PLAN-2026-10-13-landing-pocketbiz-rutas](../plans/PLAN-2026-10-13-landing-pocketbiz-rutas.md) — **v1**, Modo COMPLETO, Specification readiness: **READY**. 17 AC (AC-01..AC-17), 6 casos borde; E2E: NO (humo manual obligatorio en 1440 y 390 px). Base verificada en `origin/main` `1071dc7`: **103** archivos no-spec y **20** specs con rutas antiguas (68 de los no-spec son demos de la plantilla). Dos commits de código: rutas y landing. Sin dependencias nuevas.
- **v2 (2026-10-13)** — mismo documento, mismo PR: [Implementation Plan] Fase 2b (URLs sin hash, arranque de compatibilidad, `CLAUDE.md`), tests y riesgos; [Specification] **AC-18, AC-19, EDGE-07, EDGE-08**, aprobados explícitamente por el usuario ("Aprobar todo"). Specification readiness: **READY**. Pasos 1–14 ya implementados (`71ca1a5`, `f3d34b7`); quedan los pasos 15–21.
- Preguntas abiertas no bloqueantes: F-01 (color/tamaño del texto del CTA), logo y captura reales sustituyen las recreaciones de Stitch, fallback de SPA en el servidor (fuera del repo; requisito documentado en AC-19).

## Implementación
Implementado según PLAN v1 (COMPLETO) en dos commits (`71ca1a5` rutas, `f3d34b7` landing). **Detenido por `ARCHITECTURE_REVIEW_REQUIRED`** (ver abajo) antes de dar la implementación por completa.

### Qué se hizo
| Parte | Cubre |
|---|---|
| `core/routing/app-paths.ts` (`APP_BASE`, `APP_PATHS`) y uso en guard, interceptor, header, signin y signup | AC-06 |
| `app.routes.ts`: `''` landing (lazy, pública); `pocketbiz` con grupo privado (`MainLayout` + `AuthGuard`, `''`→`dashboard/main`) y grupo público (`AUTH_ROUTE`: `login`, `signup`, `forgot`, `reset`, `page404`, `page500`); `**` → `Page404` | AC-01, AC-03, AC-04, AC-05 |
| `core/routing/legacy-redirects.ts`: redirecciones temporales con query y fragmento (UrlTree) | AC-08 |
| Reemplazo mecánico de rutas absolutas en **124 archivos** (103 no-spec + 20 specs + `routes.json`), 256 sustituciones; `grep` sin literales antiguos fuera de las redirecciones y su spec | AC-07, AC-09 |
| 404/500 "Back to Home" → `/pocketbiz`; logo de login/registro → `/` | AC-06, AC-10 |
| `features/landing` (página, contenido tipado, SCSS) + captura en `assets/images/landing/` | AC-11..AC-16 |
| `CLAUDE.md:15` con las rutas nuevas | AC-17 |
| Specs: `core/routing/app-routes.spec.ts` (estructura y 13 redirecciones + query + 404 + sin ciclos), `landing.component.spec.ts` (anónimo y con sesión), 4 specs de features con tablas de rutas de prueba prefijadas | AC-01..AC-17 |

### Verificación propia (no es el Quality Gate)
- `ng lint`: OK. `ng build --configuration development`: OK.
- `ng test` (excluyendo `app.component.spec.ts`, que no compila en `main`): **463 OK / 71 FAILED**; los 71 son todos `should create` de specs de la plantilla ya fallidos en `main` (línea base 415 OK / 71 FAILED); sin fallos nuevos.
- Humo en navegador (`ng serve`, sin sesión): `/` muestra la landing sin redirigir; `#/authentication/signin`→`#/pocketbiz/login`; `#/dashboard/main` y `#/sales/orders?status=NEW`→`#/pocketbiz/login` (por el guard); `#/pocketbiz`→`#/pocketbiz/login`; `#/ui/tabs`→404; a 375 px (388 de ancho útil) sin desborde horizontal, botón del menú 44×44 y CTA visible.
- **No verificado:** humo con sesión activa y backend (CTA "Ir a mi panel" solo en spec), 1440 px por captura, foco/teclado en navegador, contraste con herramienta; `npm audit`.

### Hallazgo que bloquea: ARCHITECTURE_REVIEW_REQUIRED
- **Hecho:** la aplicación usa `HashLocationStrategy` (`frontend/panel_admin/src/app/app.config.ts:6,23`). Las URLs reales son `http://host/#/pocketbiz/login`, no `/pocketbiz/login`. La investigación afirmó que no había `withHashLocation`/base href por un `grep` incompleto (no buscó `HashLocationStrategy`), y el ADR `esquema-rutas-montaje` dio por hecho `PathLocationStrategy`.
- **Impacto:** el requisito de usuario Q7 ("`/pocketbiz/login`, `/pocketbiz/signup`, `/pocketbiz/**`") **no se cumple en URL real** con el código actual: en navegador la URL es `/#/pocketbiz/login`. Con `HashLocationStrategy` tampoco existe una "ruta `/pocketbiz`" en el servidor: una URL `/pocketbiz/login` sin hash carga la landing.
- **Por qué es de arquitectura:** pasar a `PathLocationStrategy` quita el provider (`app.config.ts:23`) pero **exige fallback de SPA en el servidor para `/pocketbiz/**`** (hoy no lo necesita porque el servidor solo ve `/`), cambia todas las URLs ya compartidas (`/#/…`), y afecta al dev server y a cualquier despliegue; es una decisión de infraestructura que no tomé.
- **Lo ya implementado es válido bajo ambas estrategias:** los paths del router, constantes, redirecciones y landing no dependen de la estrategia; si se elige Path, el cambio es un provider y su verificación; las redirecciones deberán revisarse (en Hash, las URLs antiguas son `/#/authentication/signin`).
- **Preguntas para arquitectura/usuario:** (1) ¿mantener hash (`/#/pocketbiz/login`) o pasar a URLs limpias? (2) si se pasa a Path, ¿qué servidor/proxy servirá el fallback y cómo se despliega? (3) ¿las URLs antiguas con `#` deben redirigir igual (sí, ya lo hacen)?

### Desviaciones respecto al plan (Specification sigue satisfecha salvo lo anterior)
- **El plan hablaba de componentes pequeños** (marco de teléfono, tarjeta de plan, paso); se implementó **un solo componente** de página con contenido tipado, sin subcomponentes (YAGNI; el marco y las tarjetas son marcado y SCSS locales).
- **Orden de grupos en `pocketbiz`:** el plan describía "grupo público + grupo privado"; el privado tuvo que ir **primero** porque el público con `path: ''` coincidía con `/pocketbiz` vacío y mostraba un layout vacío (AC-05). Detectado en el humo y corregido; cubierto por un test de orden.
- **Redirección con función:** la versión por cadena perdía la query; se resolvió con `UrlTree` (`createUrlTree`) y quedó cubierto por test (EDGE-02).
- **"Entrega y pago":** se usó recreación HTML de las tarjetas de estado en vez de capturas recortadas (legibles en móvil; Q25 del spec).
- **Resumen:** las 4 pestañas de periodo son ilustrativas (no interactivas).
- **Entorno:** el `node_modules` de este checkout estaba incompleto (sin `@angular`); se apartó como `frontend/panel_admin/.node_modules.partial` (excluido en `.git/info/exclude`) y se enlazó una *junction* local a un `node_modules` completo de otro worktree (Angular 21.2.25, `ng-bootstrap` 20.0.0). Sin cambios en `package.json`.

### Deuda técnica / notas
- Pendientes de revisión visual contra Stitch (`/delivery-visual-review`): logo y captura reales ya usados; F-01 (contraste del CTA) sin decidir.
- El spec de `app.component` sigue sin compilar en `main` (preexistente).
- Las páginas demo de la plantilla siguen accesibles bajo `/pocketbiz/**`.
- El texto del login sigue mezclado inglés/español (fuera de alcance).

## Review
_Pendiente_

## Publicación
_Pendiente_
