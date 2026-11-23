# TASK-actualizar-dependencias-vulnerables-backend: Corregir vulnerabilidades de dependencias del backend

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** NO
**Rama:** task/TASK-actualizar-dependencias-vulnerables-backend
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/115

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-23 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-23 | INVESTIGATION → PLANNING | Veredicto NEEDS_PLAN, diseño NO | delivery-start |
| 2026-11-23 | PLANNING → ENGINEERING | Plan v1 READY, PR abierto | delivery-start |
| 2026-11-23 | ENGINEERING → REVIEW | Implementación completa | delivery-build |

## Investigación

### Requerimiento
«En DigitalOcean he estado recibiendo alertas de vulnerabilidades en muchos lenguajes y frameworks. Necesitamos revisar si hay alguna vulnerabilidad para nuestra versión de Python y Django y arreglarla sin introducir bugs al backend.»

### Hechos encontrados
Auditoría hecha el 2026-11-23 consultando la base OSV (api.osv.dev, ecosistema PyPI) contra cada paquete resuelto de `requirements/production.txt` (incluidas dependencias transitivas), sin instalar nada.

- `backend/requirements/base.txt:1` — `Django==5.2.17`: **sin avisos en OSV**. Pero PyPI ya publica 5.2.18 y 5.2.19 (misma serie LTS 5.2); los parches de seguridad de Django a veces tardan en aparecer en OSV.
- `backend/requirements/base.txt:2` — `djangorestframework==3.18.1`: **3 avisos, todos corregidos en 3.18.2** (última: 3.18.3):
  - GHSA-33wh-fxxf-88vv / CVE-2026-114138 — cabecera `Accept` con muchos parámetros entrecomillados grandes consume ~19 s de CPU por petición, sin autenticación (DoS; CVSS A:H).
  - GHSA-3547-9m27-7rxg / CVE-2026-114136 — `JSONParser` aplica el codec nombrado en el `charset` del `Content-Type`; evade `DATA_UPLOAD_MAX_MEMORY_SIZE` y agota memoria, sin autenticación (DoS).
  - GHSA-xw6w-gcfp-cf8m / CVE-2026-114137 — `TokenProxy.delete()` no revoca nada pero informa éxito (afecta a quien borre tokens desde el admin de Django con `TokenProxy`).
- `backend/requirements/base.txt:3-5`, `production.txt:2` — `psycopg 3.3.6`, `django-environ 0.14.0`, `openpyxl 3.1.5`, `gunicorn 26.2.0`: sin avisos. Transitivas (`asgiref 3.13.0`, `sqlparse 0.6.1`, `tzdata`, `typing_extensions`, `et_xmlfile`): sin avisos.
- `backend/Dockerfile:1` — `python:3.12-slim` (etiqueta flotante) y el deploy construye con `docker build --pull` (`.github/workflows/deploy.yml`), así que cada despliegue toma el último parche 3.12.x. Python 3.12 sigue con soporte de seguridad. Python no necesita cambio de versión.
- `backend/modules/accounts/api/views.py:4,71` — el logout usa `Token.delete()` (modelo concreto), **no** `TokenProxy`; el aviso de `TokenProxy` no afecta al flujo de API, solo al admin.
- `backend/config/settings/base.py:93-112` — `TokenAuthentication` + `SessionAuthentication`, `JSONRenderer` único, sin parsers personalizados: el `JSONParser` por defecto y la negociación de `Accept` quedan expuestos a los dos avisos de DoS en todos los endpoints.
- No existe `.github/dependabot.yml` ni ningún job de auditoría en CI (`.github/workflows/` solo tiene `deploy.yml`).
- El frontend (npm) queda fuera: la petición habla de Python y Django.

### Hipótesis / supuestos no confirmados
- Las alertas de DigitalOcean (probablemente de la imagen/App Platform) pueden incluir paquetes del SO de la imagen base o del frontend que no se ven en `requirements`. No se ve el panel de DO; se asume que las alertas relevantes al backend son las de DRF.
- Se asume que 5.2.18/5.2.19 son parches menores compatibles (política de Django: sin cambios incompatibles en parches).

### Módulos y dependencias relacionadas
Solo `backend/requirements/*.txt`. Toda la API usa DRF (`modules/*/api/`).

### Implementaciones similares existentes
Pines exactos con `==` en `requirements/`; se mantiene el estilo.

### Comportamiento actual
Producción corre DRF 3.18.1 con los dos DoS sin autenticación explotables hoy.

### Restricciones
`CLAUDE.md`: avisar antes de instalar dependencias nuevas (aquí no se añade ninguna, solo se suben versiones pinneadas); no tocar `.env`; cada push a `main` despliega a producción.

### Riesgos identificados
- Regresión por cambio de versión de DRF/Django: mitigado con la suite completa (`python manage.py test`), lint y subidas solo de parche/menor dentro de la misma serie.
- DRF 3.18.2/3.18.3 pueden tocar parsers/negociación: revisar notas de versión y que los tests de API sigan pasando.

### Veredicto de complejidad
**NEEDS_PLAN** — cambio acotado de versiones pinneadas, sin decisión arquitectónica nueva, pero afecta a todos los endpoints y se despliega a producción, por lo que merece plan y verificación completa.

### Diseño requerido
**NO** — solo backend, sin cambios visibles.

## Diseño
No aplica.

## Arquitectura
No aplica según veredicto.

## Plan
`docs/plans/PLAN-2026-11-23-actualizar-dependencias-vulnerables-backend.md` (v1, COMPACTO).

## Implementación
Cambio solo en `backend/requirements/base.txt`: `Django 5.2.17 → 5.2.19`, `djangorestframework 3.18.1 → 3.18.3`, `psycopg[binary] 3.3.6 → 3.3.9`. Sin dependencias nuevas, sin cambios de código ni migraciones.

Verificación propia (no es el Quality Gate), con PostgreSQL 16 temporal y venv fuera del repo:
- AC-01: pines actualizados.
- AC-02: consulta OSV de los 12 paquetes resueltos de `production.txt`: 0 avisos (antes: 3 en DRF).
- AC-03: `python manage.py test` → 2362 tests, OK (en serie; `--parallel` no funciona en Windows).
- AC-04: `makemigrations --check` sin cambios; `check --deploy` sin errores (los 5 avisos W* vienen de `config.settings.test`, no de producción).
- AC-05: solo `.txt`, nada que lintear.

Desviaciones del plan: ninguna. Deuda/seguimiento sugerido: añadir Dependabot o un job de auditoría (pip-audit) en CI; revisar las alertas de DigitalOcean que no sean de Python (imagen base, npm).

## Review
_Pendiente_

## Publicación
_Pendiente_
