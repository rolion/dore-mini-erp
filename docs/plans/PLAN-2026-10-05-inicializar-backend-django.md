# PLAN-2026-10-05-inicializar-backend-django (v1)

**Task:** TASK-inicializar-backend-django
**DDRs relacionados:** Ninguno
**ADRs relacionados:**
- [ADR-inicializar-backend-django-stack-y-estructura](../adr/ADR-inicializar-backend-django-stack-y-estructura.md)
- [ADR-inicializar-backend-django-modelo-usuario](../adr/ADR-inicializar-backend-django-modelo-usuario.md)

## Objective
Crear el esqueleto ejecutable del backend (`backend/`) con Django 5.2 LTS + DRF y PostgreSQL por variables de entorno, listo para que cada módulo de negocio se agregue en su propio task.

## Context
Ver `docs/tasks/TASK-inicializar-backend-django.md`. El repo no tiene backend; `CLAUDE.md` y `docs/architecture/ddd.md` fijan stack y estructura; los ADR fijan versión, layout de settings, entorno y modelo de usuario.

## Current behavior
`backend/` no existe (en el checkout principal es un directorio vacío); ningún comando de `CLAUDE.md:15` funciona. Verificado de nuevo al planificar: `origin/main` = `466c871`, sin cambios desde la investigación. `pip index` muestra Django 6.1.1 como última; se mantiene 5.2 LTS por ADR.

## Expected behavior
Desde `backend/` con el venv activo y una PostgreSQL accesible: `python manage.py check`, `migrate`, `test` y `runserver` funcionan; `GET /api/health/` responde 200 JSON sin autenticación; cualquier otra ruta bajo `/api/` exige autenticación por defecto.

## Architecture considerations
Resumen de los ADR (no se re-derivan):
- Layout `config/ modules/ shared/` conforme a `ddd.md` §12; sin carpetas de módulos de negocio vacías.
- Settings por entorno (`base/local/test/production`) con `django-environ`; sin secretos hardcodeados ni `.env` versionado.
- `AUTH_USER_MODEL = "accounts.User"` fijado antes del primer `migrate`; `accounts` es infraestructura, no bounded context.
- Contrato API: no hay consumidores aún (Angular no llama al backend), sin riesgo de ruptura. Sin datos existentes, sin riesgo de migración.
- Dinero: no aplica todavía; se mantiene la regla `Decimal` para los módulos futuros.
- Seguridad: DRF `IsAuthenticated` por defecto; `production.py` exige `SECRET_KEY`, `DATABASE_URL` y `ALLOWED_HOSTS` sin default y `DEBUG=False`.

## Proposed solution
Generar el proyecto con la estructura de los ADR, a mano a partir de `startproject` (renombrando el paquete a `config` y partiendo `settings.py` en el paquete `settings/`), crear la app `modules/accounts` con el `User` mínimo y su migración `0001` generada por `makemigrations`, un endpoint `health` en `config/` (vista DRF `AllowAny`) y documentar el entorno en `CLAUDE.md`.

## Files/components affected
**Backend (nuevos, bajo `backend/`):**
- `manage.py` (default `config.settings.local`), `config/{__init__,urls,wsgi,asgi}.py`, `config/settings/{__init__,base,local,test,production}.py`
- `config/health.py` (vista) — o equivalente mínimo ubicado en `config/`
- `modules/__init__.py`, `modules/accounts/{__init__,apps,models}.py`, `modules/accounts/migrations/{__init__,0001_initial}.py`
- `shared/__init__.py`
- `requirements/{base,dev}.txt`, `.env.example`, `.gitignore` (de `backend/`: `.env`, `.venv/`, `__pycache__/`)

**Documentación:** `CLAUDE.md` (sección Comandos: crear venv, instalar, variables, `check/test`).

**Frontend:** ninguno.

## Implementation steps
1. **Entorno** (requiere confirmación, ver "Dependencias nuevas"): crear `backend/.venv` con Python 3.12, escribir `requirements/base.txt` (Django 5.2.x, djangorestframework, `psycopg[binary]`, django-environ) y `dev.txt` (`-r base.txt`, `bandit`), instalar.
2. Generar el proyecto con `django-admin startproject config .` dentro de `backend/`; convertir `settings.py` en el paquete `settings/` (`base`, `local`, `test`, `production`) leyendo `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL`, `TIME_ZONE` con `django-environ`; `LANGUAGE_CODE="es"`, `USE_TZ=True`, `DEFAULT_AUTO_FIELD` explícito. `manage.py`/`wsgi`/`asgi` apuntan a `config.settings.local` por defecto (producción vía variable de entorno).
3. Crear `modules/__init__.py`, `shared/__init__.py` y la app `modules/accounts` (`User(AbstractUser)` sin campos extra); registrar en `INSTALLED_APPS` y fijar `AUTH_USER_MODEL`.
4. Configurar DRF en `base.py`: `SessionAuthentication`, `IsAuthenticated`, renderer JSON, paginación por defecto.
5. `config/urls.py`: `path("api/", include(...))` con `GET /api/health/` (`AllowAny`, responde `{"status": "ok"}`); `django.contrib.admin` queda habilitado como en `startproject`.
6. Generar la migración con `python manage.py makemigrations accounts` (no escribirla a mano).
7. Agregar `.env.example` (solo nombres), `backend/.gitignore`, y verificar que ningún `.env` real quede versionado.
8. Escribir las pruebas (ver Test strategy) y ejecutarlas.
9. Actualizar `CLAUDE.md` (Comandos) con el flujo real de entorno y variables.
10. Verificar con `python manage.py check` y `check --deploy` bajo `production` (con variables de ejemplo), y que `makemigrations --check` no detecte cambios pendientes.

## Test strategy
- **Unitario/integración backend** (`python manage.py test`, requiere PostgreSQL por `DATABASE_URL`):
  - `GET /api/health/` → 200 y `{"status": "ok"}` sin credenciales.
  - Una ruta protegida de prueba bajo `/api/` (con una vista de prueba registrada solo en el test) → 401/403 sin sesión, confirmando la política de denegar por defecto.
  - `get_user_model()` es `accounts.User` y se puede crear un usuario con `create_user`.
  - `production.py`: importarlo sin `SECRET_KEY`/`DATABASE_URL` en el entorno lanza `ImproperlyConfigured`.
- **Checks sin BD:** `manage.py check`, `makemigrations --check --dry-run` (no requieren conexión activa).
- **E2E (Playwright): NO corresponde.** No hay flujo de usuario ni integración frontend-backend todavía; es una base sin UI. Playwright no se evalúa en `frontend/panel_admin/package.json` porque no se instalará.
- Cada paso con lógica (settings de producción, política de permisos, modelo de usuario, health) tiene al menos un caso arriba.

## Acceptance criteria
- `backend/` con la estructura de los ADR y sin carpetas de módulos de negocio vacías.
- Con venv + `DATABASE_URL` válido: `check`, `migrate`, `test` pasan y `runserver` sirve `/api/health/`.
- `makemigrations --check` sin cambios pendientes; la única migración es `accounts/0001`, generada por Django.
- Sin secretos ni `.env` real en el repo; `.env.example` solo con nombres.
- `production.py` falla ruidosamente si faltan variables obligatorias.
- `CLAUDE.md` documenta el entorno y comandos reales.

## Risks
- **Sin PostgreSQL local** (`pg_isready`/`psql` no están en el PATH del entorno de planificación): `migrate` y `test` no se podrán ejecutar hasta tener una instancia. Mitigación: pedir al usuario una `DATABASE_URL` (instancia local o contenedor) antes de implementar; si no la hay, `delivery-engineer` verificará solo los checks sin BD y lo declarará explícitamente — no se sustituye por SQLite.
- **Versión LTS vs. la última (6.1):** se acepta una versión no-última por soporte largo; migrar a 6.2 LTS futura es un task aparte.
- **`modules/accounts` fuera de `ddd.md`:** desviación documentada en el ADR; se sugiere mencionarla en `docs/architecture/ddd.md` en este mismo PR (ver Out of scope).
- Dependencias globales de Python (Django 4.2.1) pueden filtrarse si no se activa el venv; los comandos de verificación deben ejecutarse con el intérprete del venv.

## Out of scope
- Módulos de negocio, esquema de autenticación de API (token/JWT), roles/permisos, CORS, Docker, CI, despliegue, lockfile (poetry/uv).
- Preguntas abiertas para el usuario: (1) ¿hay una PostgreSQL local o un contenedor disponible y cuál es el nombre de base/usuario a documentar en `.env.example`? (2) ¿se desea añadir una nota sobre `accounts` en `docs/architecture/ddd.md` dentro de este PR?

## Dependencias nuevas
Requieren confirmación antes de instalarse (regla de `CLAUDE.md`), solo dentro de `backend/.venv`:
- Producción: `Django` 5.2.x, `djangorestframework`, `psycopg[binary]`, `django-environ`.
- Desarrollo: `bandit` (usado por `delivery-review`).
