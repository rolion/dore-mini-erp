# TASK-inicializar-backend-django: Inicializar el proyecto backend con Django

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** NO
**Rama:** `task/TASK-inicializar-backend-django`
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/2

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-05 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-10-05 | ARCHITECTURE → PLANNING | ADRs de stack/estructura y modelo de usuario propuestos | delivery-architect |
| 2026-10-05 | PLANNING → ENGINEERING | Plan v1 listo y PR abierto, pendiente de aprobación | delivery-plan |

## Investigación

### Requerimiento
"inicializa el proyecto de backend con django framework" — crear el esqueleto del proyecto Django/DRF del backend de `dore-mini-erp`, hoy inexistente.

### Hechos encontrados
- `backend/` no existe en este worktree y en el checkout principal es un directorio vacío (verificado con `ls -la`); no hay `manage.py`, `config/`, `requirements*` ni `modules/`.
- `CLAUDE.md:5` — el backend es "Python + Django + DRF, monolito modular con DDD pragmático en `backend/modules/` (aún vacío). Base de datos: PostgreSQL".
- `CLAUDE.md:15` — comandos esperados desde `backend/`: `runserver`, `test`, `makemigrations`, `migrate`. PostgreSQL, "no usar SQLite salvo tests explícitos"; conexión por variables de entorno, nunca hardcodeada. La sección debe actualizarse "cuando se defina el entorno (venv, requirements, DB)".
- `CLAUDE.md` (Reglas) — avisar antes de instalar dependencias nuevas; no leer/modificar `.env` ni commitear secretos; dinero en `Decimal`; no editar migraciones aplicadas; una rama y un PR por task.
- `docs/architecture/ddd.md:830-875` (sección 12) — estructura sugerida: `backend/manage.py`, `backend/config/{settings/, urls.py, wsgi.py}`, `backend/modules/{catalog,customers,sales,expenses,reporting}/` (cada uno con `domain/ application/ infrastructure/ api/`) y `backend/shared/domain/`.
- `docs/architecture/ddd.md:80` — "No todos los módulos necesitan todas estas carpetas desde el primer día"; `CLAUDE.md` indica crear carpetas solo cuando hagan falta.
- `docs/architecture/ddd.md:914-974` (sección 14) — endpoints REST bajo prefijo `/api/` (products, customers, orders, expenses, expense-categories, reports/*).
- Entorno local: Python 3.12.3, pip 24.0; el Python global ya tiene `Django 4.2.1`, `djangorestframework 3.14.0`, `django-environ 0.10.0`, `gunicorn 20.1.0` y `virtualenv`. No hay `psycopg` instalado ni venv del proyecto.
- Este worktree se creó desde el commit `38491f2` ("first commit"), anterior a `CLAUDE.md` y `docs/`; se avanzó con fast-forward a `main` (`466c871`) para disponer de ellos.
- `docs/tasks/` solo contenía `.gitkeep`; no hay tasks previos ni colisión de slug.

### Hipótesis / supuestos no confirmados
- Se asume que "inicializar" significa solo el esqueleto (proyecto, settings, URL raíz bajo `/api/`, DRF configurado, conexión PostgreSQL por entorno, `manage.py check` y `test` funcionando), sin implementar ningún módulo de negocio. No confirmado con el usuario.
- Se asume Django de la serie LTS vigente y no la 4.2.1 global (la versión exacta no está decidida en ningún documento).
- No se sabe si hay una instancia de PostgreSQL local disponible para correr `migrate`; no se verificó.
- No se sabe si se requiere autenticación, CORS (frontend Angular en otro origen), Docker o CI desde el inicio; ningún documento lo define.
- Gestor de dependencias/entorno (venv + `requirements.txt` vs. poetry/uv) no definido.

### Módulos y dependencias relacionadas
- Backend: ninguno existente. Contexto futuro: `modules/{catalog,customers,sales,expenses,reporting}` y `shared/domain` (`ddd.md` sección 12).
- Frontend: `frontend/panel_admin/` (Angular 21) consumirá la API `/api/...`; no hay servicio ni configuración de URL de API revisada en esta investigación.
- Skills `delivery-*` asumen `python manage.py test` ejecutado desde `backend/` (`delivery-engineer`, `delivery-review`) y herramientas como `bandit` en review.

### Implementaciones similares existentes
Ninguna en el repo (no hay código backend). La única referencia es la estructura propuesta en `docs/architecture/ddd.md`. Nota: las skills mencionan `praxsa_manager/` en algún texto heredado; no corresponde a este repo (ruta real: `backend/`).

### Comportamiento actual
No hay backend ejecutable. Ningún comando de `CLAUDE.md:15` funciona hoy.

### Restricciones
- PostgreSQL obligatorio; configuración por variables de entorno; sin secretos en el repo ni lectura de `.env` (`CLAUDE.md`).
- Avisar antes de instalar dependencias (`pip`).
- Estructura de carpetas alineada a `ddd.md` sección 12, sin crear módulos/capas vacíos innecesarios.
- Cambios acotados y un único PR en rama `task/TASK-<slug>`; base `main`.
- Actualizar la sección "Comandos" de `CLAUDE.md` con el entorno definido.

### Riesgos identificados
- Decisiones de base con efecto duradero aún sin tomar: versión de Django, layout de `settings/` (base/dev/prod/test), manejo de variables de entorno (`django-environ` ya está en el Python global, pero no se decidió), gestor de dependencias, modelo de usuario (`AUTH_USER_MODEL` es costoso de cambiar tras la primera migración), zona horaria/idioma/moneda.
- Si se corre `migrate` sin decidir el modelo de usuario, se fija el esquema inicial de `auth`.
- Sin PostgreSQL local disponible, la verificación se limitaría a `check`/tests con una configuración alternativa, en tensión con la regla "no SQLite salvo tests explícitos".
- Dependencias globales de Python con versiones distintas a las del proyecto pueden contaminar la verificación si no se usa un venv aislado.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — Es la creación del backend completo: estructura del monolito modular, configuración de base de datos (PostgreSQL), autenticación (`AUTH_USER_MODEL`) y convenciones de settings/entorno que condicionan todos los módulos futuros. Se cumplen varios indicadores (cambio estructural, nuevo módulo/bounded context base, base de datos, posible autenticación, infraestructura) y hay decisiones difíciles de revertir.

### Diseño requerido
**NO** — Es una tarea puramente de backend/infraestructura sin superficie de UI.

## Diseño
_No aplica_

## Arquitectura
- [ADR-inicializar-backend-django-stack-y-estructura](../adr/ADR-inicializar-backend-django-stack-y-estructura.md) — Django 5.2 LTS + DRF, venv + requirements, `django-environ`, settings por entorno, PostgreSQL, layout `config/ modules/ shared/`, `/api/health/`.
- [ADR-inicializar-backend-django-modelo-usuario](../adr/ADR-inicializar-backend-django-modelo-usuario.md) — `AUTH_USER_MODEL` propio (`modules/accounts`) antes del primer `migrate`; DRF deniega por defecto; auth de API diferida.

## Plan
[PLAN-2026-10-05-inicializar-backend-django](../plans/PLAN-2026-10-05-inicializar-backend-django.md) — v1

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
