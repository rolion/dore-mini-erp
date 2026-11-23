# PLAN-2026-11-23-actualizar-dependencias-vulnerables-backend (v1)

**Task:** TASK-actualizar-dependencias-vulnerables-backend · **Modo:** COMPACTO · **Specification readiness:** READY
**DDRs / ADRs:** Ninguno

## Objective
Eliminar las vulnerabilidades conocidas de las dependencias Python del backend (DRF 3.18.1 con 3 avisos) y tomar los parches vigentes de Django 5.2, sin cambiar comportamiento funcional ni introducir regresiones.

# Specification
- **Expected behavior:** el backend funciona igual que hoy, pero con versiones sin avisos conocidos. Python se mantiene en 3.12 (la imagen ya toma el último parche en cada build).
- **Acceptance criteria:**
  - AC-01: `djangorestframework` pinneado a una versión ≥ 3.18.2 (objetivo 3.18.3); `Django` a la última 5.2.x (objetivo 5.2.19); `psycopg[binary]` al último parche 3.3.x (objetivo 3.3.9).
  - AC-02: una consulta a OSV de todos los paquetes resueltos de `requirements/production.txt` devuelve 0 avisos.
  - AC-03: la suite completa `python manage.py test` pasa con `config.settings.test`, igual que en `main`.
  - AC-04: `python manage.py check --deploy` y `makemigrations --check --dry-run` no reportan problemas nuevos (el upgrade no genera migraciones).
  - AC-05: `ruff`/`flake8` sin avisos en lo cambiado (solo `.txt`, nada que lintear).
- **Edge/error cases:** si algún test falla por el upgrade, se corrige la causa o se fija la versión previa de ese paquete; no se desactivan tests. Si 5.2.19 o DRF 3.18.3 rompen algo, se baja a la versión mínima segura (DRF 3.18.2).
- **Out of scope:** `gunicorn` (26.2.0, sin avisos; 27.x es salto mayor), Django 6.x, frontend/npm, paquetes del SO de la imagen, alertas de DigitalOcean no atribuibles a Python, añadir Dependabot/auditoría en CI (se sugiere como seguimiento).

# Test Specification
- AC-01/AC-02: script de auditoría OSV contra los paquetes resueltos (`pip install --dry-run --report`), resultado registrado en el TASK.
- AC-03: suite completa de Django (unit + integración de API existentes), que ejercita DRF en todos los módulos, login/logout con token incluido.
- AC-04: `check --deploy` y `makemigrations --check`.
- **E2E: NO** — no hay cambio de flujo de usuario; la suite de API cubre las rutas.

# Implementation Plan
- **Files affected:** backend: `backend/requirements/base.txt`. Frontend: ninguno.
- **Steps:**
  1. Subir versiones en `base.txt` (AC-01).
  2. Crear venv fuera del repo, instalar `requirements/dev.txt` y correr la suite completa contra PostgreSQL de pruebas (AC-03); leer las notas de versión de DRF 3.18.2/3.18.3 y Django 5.2.18/5.2.19 por cambios de comportamiento.
  3. Correr `check --deploy`, `makemigrations --check` (AC-04) y la auditoría OSV (AC-02).
  4. Registrar resultados en el TASK.
- **Risks:** regresión en parsers/negociación de DRF (mitigado por la suite). Sin dependencias nuevas, solo cambios de versión. Rollback: revertir el commit; el deploy reconstruye la imagen con el pin anterior.
