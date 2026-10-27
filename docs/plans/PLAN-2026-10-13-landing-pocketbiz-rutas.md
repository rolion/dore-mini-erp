# PLAN-2026-10-13-landing-pocketbiz-rutas (v2)

**Task:** TASK-landing-pocketbiz-rutas
**Modo:** COMPLETO
**DDRs relacionados:** [DDR-landing-pocketbiz-rutas-landing-y-entradas](../design/DDR-landing-pocketbiz-rutas-landing-y-entradas.md)
**ADRs relacionados:** [ADR-landing-pocketbiz-rutas-esquema-rutas-montaje](../adr/ADR-landing-pocketbiz-rutas-esquema-rutas-montaje.md), [ADR-landing-pocketbiz-rutas-compatibilidad-urls-antiguas](../adr/ADR-landing-pocketbiz-rutas-compatibilidad-urls-antiguas.md), [ADR-landing-pocketbiz-rutas-url-sin-hash](../adr/ADR-landing-pocketbiz-rutas-url-sin-hash.md)
**Specification readiness:** READY

> **v2 (2026-10-13):** incorpora el ADR `url-sin-hash` tras `ARCHITECTURE_REVIEW_REQUIRED` (la app usa `HashLocationStrategy`). Cambios de Specification **aprobados explícitamente por el usuario** en el chat de esta fecha: URLs reales sin hash, AC-18, AC-19, EDGE-07/08 y requisito de despliegue. Ver `## Changelog`.

**Por qué COMPLETO:** eje 3 (decisión arquitectónica con 2 ADR, cambio de rutas de toda la aplicación y DDR con impacto visual relevante). No hay eje 1 ni 2 (sin reglas de dominio, sin bounded contexts de backend).

## Objective
Mostrar una landing pública en `/` y mover el producto bajo `/pocketbiz` (`/pocketbiz/login`, `/pocketbiz/signup`, `/pocketbiz/**`) dentro de la SPA actual, sin cambiar backend, contratos ni sesión, y sin romper URLs antiguas.

## Context
Ver TASK-landing-pocketbiz-rutas (`## Investigación`). Base del plan: `origin/main` en `1071dc7` (incluye PR #12, que tocó `layout/header` y `layout/sidebar`). Verificado en esa base: las referencias de la investigación siguen vigentes (`app.routes.ts:13,131-137`, `auth.guard.ts:17`, `error.interceptor.ts:19`, `header.component.ts:178` —antes `:180`—, `signin.component.ts:10`, `signup.component.ts:15`). Conteo actual: **103** archivos no-spec y **20** specs con rutas absolutas antiguas; de los no-spec, 35 son de negocio/núcleo y **68** son páginas demo de la plantilla.

---

# Specification

## Domain context
No aplica dominio de backend (cambio de enrutamiento y una pantalla estática en el frontend). Contexto de UI: feature nueva `landing`; entradas `authentication`; núcleo `core`.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Landing | Página pública en `/` | ux-brief, DDR |
| Aplicación / panel | Todo lo que vive bajo `/pocketbiz/**` | Decisión Q7 |
| Entradas | `/pocketbiz/login`, `/pocketbiz/signup` (y forgot/reset) | ADR esquema |
| Redirección de compatibilidad | Ruta antigua → `/pocketbiz/…` | ADR compatibilidad |
| Ganancia estimada | Ventas − gastos registrados, nunca "ganancia" a secas | ddd.md, spec landing |

Inconsistencia a respetar: el componente se llama `SigninComponent` pero la URL será `login`; no se renombra el componente.

## Current behavior
- `/` → (con `AuthGuard`) → `/authentication/signin` (`app.routes.ts:13`); login/registro en `/authentication/*`; panel en `/dashboard`, `/catalog`, `/customers`, `/sales`, `/expenses`, `/reports`.
- Tras login/registro → `/dashboard/main` (`signin.component.ts:10`, `signup.component.ts:15`); 401 → `/authentication/signin` (`error.interceptor.ts:19`).

**Hecho añadido en v2:** la aplicación usa `HashLocationStrategy` (`frontend/panel_admin/src/app/app.config.ts:6,23`); las URLs actuales de producción de cada pantalla son `/#/<ruta>` (por ejemplo `/#/authentication/signin`). La investigación original omitió este provider.

## Expected behavior
- Las URLs reales **no llevan hash**: `/`, `/pocketbiz/login`, `/pocketbiz/signup`, `/pocketbiz/dashboard/main` (ADR `url-sin-hash`).
- Una URL antigua con hash (`/#/authentication/signin`, `/#/dashboard/main`) llega a su equivalente limpio bajo `/pocketbiz` (por el arranque de compatibilidad y las redirecciones).
- `/` muestra la landing a cualquier visitante, con o sin sesión; no redirige.
- Login y registro responden en `/pocketbiz/login` y `/pocketbiz/signup`; el panel, bajo `/pocketbiz/**` con los mismos paths relativos (`/pocketbiz/dashboard/main`, `/pocketbiz/sales/orders`, …).
- `/pocketbiz` sin subruta lleva al dashboard (con sesión) o al login (sin sesión).
- Las URLs antiguas listadas en el ADR de compatibilidad redirigen a su equivalente bajo `/pocketbiz`.
- La landing implementa el contenido de `docs/design/specs/landing-pagina-principal.md` y el DDR, con la sección "Planes" solo informativa.

## Acceptance criteria
- **AC-01:** `GET /` renderiza la landing sin sesión y con sesión; en ambos casos permanece en `/` (sin redirección).
- **AC-02:** En la landing, "Empezar gratis" (cabecera, hero, plan Gratis, cierre) navega a `/pocketbiz/signup`; "Iniciar sesión" a `/pocketbiz/login`; con sesión activa el CTA principal dice "Ir a mi panel" y navega a `/pocketbiz/dashboard/main`.
- **AC-03:** `/pocketbiz/login`, `/pocketbiz/signup`, `/pocketbiz/forgot`, `/pocketbiz/reset`, `/pocketbiz/page404` y `/pocketbiz/page500` son accesibles sin sesión.
- **AC-04:** Cualquier ruta privada bajo `/pocketbiz/**` sin sesión termina en `/pocketbiz/login`; con sesión renderiza la pantalla.
- **AC-05:** `/pocketbiz` redirige a `/pocketbiz/dashboard/main` con sesión y a `/pocketbiz/login` sin sesión.
- **AC-06:** Login y registro exitosos navegan a `/pocketbiz/dashboard/main`; un 401 fuera del login limpia la sesión y navega a `/pocketbiz/login`; el logout fallido va a `/pocketbiz/login`; "Back to Home" de 404/500 va a `/pocketbiz`.
- **AC-07:** Las 9 rutas de `assets/data/routes.json` y el enlace del logo del sidebar usan el prefijo `/pocketbiz`; el resaltado del ítem activo sigue funcionando.
- **AC-08:** Redirecciones de compatibilidad: `/authentication/signin`→`/pocketbiz/login`, `/authentication/signup`→`/pocketbiz/signup`, `/authentication/{forgot,reset,page404,page500}`→mismo bajo `/pocketbiz`, y `/{dashboard,catalog,customers,sales,expenses,reports}/**`→`/pocketbiz/<misma ruta>`, conservando subruta y query. Ningún destino es origen de otra (sin ciclos). Una ruta desconocida (p. ej. `/ui/tabs`) llega a `Page404`.
- **AC-09:** No quedan literales de rutas antiguas (`/authentication/…`, `/dashboard/…`, `/catalog/…`, `/customers`, `/sales/…`, `/expenses…`, `/reports…`) en `src/app` ni `routes.json`, salvo la tabla de redirecciones y sus tests.
- **AC-10:** El logo de login y registro enlaza a `/`.
- **AC-11:** Contenido de la landing: un único `h1` "Tu negocio en el bolsillo"; subtítulo y nota de límites ("1 producto, 1 cliente, 2 ventas y 2 gastos por día"); secciones Qué puedes controlar, Entrega y pago por separado, Tu resumen, Cómo empezar, Planes, Tus datos, Preguntas frecuentes y cierre; "Ganancia estimada" siempre con su nota "Ventas − gastos registrados. Es una estimación, no la utilidad contable."; capturas rotuladas como datos de ejemplo.
- **AC-12:** Planes: Gratis (Bs 0; 1 producto, 1 cliente, 2 ventas y 2 gastos por día; dashboard y reportes; texto del límite; botón "Empezar gratis") y Pro (Bs 350 al año / Bs 30 al mes; sin restricciones; **sin botón de compra**, con "Pago disponible próximamente"). El selector Mensual/Anual cambia el precio mostrado; por defecto Anual.
- **AC-13:** FAQ con las 6 preguntas y respuestas de la spec, operable con teclado; primer ítem abierto.
- **AC-14:** La landing no contiene "sin tarjeta", "prueba gratis", "©", "Privacidad", "Términos", "Contacto", testimonios ni cifras de clientes.
- **AC-15:** El hero muestra `dashboard-movil-403-positivo.png` dentro de un marco CSS con `alt` descriptivo; el archivo existe en `src/assets/images/`.
- **AC-16:** Sin desborde horizontal a 390 px; el menú de la cabecera se colapsa; el CTA de la cabecera es visible sin abrir el menú. Foco visible y objetivos táctiles ≥ 44 px.
- **AC-17:** `CLAUDE.md` y los documentos de diseño citan las rutas nuevas; `npm run lint` y `npm run build` pasan.
- **AC-18 (v2):** La aplicación usa `PathLocationStrategy`: no hay provider de `HashLocationStrategy`; las URLs de navegador de login, registro y panel no contienen `#`. Al abrir `/#/<ruta>` la aplicación navega a `<ruta>` reemplazando la entrada del historial, y las redirecciones de AC-08 resuelven las rutas antiguas (`/#/authentication/signin` → `/pocketbiz/login`; `/#/dashboard/main` → `/pocketbiz/dashboard/main`, o `/pocketbiz/login` sin sesión).
- **AC-19 (v2):** `CLAUDE.md` documenta, como requisito de despliegue, que el servidor debe devolver `index.html` para cualquier ruta que no sea `/api/*`, `/admin/*` ni un archivo estático.

Verificación sobre URL real: AC-03, AC-04, AC-05 y AC-08 se comprueban en el navegador con URLs sin hash (carga directa y recarga), no solo en el router de pruebas.

## Edge cases
- **EDGE-01:** Recarga profunda de `/pocketbiz/sales/orders/<id>` sin sesión → login; con sesión → la pantalla.
- **EDGE-02:** Redirección conserva query (`/sales/orders?status=NEW` → `/pocketbiz/sales/orders?status=NEW`).
- **EDGE-03:** `/pocketbiz/` (con barra final) se comporta como `/pocketbiz`.
- **EDGE-04:** Sesión guardada antes del cambio sigue válida (el token no depende de la ruta).
- **EDGE-05:** Visitar `/pocketbiz/login` con sesión activa no redirige (comportamiento actual).
- **EDGE-06:** Ruta inexistente bajo `/pocketbiz/**` → `Page404`.
- **EDGE-07 (v2):** `/#/` (hash vacío o solo `#/`) abre la landing en `/` sin bucle; un hash que no empieza por `#/` (p. ej. `#seccion`) no se interpreta como ruta.
- **EDGE-08 (v2):** Carga directa y recarga de `/pocketbiz/sales/orders/<id>` y de `/pocketbiz/login` (sin hash) funcionan con el fallback de SPA (`ng serve` lo provee).

## Error cases
- 401 en cualquier llamada → login (AC-06). Sin otros nuevos: la landing no llama a la API.

## Authorization / permissions
Landing pública. `/pocketbiz/**` privado sigue protegido por `AuthGuard` en el cliente y por token y `CompanyAdminPermission` en el servidor, sin cambios. El guard no es la barrera de seguridad real.

## UI behavior
Derivado del DDR (no se rediseña): cabecera fija con CTA, secciones en el orden de la spec, FAQ con `ngbAccordion`, toggle de planes con `aria-pressed`, marco de teléfono CSS, menú móvil con `NgbCollapse`; estado con sesión activa ("Ir a mi panel"); imágenes con `alt`.
- **UI-01:** Estado anónimo y estado con sesión de la cabecera/CTA.
- **UI-02:** Planes: Pro sin botón de compra.
- **UI-03:** Menú móvil abierto/cerrado.

## Non-functional requirements
- Accesibilidad: un `h1`, jerarquía `h2`, `nav` con `aria-label`, foco visible, `prefers-reduced-motion` en scroll por anclas; contraste según `design-system.md` (texto secundario sobre `#F6F6F6` con `#5F6870`).
- Rendimiento: landing con carga diferida (`loadComponent`); imagen del hero con dimensiones reservadas y optimizada.
- Compatibilidad: sin cambio en `base href`, API, proxy ni almacenamiento de sesión.

## Out of scope
- Límites de plan, cobro, contratación (Q13/Q21 ignoradas); páginas legales (Q4); SSR/SEO; regenerar referencias de Stitch; versión dark; rediseño de login/registro; limpieza de páginas demo de la plantilla; backend.

## Open questions (no bloqueantes)
- **F-01:** color/tamaño del texto del CTA (`#1677FF` con texto blanco = 4,10:1). Por defecto: botón primario actual de la plantilla; si el usuario decide `#0958D9`, es un cambio de token aparte.
- **F-05/F-06:** el logo real y la captura real reemplazan la recreación de Stitch (ya previsto).
- Servidor de producción con fallback de SPA (fuera del repo).

---

# Test Specification

## Unit tests (Karma + Jasmine, patrón existente)
- `core/routing` (constantes) — sin lógica; cubierto por los demás.
- `app.routes.spec.ts` (nuevo): estructura de rutas y tabla de redirecciones (AC-03, AC-05, AC-08, EDGE-02/03/06) usando el `Router` con rutas reales y `redirectTo` evaluado; ausencia de ciclos.
- `auth.guard.spec.ts`, `interceptors.spec.ts`: destino `/pocketbiz/login` (AC-04, AC-06).
- `signin.component.spec.ts`, `signup.component.spec.ts`: destino post-acción, enlaces y logo a `/` (AC-06, AC-10).
- `header.component.spec.ts`, `sidebar.component.spec.ts`, `sidebar-menu.spec.ts`: logout, logo y rutas del menú (AC-06, AC-07).
- Specs de features (`products`, `customers`, `sales`, `expenses`, `reporting`): sustituir literales por las rutas nuevas sin cambiar lo que verifican.
- `landing.component.spec.ts` (nuevo): AC-01, AC-02, AC-11, AC-12, AC-13, AC-14, AC-15 (texto, enlaces, ausencia de botón de compra, toggle, FAQ, `h1` único, `alt`).
- `legacy-hash-redirect.spec.ts` (nuevo, v2): AC-18 y EDGE-07 — con `#/authentication/signin` navega a `/authentication/signin` con `replaceUrl`; con `#/dashboard/main?x=1` conserva la query; con `#/`, hash vacío o `#seccion` no navega.
- `app.config.spec.ts` o verificación equivalente (v2): AC-18 — la configuración no provee `HashLocationStrategy` (el `LocationStrategy` resuelto es `PathLocationStrategy`).

## Integration tests
- No hay API nueva. Verificación de integración manual en navegador (ver E2E).

## E2E
**¿Corresponde E2E?** NO — el repo no tiene Playwright ni E2E; el cambio es de enrutamiento del cliente y una pantalla estática, cubierto por specs de router/componentes. Compensación: **humo manual** obligatorio antes de fusionar con `npm start` + backend: recorrido `/` → registro → dashboard → recarga profunda (URL sin hash) → logout → `/authentication/signin` y `/#/authentication/signin` (redirección a `/pocketbiz/login`) → 404; en 1440 y 390 px. En v2 el humo es sobre **URLs reales sin `#`**.

## Regression tests
- Suite completa de Angular (con las fallas preexistentes de la plantilla documentadas en tasks anteriores: `app.component.spec.ts` no compila en `main`, 71 "should create" de plantilla fallan); no deben aumentar.
- Login/registro/logout/401 y resaltado del menú.

## Acceptance criteria mapping
| AC | Verificación |
|---|---|
| AC-01, AC-02, AC-11–AC-15 | `landing.component.spec.ts` + humo manual |
| AC-03, AC-05, AC-08, EDGE-02/03/06 | `app.routes.spec.ts` |
| AC-04, AC-06 | `auth.guard.spec.ts`, `interceptors.spec.ts`, `signin`/`signup`/`header` specs |
| AC-07 | `sidebar-menu.spec.ts`, `sidebar.component.spec.ts` |
| AC-09 | `grep` (paso de verificación) |
| AC-10 | `signin`/`signup` specs |
| AC-16 | Humo manual en 1440 y 390 px (herramienta de navegador) |
| AC-17 | `npm run lint`, `npm run build`, revisión de diff de docs |
| AC-18, EDGE-07 | `legacy-hash-redirect.spec.ts`, verificación de la configuración, humo manual con URLs sin `#` |
| AC-19, EDGE-08 | Revisión de `CLAUDE.md`; humo manual de carga directa y recarga profunda |

---

# Implementation Plan

## Architecture considerations
Cumple ADR esquema (una SPA, `<base href="/">`, prefijo en el router, constantes y reemplazo mecánico) y ADR compatibilidad (redirecciones acotadas y temporales). Respeta `CLAUDE.md`: feature en `src/app/features/landing/` con `pages`, `components`, `models`; lógica no visual fuera de plantillas; tipos explícitos sin `any`; sin suscripciones colgadas.

## Proposed solution
1. **Constantes de ruta** en `core/routing/app-paths.ts`: `APP_BASE='/pocketbiz'`, `LOGIN`, `SIGNUP`, `DASHBOARD`.
2. **Router** (`app.routes.ts`): `''` landing (lazy, pública); `pocketbiz` con (a) grupo público (`AuthLayout` + `AUTH_ROUTE` sin redirect `''`, `signin`→`login`) y (b) grupo privado (`MainLayout` + `AuthGuard`, `''`→`dashboard/main` + features con los mismos paths); redirecciones de compatibilidad antes de `**`; `**` → `Page404`.
3. **Landing** en `features/landing/`: página + componentes pequeños (marco de teléfono, tarjeta de plan, paso) y un archivo tipado de contenido; SCSS propio con tokens.

## Files/components affected
- **Frontend (nuevo):** `core/routing/app-paths.ts`; `features/landing/{pages/landing,components/*,models,landing.content.ts,index.ts}` (+ specs); `src/assets/images/landing/dashboard-movil-403-positivo.png`.
- **Frontend (modificado):** `app.routes.ts`; `authentication/auth.routes.ts`; `core/guard/auth.guard.ts`; `core/interceptor/error.interceptor.ts`; `layout/header/header.component.ts`; `authentication/signin|signup` (ts+html); `authentication/page404|page500` (html); `layout/sidebar/sidebar.component.html`; `assets/data/routes.json`; reemplazo mecánico en los **103** archivos no-spec con rutas absolutas (35 de negocio/núcleo y 68 demos); **20** specs.
- **Backend / DB / API:** ninguno.
- **Documentación:** `CLAUDE.md` (comandos y registro), `docs/design/*` que citan rutas antiguas, `TASK`.

## Implementation steps
Dos commits de código con el PR único (ADR esquema, punto 6), y verificación entre fases.

**Fase 1 — Rutas (commit "rutas bajo /pocketbiz")**
1. Crear `core/routing/app-paths.ts` (AC-06).
2. Reestructurar `app.routes.ts` y `auth.routes.ts` según la solución; quitar el `redirectTo` a `/authentication/signin` (AC-03, AC-04, AC-05).
3. Actualizar guard, interceptor, header, `DEFAULT_ROUTE_AFTER_LOGIN/SIGNUP`, enlaces de signin/signup/404/500 con las constantes o `/pocketbiz/…` (AC-06, AC-10 parcial).
4. Actualizar `routes.json` y el logo del sidebar (AC-07).
5. Reemplazo mecánico en plantillas y TS (patrones `routerLink="/…"`, `[routerLink]="['/…']"`, `navigate(['/…'])`, `navigateByUrl('/…')`) limitado a los prefijos conocidos; revisión del diff archivo por archivo (AC-09).
6. Añadir las redirecciones de compatibilidad (AC-08).
7. Actualizar los 20 specs y crear `app.routes.spec.ts`.
8. `grep` de verificación, `npm run lint`, specs afectados (AC-09, AC-17).
9. Documentación: `CLAUDE.md` y docs de diseño (AC-17).

**Fase 2 — Landing (commit "landing en /")**
10. Copiar la captura a `assets/images/landing/` y optimizar (AC-15).
11. Crear `features/landing` con contenido tipado, secciones, FAQ (`ngbAccordion`), selector de planes (`btn-group`, `aria-pressed`), menú móvil (`NgbCollapse`) y marco CSS (AC-11–AC-16).
12. CTA sensible a sesión con `AuthService.isAuthenticated` (AC-01, AC-02).
13. Enlazar el logo de login/registro a `/` (AC-10).
14. Specs del componente (AC-01, AC-02, AC-11–AC-15).

**Fase 2b — URLs limpias (v2, commit "URLs sin hash")**
15. Quitar el provider `{ provide: LocationStrategy, useClass: HashLocationStrategy }` y su import de `app.config.ts:6,23` (AC-18). `<base href="/">` no cambia.
16. Añadir el arranque de compatibilidad (por ejemplo `provideAppInitializer` o un servicio inicializado al arrancar) que, si `location.hash` empieza por `#/`, ejecuta `router.navigateByUrl(hash.slice(1), { replaceUrl: true })`; ignora otros hashes (AC-18, EDGE-07). Documentar en comentario su retiro junto con las redirecciones.
17. Specs: `legacy-hash-redirect.spec.ts` y comprobación de la estrategia (AC-18).
18. `CLAUDE.md`: requisito de despliegue (fallback de SPA para rutas que no sean `/api/*`, `/admin/*` ni archivos estáticos) y nota del cambio de URLs (AC-19).

**Fase 3 — Verificación**
19. `npm run lint`, `npm run build`, `ng test` acotado a los specs afectados y a la suite completa (comparar con la línea base de `main`).
20. Humo manual en 1440 y 390 px (AC-16) sobre **URLs sin hash**: `/`, `/pocketbiz/login`, carga directa y recarga de una ruta profunda, y `/#/authentication/signin` (AC-18, EDGE-08); registro en el TASK.
21. `/delivery-visual-review` de la landing contra las referencias.

**Estado de avance (v2):** los pasos 1–14 ya están implementados en `71ca1a5` y `f3d34b7` y verificados en modo hash (463 OK / 71 FAILED de plantilla, igual que la línea base). Quedan los pasos 15–21.

## Database / migrations
No aplica.

## Risks
- **Reemplazo mecánico masivo (103 archivos):** falsos positivos o enlaces omitidos. Mitigación: patrones acotados, revisión del diff, `grep` de AC-09 y redirecciones de compatibilidad como red de seguridad.
- **Enrutamiento con dos rutas hermanas bajo `pocketbiz`:** si el grupo privado captura `login`, el guard redirigiría en bucle. Mitigación: grupo público primero y spec de rutas (AC-03/AC-04).
- **Resaltado del sidebar:** `linkActiveOptions` compara prefijos de `routes.json`; al prefijarse todos de forma consistente debe mantenerse. Verificar en `sidebar-menu.spec.ts` y en el navegador.
- **Specs preexistentes que fallan en `main`:** no atribuir a este cambio; comparar contra la línea base.
- **Sin servidor de despliegue en el repo:** el fallback de SPA para `/pocketbiz/**` queda como requisito documentado.
- **Referencias de Stitch con desviaciones abiertas (F-01…F-16):** la spec prevalece.
- **Fallback de SPA (v2):** con URLs limpias, un servidor sin fallback devolvería 404 en recargas profundas (EDGE-08). Mitigación: requisito documentado (AC-19) y orden de despliegue (servidor primero); rollback de una línea (reponer el provider de hash).
- **URLs con hash ya compartidas (v2):** quedarían apuntando a la landing sin el arranque de compatibilidad. Mitigación: AC-18, con spec.
- **Bucle de navegación del arranque (v2):** un hash que se reescribe a sí mismo. Mitigación: `replaceUrl`, solo hashes `#/…` y spec de EDGE-07.

## New dependencies
Ninguna (usa `@ng-bootstrap/ng-bootstrap` 20.0.0, Bootstrap 5.3 y Font Awesome ya instalados).

## Changelog
- **v2** (2026-10-13): [Implementation Plan] Se agrega la Fase 2b y se actualizan Test Specification, riesgos y estado de avance tras `ARCHITECTURE_REVIEW_REQUIRED` de `delivery-engineer` (la app usa `HashLocationStrategy`); ADR `url-sin-hash`.
- **v2** (2026-10-13): [Specification] Se agregan AC-18 y AC-19, EDGE-07 y EDGE-08, y se fija que AC-03/AC-04/AC-05/AC-08 se verifican sobre URL real sin hash. **Aprobado explícitamente por el usuario** ("Aprobar todo") en el chat del 2026-10-13. Solicitado por `delivery-engineer`/`delivery-architect`.
