# ADR-frontend-login-backend-autenticacion-token: Autenticación de la API con token DRF y proxy de desarrollo

**Estado:** Propuesto
**Task relacionado:** TASK-frontend-login-backend
**Fecha:** 2026-10-07

## Contexto
El frontend Angular (SPA) debe validar el login contra el backend y bloquear el acceso si las credenciales son inválidas. Hoy el login es simulado (`AuthService` con usuario hardcodeado), el backend no tiene endpoint de login, y `ADR-inicializar-backend-django-modelo-usuario` dejó explícitamente pendiente el esquema de autenticación de la API, los permisos por rol y CORS "cuando el frontend lo requiera". El backend usa `SessionAuthentication` + `IsAuthenticated` por defecto; `requirements/base.txt` solo trae Django, DRF, psycopg y django-environ (sin `django-cors-headers` ni `simplejwt`). El frontend ya modela una sesión basada en token (`User.token`, `JwtInterceptor` con `Authorization: Bearer`, persistencia en `LocalStorageService`). No hay Docker/nginx todavía. El MVP es un panel administrativo interno de un solo origen lógico.

## Decisión
1. **Esquema: token opaco de DRF (`rest_framework.authtoken`)**, ya incluido en `djangorestframework` (sin dependencias nuevas).
   - Se añade `rest_framework.authtoken` a `INSTALLED_APPS` (migración propia de la librería) y `TokenAuthentication` a `DEFAULT_AUTHENTICATION_CLASSES`, conservando `SessionAuthentication` para el admin de Django. `IsAuthenticated` sigue como permiso por defecto.
   - Endpoint `POST /api/auth/login/` en `modules/accounts/api/`, explícitamente público (`AllowAny`), recibe `username` + `password`, devuelve `{ token, user: { id, username, first_name, last_name } }` en éxito y **HTTP 401 con un mensaje genérico de credenciales inválidas** en fallo (sin distinguir usuario inexistente de contraseña errónea). Usuarios inactivos se tratan igual que inválidos.
   - Endpoint `POST /api/auth/logout/` (autenticado) que elimina el token del usuario, de modo que el logout invalida la sesión en el servidor.
   - El serializer valida forma y tipos; la verificación de credenciales usa `django.contrib.auth.authenticate`. No se crea dominio ni aplicación en `accounts` (sigue siendo infraestructura de identidad, según el ADR del modelo de usuario).
2. **Identificador de login: `username` de Django.** No se cambia `USERNAME_FIELD`; el campo del formulario se muestra como "Usuario" (sin `type="email"`).
3. **Origen cruzado: proxy del dev server de Angular, sin CORS.** En desarrollo, `ng serve` hace proxy de `/api` al backend (`proxy.conf.json` referenciado en `angular.json`), y el frontend usa URLs relativas (`/api/...`). No se agrega `django-cors-headers`. En producción se asume mismo origen detrás de un reverse proxy (a definir en el task de despliegue).
4. **Cliente:** el token se persiste donde la plantilla ya persiste la sesión (`LocalStorageService`), y se envía como `Authorization: Token <token>` (el prefijo de DRF, no `Bearer`). Un 401 en `login` no debe disparar logout/recarga. El guard de rutas debe considerar autenticado solo a quien tiene token real.
5. Redirección tras login exitoso: `/dashboard/main` (página por defecto del dashboard existente).

## Alternativas consideradas
- **Sesión Django + cookie (SessionAuthentication) con CSRF:** sin dependencias y revocación natural, pero obliga a manejar CSRF y cookies entre orígenes distintos (SameSite, `withCredentials`, `CSRF_TRUSTED_ORIGINS`), y la plantilla ya está pensada para token. Más fricción en desarrollo con dos puertos.
- **JWT (`djangorestframework-simplejwt`):** access/refresh con expiración, estándar de facto en SPAs, pero requiere dependencia nueva (hay que avisar según `CLAUDE.md`), manejo de refresh, rotación y blacklist; es sobreingeniería para un panel interno sin requisitos de expiración ni de terceros que validen tokens. Sigue siendo una migración posible más adelante.
- **CORS con `django-cors-headers`:** necesario solo si front y back viven en orígenes distintos en producción; hoy no hay evidencia de eso. Se pospone hasta que el despliegue lo requiera.
- **Mantener el login simulado:** no cumple el requerimiento.

## Estrategia de rollback / mitigación
- Cambio aditivo: nuevo endpoint y una app de librería (`authtoken`) con su migración propia. El rollback es revertir el PR y, si ya se aplicó, `migrate authtoken zero`; no se tocan migraciones existentes ni el modelo `User`.
- Seguridad: denegar por defecto se mantiene; solo `/api/auth/login/` y `/api/health/` son públicos. Mensaje de error genérico para evitar enumeración de usuarios. Un token comprometido se revoca borrándolo (logout o admin). El login debería tener limitación de intentos (throttling de DRF para `AnonRateThrottle`/scope de login) para mitigar fuerza bruta.
- Si el equipo decide luego migrar a JWT o sesión, el contrato del frontend (`login` → `{token, user}`) queda aislado en `AuthService`, lo que acota el cambio.

## Consecuencias
- Fácil: sin dependencias nuevas, implementación corta, logout con revocación real, el frontend reutiliza el patrón token de la plantilla.
- Difícil / deuda aceptada conscientemente:
  - Los tokens de DRF **no expiran**; no hay refresh ni rotación.
  - El token en `localStorage` es accesible a JavaScript (riesgo ante XSS); se acepta para el MVP interno.
  - Roles/permisos por módulo siguen sin definirse (fuera de alcance).
  - Si en producción front y back quedan en orígenes distintos habrá que añadir CORS (nueva dependencia) en un task posterior.
  - Alta de usuarios: no hay registro; los usuarios se crean con `createsuperuser`/admin, y el enlace "Sign Up" de la plantilla queda sin funcionalidad.
- Fuera del alcance de la decisión: el hecho de que `frontend/` no esté versionado (tema de proceso, a resolver antes de abrir el PR).
