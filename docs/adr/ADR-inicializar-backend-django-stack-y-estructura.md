# ADR-inicializar-backend-django-stack-y-estructura: Stack, estructura y configuración del backend

**Estado:** Propuesto
**Task relacionado:** TASK-inicializar-backend-django
**Fecha:** 2026-10-05

## Contexto
`backend/` no existe. `CLAUDE.md` exige Python + Django + DRF, PostgreSQL configurado por variables de entorno (sin SQLite salvo tests explícitos), sin secretos en el repo, y `docs/architecture/ddd.md` (sección 12) propone `backend/{manage.py, config/settings/, config/urls.py, modules/, shared/domain/}`. Ningún documento fija versión de Django, layout de settings, gestor de dependencias ni librería de entorno.

## Decisión
- **Versión:** Django 5.2 LTS (serie LTS vigente, soportada hasta 2028) + Django REST Framework, sobre Python 3.12 (el del entorno). No se usa el Django 4.2.1 del Python global.
- **Entorno aislado:** `venv` en `backend/.venv` (ignorado por git) y `requirements/base.txt`, `requirements/dev.txt` con versiones fijadas. Dependencias iniciales: `Django`, `djangorestframework`, `psycopg[binary]` (v3), `django-environ`. Instalarlas requiere aviso/confirmación previa (regla de `CLAUDE.md`).
- **Layout** (sigue `ddd.md` sección 12, sin crear capas vacías):
  ```text
  backend/
  ├── manage.py
  ├── config/{__init__.py, urls.py, wsgi.py, asgi.py, settings/{base,local,test,production}.py}
  ├── modules/__init__.py        # vacío; cada módulo se crea en su propio task
  ├── shared/__init__.py         # shared/domain se crea cuando haya contenido real
  ├── requirements/{base,dev}.txt
  ├── .env.example               # solo nombres de variables, sin valores reales
  └── .gitignore                 # .env, .venv, __pycache__
  ```
- **Settings:** `base.py` común; `local.py` (DEBUG) por defecto en `manage.py`; `test.py`; `production.py` (`DEBUG=False`, hosts obligatorios). Selección por `DJANGO_SETTINGS_MODULE`.
- **Variables de entorno** vía `django-environ`: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL` (PostgreSQL), `TIME_ZONE` (default `UTC`). `SECRET_KEY` y `DATABASE_URL` sin default en `production`; en `local` no se hardcodea ningún secreto real. `LANGUAGE_CODE="es"`, `USE_TZ=True`.
- **Base de datos:** solo PostgreSQL, también en `test.py` (nada de SQLite).
- **API base:** `config/urls.py` monta `/api/`; DRF configurado con paginación y respuestas JSON únicamente; un endpoint `GET /api/health/` sin autenticación como smoke test. Los routers de cada módulo se agregan en sus propios tasks.
- **Fuera de alcance:** módulos de negocio, CORS, Docker/CI, despliegue.

## Alternativas consideradas
- **Django 6.0 (no LTS):** más nuevo pero con soporte corto; para una base que vivirá años gana la LTS.
- **Un solo `settings.py`:** más simple, pero mezcla DEBUG/producción y `ddd.md` ya prevé `settings/` como paquete; el costo de dividir ahora es mínimo.
- **poetry/uv en vez de venv + requirements:** mejor lockfile, pero agrega una herramienta no decidida por el equipo y las skills asumen `python manage.py ...` plano. Revisable después sin afectar el código.
- **`python-decouple` / `os.environ` a mano:** `django-environ` ya parsea `DATABASE_URL` y es el más común; el costo de cambiarlo es bajo.
- **Crear ya las carpetas de los 5 módulos:** contradice "crear carpetas solo cuando hagan falta" (`CLAUDE.md`, `ddd.md`).

## Estrategia de rollback / mitigación
El cambio es aditivo: solo crea archivos nuevos bajo `backend/` y edita `CLAUDE.md` (sección Comandos). Rollback = revertir el PR/commit; no hay datos ni migraciones propias (las del modelo de usuario están en el otro ADR). Aislar con venv evita contaminar el Python global. Ningún secreto se versiona (`.env.example` sin valores reales).

## Consecuencias
- Queda fácil: arrancar módulos nuevos sobre una base uniforme, correr `manage.py check/test` con PostgreSQL real.
- Más difícil: los tests requieren una instancia PostgreSQL accesible (deuda aceptada por la regla del proyecto).
- Deuda consciente: sin lockfile transitivo ni CI/Docker todavía; se abordan en tasks aparte cuando haga falta.
