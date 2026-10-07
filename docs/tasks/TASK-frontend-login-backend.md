# TASK-frontend-login-backend: Login del frontend validado contra el backend

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** NO
**Rama:** `task/TASK-frontend-login-backend`
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/4

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-07 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-10-07 | ARCHITECTURE → PLANNING | Decisión de autenticación registrada en ADR | delivery-architect |
| 2026-10-07 | PLANNING → ENGINEERING | Plan v1 COMPLETO, Specification READY; PR abierto | delivery-plan |

## Investigación

### Requerimiento
"En el frontend debemos crear el login. La plantilla ya tiene un formulario de login. Valida el login con el backend; si el login es exitoso deja entrar al usuario y llévalo a la página del dashboard (usa la página por defecto). Si el login es inválido muestra un mensaje de error de credenciales inválidas y no dejes pasar al usuario."

### Hechos encontrados

**Ubicación del código (importante)**
- `frontend/` **no está versionado**: `git status` en el checkout principal (`E:\dore-mini-erp`) lo lista como `?? frontend/`, y `git ls-files frontend` no devuelve nada. Este worktree (`claude/frontend-login-validation-57643b`) no contiene `frontend/`; solo existe en el checkout principal. Los paths de frontend abajo son relativos a `frontend/panel_admin/` en ese checkout.

**Frontend (plantilla Oreva)**
- `src/app/authentication/auth.routes.ts:9-17` — `/authentication` redirige a `signin`; `signin` → `SigninComponent`.
- `src/app/authentication/signin/signin.component.ts:27-31` — formulario con `UntypedFormBuilder` (no tipado), campos `username`, `password`, `remember`, con **valores por defecto precargados** `admin@email.com` / `admin@123`.
- `src/app/authentication/signin/signin.component.ts:38-72` — `onSubmit()` llama `authService.login(...)`; en éxito navega a `/dashboard/main` si hay `token`; el bloque `next` tiene `if (res)` duplicado y ramas `Invalid Login`; en error asigna `this.error = error`. Con formulario inválido muestra `'Username and Password not valid !'` (en inglés).
- `src/app/authentication/signin/signin.component.html:20-30` — input `type="email"` para `username`, labels en inglés ("Your Email", "Password", "Sign in"); `:50-52` muestra `error` en un `alert alert-danger`; `:57-70` botones de login social (Facebook/GitHub/Twitter/GitLab) sin funcionalidad; `:72-75` enlace a Sign Up; `:46` enlace "Forgot password".
- `src/app/core/service/auth.service.ts:11-20` — **autenticación simulada**: lista `users` hardcodeada con `admin@email.com`/`admin@123` y `token: 'admin-token'`. `:34-52` `login()` busca en esa lista, guarda en `LocalStorageService` bajo `currentUser`, y devuelve `of(HttpResponse)` o `throwError('Username or password is incorrect')`. No hay llamada HTTP.
- `src/app/core/service/auth.service.ts:25-27` — el `BehaviorSubject` se inicializa con `{}` cuando no hay usuario guardado.
- `src/app/core/guard/auth.guard.ts:14-18` — `AuthGuard.canActivate()` comprueba `if (this.authService.currentUserValue)`; como el valor por defecto es `{}` (truthy), **el guard deja pasar siempre**, incluso sin sesión.
- `src/app/app.routes.ts:7-10,12-15` — la ruta raíz con `MainLayoutComponent` usa `canActivate: [AuthGuard]`; `''` redirige a `/authentication/signin`. `src/app/dashboard/dashboard.routes.ts:6-14` — `dashboard` → redirige a `main` (`MainComponent`); `dashboard2` existe como alternativa. La "página por defecto" del dashboard es `/dashboard/main`.
- `src/app/core/interceptor/jwt.interceptor.ts:15-24` — agrega `Authorization: Bearer <token>` si `currentUser.token`.
- `src/app/core/interceptor/error.interceptor.ts:13-24` — en 401 llama `logout()` y `location.reload()`; luego `throwError(err.error.message || err.statusText)` (accede a `err.error.message` sin null-check).
- `src/app/app.config.ts:21-22` — interceptores registrados vía `HTTP_INTERCEPTORS` (clase) con `provideHttpClient()` **sin** `withInterceptorsFromDi()`, por lo que según la API de Angular no quedarían activos (ver hipótesis). `:20` `HashLocationStrategy` (rutas con `#`).
- `src/environments/environment.ts:6` y `environment.development.ts:3` — `apiUrl: 'http://localhost:4200'` (el propio dev server del frontend, no el backend). `angular.json` sin `proxy`/`proxyConfig` (grep sin coincidencias). Ningún `.ts` usa `apiUrl`.
- `src/app/layout/header/header.component.ts:166-172` — `logout()` llama `authService.logout()` y navega a signin.
- `src/app/core/service/auth.service.spec.ts` — único spec del servicio: solo "should be created". `signin.component.spec.ts` existe.
- `src/app/core/models/user.ts` — modelo `User` con `password` y `token` como campos, `firstName`, `lastName`, `username` (no coincide con lo que haría el backend).

**Backend (Django/DRF)**
- `backend/config/urls.py:6-9` — solo `admin/` y `api/health/`. **No existe ningún endpoint de login/autenticación.**
- `backend/config/settings/base.py:70-76` — DRF con `SessionAuthentication` por defecto y `IsAuthenticated` por defecto (denegar por defecto). `:11-19` `INSTALLED_APPS` sin `corsheaders` ni `rest_framework.authtoken` ni `simplejwt`; `:21-30` `MIDDLEWARE` sin CORS. `AUTH_USER_MODEL = 'accounts.User'` (`:21`).
- `backend/modules/accounts/models.py:4-5` — `User(AbstractUser)` sin campos extra; el login natural es `username` + `password` (no email). No hay usuarios sembrados; la base está vacía.
- `docs/adr/ADR-inicializar-backend-django-modelo-usuario.md` (sección Decisión y "Pendiente consciente") — el esquema de autenticación de la API (sesión/token/JWT), roles/permisos y CORS quedaron explícitamente **sin decidir**, a resolver "en un task posterior cuando el frontend lo requiera" — que es este task.
- `backend/config/health.py:1-3` — `/api/health/` es público (`AllowAny`), único precedente de endpoint DRF.
- `requirements/` — dependencias del backend en `backend/requirements/`; no se verificó si incluye `django-cors-headers` ni `simplejwt` (ver hipótesis).

**Reglas del proyecto**
- `CLAUDE.md` — frontend: Reactive Forms, tipos explícitos sin `any`, lógica no visual en services inyectables, sin suscripciones colgadas, organización por `features/<modulo>/`. Avisar antes de instalar dependencias nuevas. No tocar `.env`/secretos. Cambios acotados; proponer plan antes de tocar varios archivos.
- `docs/architecture/ddd.md` (sección 15, ~línea 980) — `core/auth/` y `core/interceptors/` como ubicación esperada para auth en el frontend.

### Hipótesis / supuestos no confirmados
- Probablemente los interceptores de la plantilla **no se ejecutan** (`provideHttpClient()` sin `withInterceptorsFromDi()`); no se verificó levantando la app.
- No se verificó el contenido de `backend/requirements/*.txt`; se asume que no hay `django-cors-headers` ni `djangorestframework-simplejwt`.
- Se asume que el identificador de login es `username` de Django (no email), pues la plantilla usa un campo de tipo email pero el modelo no lo define como `USERNAME_FIELD`. No confirmado con el usuario.
- Se asume que el frontend correrá en `localhost:4200` y el backend en otro puerto (típicamente 8000), por lo que habría un problema de origen cruzado (CORS/proxy) y de CSRF si se usa sesión; no verificado en ejecución.
- "Página por defecto" se interpreta como `/dashboard/main`; podría referirse a otra.
- No se sabe si se espera conservar los botones sociales, "Sign Up", "Forgot password" y "Remember me" (la plantilla los trae pero el backend no los soporta).
- El hecho de que `frontend/` esté sin versionar puede ser intencional o un olvido; condiciona en qué rama/PR puede entregarse este task.

### Módulos y dependencias relacionadas
- Backend: app `modules/accounts` (modelo de usuario, infraestructura de identidad, no bounded context), `config/settings/base.py` (DRF, middleware, apps), `config/urls.py`. Ningún módulo de negocio (`catalog`, `customers`, ...) está involucrado.
- Frontend: `authentication/signin`, `core/service/auth.service.ts`, `core/guard/auth.guard.ts`, `core/interceptor/*`, `app.config.ts`, `app.routes.ts`, `environments/*`, `layout/header` (logout).

### Implementaciones similares existentes
- Backend: solo `config/health.py` (endpoint DRF function-based con `AllowAny`); no hay serializers ni views de módulos todavía.
- Frontend: no hay llamadas HTTP reales en el código de la plantilla (se verificó que `apiUrl` no se usa); el login simulado de `AuthService` es el único patrón de auth.

### Comportamiento actual
Al abrir la app, `''` redirige a `/authentication/signin`. El formulario viene precargado con credenciales demo; al enviar se compara contra una lista local, se guarda un token falso en `localStorage` y se navega a `/dashboard/main`. No hay comunicación con el backend. El backend no tiene endpoint de login. El `AuthGuard` no protege realmente las rutas (siempre `true`).

Lenguaje de dominio: el frontend dice `username`/"Your Email"/"Sign in"; el backend/Django dice `username`/`password`; el mensaje requerido por el usuario es "credenciales inválidas" (la plantilla muestra mensajes en inglés distintos). Idioma de la UI: plantilla en inglés (con `ngx-translate`, `assets/i18n/`), proyecto en español.

### Restricciones
- Las de `CLAUDE.md` listadas arriba; `AuthService`/`LocalStorageService` prefijan la clave de storage con el tema (`light_`/`dark_`, `storage.service.ts:16-19`), lo que afecta dónde queda guardada la sesión.
- ADR vigente: `DEFAULT_PERMISSION_CLASSES = IsAuthenticated`; un endpoint de login debe ser explícitamente público.

### Riesgos identificados
- **Decisión de autenticación abierta y de alto impacto**: sesión vs token vs JWT, CORS/CSRF, almacenamiento del token en el navegador, expiración/logout. Es la deuda declarada en el ADR existente.
- `AuthGuard` hoy no bloquea acceso: si no se corrige, "no dejar pasar al usuario" no se cumple aunque el login falle (se puede entrar tecleando la URL).
- Interceptores posiblemente inactivos y `ErrorInterceptor` con acceso sin null-check a `err.error.message`; un 401 de credenciales inválidas en el login dispararía `logout()` + `location.reload()` si el interceptor se activa, ocultando el mensaje de error.
- Credenciales demo precargadas y lista de usuarios hardcodeada en el bundle del frontend.
- `frontend/` sin versionar: riesgo de perder el trabajo o de no poder abrir un PR coherente.
- Cobertura de tests casi nula en el área (solo "should be created").
- Backend sin usuarios sembrados: no hay forma de probar el login de punta a punta sin crear un usuario.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — Toca autenticación/autorización (esquema de auth de la API aún no decidido), requiere cambios en settings del backend (CORS, apps, DRF) y un nuevo endpoint, y cruza backend y frontend con impacto en seguridad.

### Diseño requerido
**NO** — La pantalla de login ya existe en la plantilla y el pedido es reutilizarla sin cambios visuales (solo mensaje de error); no hay pantallas ni flujos nuevos que comparar.

## Diseño
_No aplica_

## Arquitectura
- [ADR-frontend-login-backend-autenticacion-token](../adr/ADR-frontend-login-backend-autenticacion-token.md) — token DRF (`authtoken`), `POST /api/auth/login/` y `/logout/`, login por `username`, proxy de `ng serve` en lugar de CORS, mensaje genérico 401. Estado: Propuesto.

## Plan
- [PLAN-2026-10-07-frontend-login-backend](../plans/PLAN-2026-10-07-frontend-login-backend.md) — **v1**, Modo COMPLETO, Specification readiness: READY. Decisión del usuario: `frontend/` se versiona con un commit base dentro de este mismo PR.

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
