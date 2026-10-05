# dore-mini-erp

Mini ERP. Proyecto nuevo, en construcción.

## Estructura

- `backend/` — API en Python + Django + DRF, monolito modular con DDD pragmático en `backend/modules/` (aún vacío). Base de datos: PostgreSQL. Ver `docs/architecture/ddd.md`.
- `frontend/panel_admin/` — Angular 21 sobre la plantilla "Oreva" (Bootstrap 5, ngx-datatable, ng-select, ngx-translate).
- `frontend/panel_admin_doc/` — documentación HTML de la plantilla (referencia, no se edita).
- `docs/` — artefactos del flujo `delivery-*` (ver `docs/README.md`).
- `.claude/skills/` — skills `delivery-*`.

## Comandos

- Frontend (desde `frontend/panel_admin/`): `npm start`, `npm run build`, `npm test` (Karma), `npm run lint`.
- Backend (desde `backend/`, Python 3.12): entorno con `python -m venv .venv`, activar y `pip install -r requirements/dev.txt`. Copiar `.env.example` a `.env` (no versionado) o exportar las variables: `DATABASE_URL` (PostgreSQL, p. ej. `postgres://usuario:clave@localhost:5432/doredb`), `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `TIME_ZONE`. Settings por entorno en `config/settings/` (`local` por defecto en `manage.py`; `DJANGO_SETTINGS_MODULE=config.settings.test` para tests; `production` exige todas las variables). Comandos: `python manage.py runserver`, `python manage.py test`, `python manage.py makemigrations`, `python manage.py migrate`. Salud: `GET /api/health/`. Base de datos: PostgreSQL (no usar SQLite salvo tests explícitos); la conexión se configura por variables de entorno, nunca hardcodeada.

## Reglas

- Cambios acotados a un objetivo; antes de tocar varios archivos, proponer un plan y esperar confirmación.
- Dinero siempre en `Decimal` (backend) — nunca `float`.
- Nunca editar una migración ya aplicada: crear una nueva con `makemigrations`.
- No leer ni modificar `.env`, credenciales ni secretos; no commitearlos.
- Avisar antes de instalar cualquier dependencia nueva (`pip` / `npm`).
- Arquitectura: `docs/architecture/ddd.md` es la referencia. Módulos `catalog`, `customers`, `sales`, `expenses`, `reporting`, cada uno con `domain/ application/ infrastructure/ api/` (crear carpetas solo cuando hagan falta). El dominio no importa Django; los módulos no se importan infraestructura entre sí; Reporting solo lee. Estados cambian por métodos del agregado (`order.deliver()`), no por asignación directa. Los serializers validan forma y tipos.
- No agregar abstracciones DDD que no respondan a una necesidad real del negocio (ver sección 29 del documento). Fuera del MVP: microservicios, event sourcing, CQRS completo, inventario/producción avanzados.
- Frontend: organizar por `src/app/features/<modulo>/` (pages, components, services, models) según el documento DDD. Lógica no visual en services inyectables, tipos explícitos (sin `any`), Reactive Forms, sin suscripciones colgadas.
- Rama base: `main`. Una rama y un PR por task (`task/TASK-<slug>`).

## Flujo de trabajo

Tareas no triviales usan las skills `delivery-*`: investigate → design → architect → plan → engineer → review → publish. Cada task vive en `docs/tasks/TASK-<slug>.md`.
