# dore-mini-erp

Mini ERP. Proyecto nuevo, en construcción.

## Estructura

- `backend/` — API en Python + Django + Django REST Framework (aún vacío).
- `frontend/panel_admin/` — Angular 21 sobre la plantilla "Oreva" (Bootstrap 5, ngx-datatable, ng-select, ngx-translate).
- `frontend/panel_admin_doc/` — documentación HTML de la plantilla (referencia, no se edita).
- `docs/` — artefactos del flujo `delivery-*` (ver `docs/README.md`).
- `.claude/skills/` — skills `delivery-*`.

## Comandos

- Frontend (desde `frontend/panel_admin/`): `npm start`, `npm run build`, `npm test` (Karma), `npm run lint`.
- Backend (desde `backend/`): `python manage.py runserver`, `python manage.py test`, `python manage.py makemigrations`, `python manage.py migrate`. Actualizar esta sección cuando se defina el entorno (venv, requirements, DB).

## Reglas

- Cambios acotados a un objetivo; antes de tocar varios archivos, proponer un plan y esperar confirmación.
- Dinero siempre en `Decimal` (backend) — nunca `float`.
- Nunca editar una migración ya aplicada: crear una nueva con `makemigrations`.
- No leer ni modificar `.env`, credenciales ni secretos; no commitearlos.
- Avisar antes de instalar cualquier dependencia nueva (`pip` / `npm`).
- Lógica de negocio fuera de views/viewsets (capa de servicios por app); los serializers validan forma y tipos.
- Frontend: lógica no visual en services inyectables, tipos explícitos (sin `any`), Reactive Forms, sin suscripciones colgadas.
- Rama base: `main`. Una rama y un PR por task (`task/TASK-<slug>`).

## Flujo de trabajo

Tareas no triviales usan las skills `delivery-*`: investigate → design → architect → plan → engineer → review → publish. Cada task vive en `docs/tasks/TASK-<slug>.md`.
