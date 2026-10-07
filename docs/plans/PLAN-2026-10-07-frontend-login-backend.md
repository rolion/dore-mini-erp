# PLAN-2026-10-07-frontend-login-backend (v1)

**Task:** TASK-frontend-login-backend
**Modo:** COMPLETO
**DDRs relacionados:** Ninguno (Diseño requerido: NO)
**ADRs relacionados:** [ADR-frontend-login-backend-autenticacion-token](../adr/ADR-frontend-login-backend-autenticacion-token.md)
**Specification readiness:** READY

> Modo COMPLETO por el eje 3: cambio de autenticación/autorización, contrato API nuevo y decisión arquitectónica (ADR).

## Objective
Reemplazar el login simulado de la plantilla por un login validado contra el backend: credenciales válidas → entra y va a `/dashboard/main`; credenciales inválidas → mensaje de credenciales inválidas y sin acceso a las rutas protegidas.

## Context
Ver `docs/tasks/TASK-frontend-login-backend.md` (Investigación). Resumen: el backend no tiene endpoint de login (`backend/config/urls.py:6-9`); el frontend autentica contra una lista hardcodeada (`frontend/panel_admin/src/app/core/service/auth.service.ts:11-20,34-52`); `AuthGuard` siempre deja pasar (`core/guard/auth.guard.ts:14-18`, el usuario por defecto es `{}`); los interceptores de la plantilla están registrados por `HTTP_INTERCEPTORS` sin `withInterceptorsFromDi()` (`app.config.ts:21-22`). El ADR fija: token DRF, `POST /api/auth/login/` y `/logout/`, login por `username`, proxy de `ng serve` sin CORS.

**Nota de vigencia:** `frontend/` no está versionado en git. Decisión del usuario: la rama `task/TASK-frontend-login-backend` incluye un primer commit "base" con `frontend/panel_admin` y `frontend/panel_admin_doc` tal cual están hoy (sin `node_modules`/`dist`), y los cambios de este task van en commits posteriores para que el diff real sea revisable.

# Specification

## Domain context
**Bounded Context:** ninguno de negocio. `modules/accounts` es infraestructura de identidad (ADR del modelo de usuario); no tiene `domain/` ni `application/`.
**Related contexts:** ninguno. Los módulos de negocio no se ven afectados.

## Ubiquitous language
| Term | Meaning | Source |
|---|---|---|
| username | Identificador de login (`AbstractUser.username`) | `backend/modules/accounts/models.py`, ADR |
| token | Token opaco de DRF asociado a un usuario; se envía como `Authorization: Token <token>` | ADR |
| credenciales inválidas | Usuario inexistente, contraseña errónea o usuario inactivo; no se distinguen | ADR |

Inconsistencias declaradas: la plantilla rotula el campo como "Your Email" con `type="email"` y variable `username` (`signin.component.html:20-24`), mientras el backend autentica por `username` (no necesariamente un email). Se resuelve por el ADR: el campo se muestra como "Usuario". "Remember me", "Forgot password", "Sign Up" y login social existen en la plantilla pero no tienen soporte backend (ver Out of scope).

## Current behavior
Ver Context. Hoy cualquiera puede entrar a `/#/dashboard/main` escribiendo la URL (guard siempre `true`), y el login solo acepta `admin@email.com`/`admin@123`, que además vienen precargados en el formulario (`signin.component.ts:28-29`).

## Expected behavior
- El formulario de login valida usuario/contraseña contra el backend.
- Con credenciales válidas, el usuario queda autenticado (token guardado) y es llevado a `/dashboard/main`.
- Con credenciales inválidas, permanece en el login, ve el mensaje "Credenciales inválidas" y no queda autenticado.
- Las rutas protegidas solo son accesibles con una sesión autenticada real; sin ella, redirigen a `/authentication/signin`.
- Cerrar sesión invalida el token en el servidor y limpia la sesión local.

## Domain rules / invariants
Existentes (deben seguir siendo verdaderas):
- INV-01: el permiso por defecto de la API es `IsAuthenticated`; solo endpoints explícitamente públicos son accesibles sin autenticación (hoy `/api/health/`).
Nuevas:
- INV-02: `POST /api/auth/login/` es el único endpoint nuevo público; `logout` exige autenticación.
- INV-03: la respuesta de login fallido es idéntica (cuerpo y status) para usuario inexistente, contraseña errónea y usuario inactivo.
- INV-04: ninguna respuesta de la API incluye la contraseña ni su hash.

## Acceptance criteria
- AC-01: Given un usuario activo con credenciales correctas, When envía `POST /api/auth/login/`, Then recibe 200 con `{token, user: {id, username, first_name, last_name}}` y el token queda asociado a ese usuario.
- AC-02: Given credenciales incorrectas (usuario inexistente, contraseña errónea o usuario inactivo), When envía login, Then recibe 401 con `{"detail": "Credenciales inválidas."}` idéntico en los tres casos y no se crea token (INV-03).
- AC-03: Given el formulario de login con credenciales válidas, When se envía, Then el frontend guarda la sesión y navega a `/dashboard/main`.
- AC-04: Given credenciales inválidas, When se envía el formulario, Then se muestra en el `alert alert-danger` el mensaje "Credenciales inválidas", el usuario permanece en `/authentication/signin` y no se guarda sesión.
- AC-05: Given un navegador sin sesión (sin token), When accede a cualquier ruta protegida (p. ej. `/#/dashboard/main`), Then es redirigido a `/authentication/signin`.
- AC-06: Given una sesión autenticada, When el usuario cierra sesión, Then el token se elimina en el servidor, se limpia el almacenamiento local y se navega a `/authentication/signin`; el mismo token deja de autenticar.
- AC-07: Given un usuario autenticado con token, When el frontend hace peticiones a `/api/...`, Then envía `Authorization: Token <token>`.
- AC-08: Given el formulario con usuario o contraseña vacíos, When se intenta enviar, Then no se hace ninguna petición y se indica que ambos son obligatorios.
- AC-09: El formulario ya no viene precargado con credenciales y el frontend no contiene usuarios ni contraseñas hardcodeados.

## Edge cases
- EDGE-01: Una petición de login que incluye un header `Authorization` inválido o vencido no debe fallar por eso; el login ignora cualquier autenticación previa.
- EDGE-02: Un 401 devuelto por el propio login no debe provocar logout ni recarga de página (que ocultaría el mensaje).
- EDGE-03: Un token ya inválido en el servidor (p. ej. borrado) usado en una petición protegida → 401 → el frontend limpia la sesión y vuelve al login.
- EDGE-04: Un usuario con token existente que inicia sesión de nuevo reutiliza su token (`get_or_create`); cerrar sesión en un dispositivo lo invalida en todos. Comportamiento aceptado (ADR: sin expiración ni multi-token).

## Error cases
- Login con campos faltantes → 400 con errores por campo (validación de forma del serializer).
- Backend inalcanzable o error 5xx/0 en login → el frontend muestra "No se pudo conectar con el servidor. Inténtalo de nuevo." (no "Credenciales inválidas"), sin guardar sesión.
- Demasiados intentos de login → 429 (throttling); el frontend muestra "Demasiados intentos. Espera un momento e inténtalo de nuevo."
- Logout sin token válido → 401.

## Authorization / permissions
Sin roles en este task: cualquier usuario activo puede iniciar sesión y acceder a todo el panel (los roles quedan fuera de alcance, ADR).

## API contract
- API-01: `POST /api/auth/login/` — público. Request JSON `{username: string, password: string}` (ambos requeridos, no vacíos). 200 `{token: string, user: {id: number, username: string, first_name: string, last_name: string}}`; 400 errores por campo; 401 `{detail: "Credenciales inválidas."}`; 429 al exceder el throttle. Throttle de scope `login` (10/min por IP).
- API-02: `POST /api/auth/logout/` — requiere `Authorization: Token <token>`. 204 sin cuerpo y elimina el token; 401 si falta o es inválido.
- API-03: Los demás endpoints (`/api/health/`) no cambian. `TokenAuthentication` se añade antes de `SessionAuthentication` en `DEFAULT_AUTHENTICATION_CLASSES`; el admin de Django sigue usando sesión.

## UI behavior
- UI-01: Campo de usuario rotulado "Usuario", `type="text"`, placeholder "Usuario"; campo de contraseña sin cambios de rotulación necesarios salvo lo mínimo para coherencia ("Contraseña"). Sin valores precargados.
- UI-02: Mensajes de error (alerta existente `alert alert-danger`): "Usuario y contraseña son obligatorios." / "Credenciales inválidas" / mensajes de conexión y throttle de Error cases. Se limpian al reenviar.
- UI-03: Mientras la petición está en curso el botón "Sign in" queda deshabilitado para evitar envíos dobles.
- UI-04: Sin cambios en el resto de la pantalla (imágenes, marca, enlaces Forgot/Sign Up, login social, "Remember me").

## Non-functional requirements
- Seguridad: mensaje genérico (INV-03); throttling de login; token solo por header, nunca en URL; no loguear contraseñas.
- Compatibilidad: aditivo; no cambia migraciones existentes.

## Out of scope
- Roles/permisos, registro de usuarios, recuperación de contraseña, "Remember me" funcional, login social, expiración/refresh de tokens, CORS, despliegue/nginx, creación de usuarios iniciales (se usa `createsuperuser`/admin), traducción completa de la pantalla (solo se tocan los textos indicados en UI-01/UI-02).

## Open questions
- Ninguna bloqueante. Pendiente para un task posterior: política de expiración de tokens y almacenamiento (ADR, Consecuencias).

# Test Specification

## Unit tests
- Frontend `AuthService` (`HttpTestingController`): login OK guarda sesión y emite usuario (AC-03, AC-09); login 401 → error "Credenciales inválidas" sin guardar (AC-04); error 0/500 → mensaje de conexión; 429 → mensaje de throttle; logout llama la API y limpia sesión aun si la API falla (AC-06).
- Frontend `AuthGuard`: sin token → redirige a signin (AC-05); con token → permite.
- Frontend interceptor de token: agrega `Authorization: Token ...` si hay token y no si no hay (AC-07).
- Frontend interceptor de error: 401 en `/auth/login/` no hace logout (EDGE-02); 401 en otra URL limpia sesión y redirige (EDGE-03); `err.error` nulo no rompe.
- Frontend `SigninComponent`: formulario vacío → no llama al servicio y muestra mensaje (AC-08); login OK → `router.navigate(['/dashboard/main'])` (AC-03); error → muestra mensaje, no navega (AC-04); sin valores precargados (AC-09).

## Integration tests
- Backend (`APITestCase`, `config.settings.test`): login OK (AC-01, INV-04), contraseña errónea / usuario inexistente / usuario inactivo con el mismo cuerpo (AC-02, INV-03), campos faltantes → 400, header `Authorization` inválido en login no rompe (EDGE-01), logout elimina token y ese token ya no autentica (AC-06), logout sin auth → 401, throttle → 429 con el rate sobreescrito para el test.

## E2E
**¿Corresponde E2E?** NO — Playwright no está instalado (`package.json` solo trae Karma/Jasmine); añadirlo es una dependencia e infraestructura nuevas desproporcionadas para este task, y cada extremo del contrato (API-01/02) queda cubierto por tests de integración backend y tests frontend con `HttpTestingController`. La integración real se verifica con un smoke manual en `delivery-review` (backend + `ng serve` con proxy, usuario creado con `createsuperuser`): login válido, login inválido, acceso directo a `/#/dashboard/main` sin sesión, logout. Se acepta la deuda de no tener E2E automatizado; un E2E de login es el primer candidato cuando se instale Playwright.

## Regression tests
- `HealthTests` y `DefaultPermissionTests` (`backend/config/tests.py`) siguen pasando: `/api/health/` público y permiso por defecto denegar.
- El test `signin.component.spec.ts` y `auth.service.spec.ts` existentes se actualizan (el segundo hoy solo verifica creación).
- `npm run build` y `npm run lint` del frontend sin errores nuevos.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Backend integration test |
| AC-02 | Backend integration test (3 casos, comparación de cuerpo) |
| AC-03 | Angular unit tests (AuthService + SigninComponent) + smoke manual |
| AC-04 | Angular unit tests (SigninComponent + AuthService) + smoke manual |
| AC-05 | Angular unit test (AuthGuard) + smoke manual |
| AC-06 | Backend integration test + Angular unit test (AuthService) + smoke manual |
| AC-07 | Angular unit test (interceptor de token) |
| AC-08 | Angular unit test (SigninComponent) |
| AC-09 | Angular unit tests + revisión de código (sin lista `users`) |

# Implementation Plan

## Architecture considerations
Sigue el ADR: sin dependencias nuevas, sin CORS, `accounts` sigue siendo infraestructura (sin `domain/`/`application/`); la capa HTTP vive en `modules/accounts/api/` y los serializers solo validan forma. Los módulos de negocio no se tocan. Frontend: lógica no visual en `AuthService` inyectable, formulario con Reactive Forms tipados (sin `any`), sin suscripciones colgadas (`takeUntilDestroyed`/`take(1)`). El destino de auth en frontend sigue en `core/` de la plantilla (ya existente) en vez de reorganizar a `core/auth/` — reorganizar queda fuera de alcance.

## Proposed solution
**Backend**
1. `config/settings/base.py`: añadir `'rest_framework.authtoken'` a `INSTALLED_APPS`; `TokenAuthentication` antes de `SessionAuthentication`; `DEFAULT_THROTTLE_RATES = {'login': '10/min'}`.
2. `modules/accounts/api/`: `serializers.py` (`LoginSerializer`: `username`, `password` requeridos, `trim_whitespace=False` en password; `UserSerializer` de salida con los 4 campos), `views.py` (`LoginView` con `authentication_classes = []`, `permission_classes = [AllowAny]`, `throttle_classes = [ScopedRateThrottle]`, `throttle_scope = 'login'`; usa `authenticate()` y `Token.objects.get_or_create`; en fallo devuelve **directamente** `Response({'detail': 'Credenciales inválidas.'}, status=401)` — no lanzar `AuthenticationFailed`, porque sin header de autenticación DRF lo degrada a 403; `LogoutView` autenticada que borra `request.auth` y devuelve 204), `urls.py`.
3. `config/urls.py`: `path('api/auth/', include('modules.accounts.api.urls'))`.
4. Migración: `python manage.py migrate` aplica las de `authtoken` (de la librería; no se crea ninguna en el repo).

**Frontend** (`frontend/panel_admin/`)
5. `proxy.conf.json` (`/api` → `http://localhost:8000`) y referencia `proxyConfig` en la configuración `development` de `serve` en `angular.json`; `environment*.ts`: `apiUrl: '/api'`.
6. `core/models/user.ts`: modelo sin `password`; `token` requerido para sesión. Tipos de respuesta del login (`LoginResponse`).
7. `core/service/auth.service.ts`: eliminar `users`; `login()` con `HttpClient.post`, guarda `{...user, token}` en `LocalStorageService`, emite el usuario, mapea errores a mensajes (401 → "Credenciales inválidas"; 429; otros → conexión); `logout()` llama `POST /auth/logout/` y limpia la sesión siempre (mantiene el retorno `{success:false}` que consume `header.component.ts:166-172`); `isAuthenticated` por token.
8. `core/guard/auth.guard.ts`: autenticado solo si `currentUserValue?.token`; si no, `UrlTree` a `/authentication/signin`.
9. Interceptores: convertir `jwt.interceptor.ts` y `error.interceptor.ts` a interceptores funcionales y registrarlos con `provideHttpClient(withInterceptors([...]))` en `app.config.ts` (quitar `HTTP_INTERCEPTORS`). Token con prefijo `Token`; error: excepción para la URL de login, null-safe sobre `err.error`, 401 en otras URLs limpia la sesión y redirige a signin.
10. `signin.component.ts/html`: `FormBuilder` tipado no-nullable, sin valores iniciales, validación de requeridos, deshabilitar botón durante la petición, mensajes de UI-02, navegar a `/dashboard/main`; ajustar etiqueta/`type` del campo usuario (UI-01).
11. Tests de la Test Specification; actualizar `auth.service.spec.ts` y `signin.component.spec.ts`.
12. Documentar en `CLAUDE.md` (comandos): `ng serve` usa proxy a `localhost:8000`; crear usuario con `createsuperuser`.

## Files/components affected
- Backend: `config/settings/base.py`, `config/urls.py`, `modules/accounts/api/{__init__,serializers,views,urls}.py`, tests en `modules/accounts/tests.py` (o `api/tests.py`).
- Frontend: `angular.json`, `proxy.conf.json` (nuevo), `src/environments/*.ts`, `src/app/app.config.ts`, `core/{models/user.ts, service/auth.service.ts, guard/auth.guard.ts, interceptor/*.ts}`, `authentication/signin/*`, specs.
- Database/migrations: solo las propias de `rest_framework.authtoken`; ninguna migración del repo.
- Documentation: `CLAUDE.md` (comandos/proxy).

## Implementation steps
1. Commit base: versionar `frontend/` tal cual (sin `node_modules`/`dist`; verificar `.gitignore`).
2. Backend: settings, serializers, vistas, URLs (AC-01, AC-02, INV-02, INV-03, INV-04, EDGE-01, API-01..03) + tests de integración.
3. Frontend: proxy y environments (soporte de API-01/02 en desarrollo).
4. Frontend: modelo, `AuthService`, interceptores y guard (AC-05, AC-06, AC-07, EDGE-02, EDGE-03) + tests.
5. Frontend: `SigninComponent` (AC-03, AC-04, AC-08, AC-09, UI-01..03) + tests.
6. Ejecutar suites (backend `manage.py test`, frontend `npm test`, `npm run lint`, `npm run build`) y smoke manual de extremo a extremo.
7. Actualizar `CLAUDE.md`.

## Database / migrations
`rest_framework.authtoken` aporta su migración (tabla `authtoken_token`, FK a `AUTH_USER_MODEL`). Aditiva y reversible con `migrate authtoken zero`. No se edita ninguna migración existente.

## Risks
- Interceptores de la plantilla hoy probablemente inactivos: al activarlos (paso 9) pueden cambiar el comportamiento de otras pantallas de la plantilla que hagan HTTP; la plantilla no consume `/api` hoy, riesgo bajo. Mitigación: tests de interceptores y smoke.
- Activar la protección real del guard puede dejar inaccesibles rutas de demo si algún componente espera sesión simulada; mitigación: smoke de navegación al dashboard.
- Token sin expiración en `localStorage` (deuda aceptada en el ADR).
- Throttle por IP detrás de un proxy usa la IP del proxy si no se configura `X-Forwarded-For`; relevante solo en despliegue.
- Versionar `frontend/` en el mismo PR hace el PR grande; mitigado separando el commit base.

## New dependencies
Ninguna.
