# TASK-configurar-dependabot-actualizaciones: Dependabot para detectar dependencias vulnerables o desactualizadas

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** NO
**Rama:** task/TASK-configurar-dependabot-actualizaciones
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/117

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-23 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-23 | INVESTIGATION → PLANNING | Veredicto NEEDS_PLAN, diseño NO | delivery-start |
| 2026-11-23 | PLANNING → ENGINEERING | Plan v1 READY, PR abierto | delivery-start |
| 2026-11-23 | ENGINEERING → REVIEW | Implementación completa | delivery-build |
| 2026-11-23 | REVIEW → PUBLISH | Quality Gate PASS | delivery-publish |

## Investigación

### Requerimiento
«Dependabot en CI», como seguimiento de TASK-actualizar-dependencias-vulnerables-backend (PR #115): agregar `.github/dependabot.yml` para detectar y proponer actualizaciones de seguridad de las dependencias (pip en el backend, npm en `frontend/panel_admin`, imágenes Docker de backend y frontend, GitHub Actions), evitando enterarse solo por las alertas de DigitalOcean. Debe agrupar parches/menores para no inundar de PRs, no tocar el flujo de deploy y respetar una rama y un PR por task.

### Hechos encontrados
- `.github/` solo contiene `workflows/deploy.yml`; no existe `dependabot.yml` ni ningún job de auditoría.
- `.github/workflows/deploy.yml:51` — única Action usada: `actions/checkout@v4`.
- `backend/requirements/{base,dev,production}.txt` — dependencias Python con pines exactos (`==`); `production.txt` y `dev.txt` incluyen `-r base.txt`.
- `backend/Dockerfile:1` — `FROM python:3.12-slim`. `frontend/panel_admin/Dockerfile:1,12` — `node:22-alpine` (build) y `nginx:stable-alpine`.
- `frontend/panel_admin/package.json:15-19` — Angular `^21.0.8` (14 paquetes `@angular/*`); `package.json:94-97` — `overrides` de `glob` y `minimatch` apuntando a `file:tools/minimatch-compat`; `package-lock.json` versionado; `.npmrc` con `legacy-peer-deps=true`.
- `compose.yaml:5,40,52` — usa imágenes locales `pocketbiz-*`, sin imágenes de terceros (nada que vigilar ahí).
- `CLAUDE.md` — cada push a `main` despliega a producción; una rama y un PR por task; los PR de Dependabot se abren contra `main` y solo despliegan al mergearse (decisión humana).
- Las versiones de TASK-actualizar-dependencias-vulnerables-backend ya están subidas (Django 5.2.19, DRF 3.18.3): Django 5.2 es serie LTS y Python 3.12 / Node 22 son LTS.

### Hipótesis / supuestos no confirmados
- Dependabot **alerts** y **security updates** deben estar activados en los ajustes del repositorio de GitHub (Settings → Code security); un archivo no puede activarlos. Se asume que la persona administradora lo hace.
- `directory: "/backend"` basta para que Dependabot (pip) detecte `requirements/*.txt`; si no, se ajusta tras ver la primera ejecución.
- La zona horaria `America/La_Paz` es razonable (el proyecto usa prefijo telefónico 591 por defecto).

### Módulos y dependencias relacionadas
Solo configuración de repositorio (`.github/`); ningún código de producto.

### Implementaciones similares existentes
Ninguna.

### Comportamiento actual
Las vulnerabilidades de dependencias solo se descubren por alertas externas (DigitalOcean) o revisiones manuales; no hay PRs automáticos.

### Restricciones
No tocar `deploy.yml` ni el flujo de deploy; Dependabot no mergea nada. Sin dependencias nuevas en el proyecto.

### Riesgos identificados
- Ruido de PRs: mitigado con agrupación de minor/patch, límite de PRs abiertos y frecuencia semanal.
- Saltos de versión mayor de Angular/Django/Python/Node son migraciones deliberadas: se ignoran las majors de esos ecosistemas (las actualizaciones de **seguridad** de Dependabot no dependen de estas reglas `ignore` de versión de forma que impidan los parches de la misma serie).
- Un PR de Dependabot mergeado despliega a producción: la revisión humana y los tests siguen siendo la barrera (no hay CI de tests en PR hoy).

### Veredicto de complejidad
**NEEDS_PLAN** — un único archivo de configuración, sin decisión arquitectónica, pero toca la cadena de dependencias de producción y requiere decisiones de política (qué majors ignorar, agrupación).

### Diseño requerido
**NO** — sin interfaz.

## Diseño
No aplica.

## Arquitectura
No aplica según veredicto.

## Plan
`docs/plans/PLAN-2026-11-23-configurar-dependabot-actualizaciones.md` (v1, COMPACTO).

## Implementación
Se creó `.github/dependabot.yml` (AC-01..AC-04): pip `/backend`, npm `/frontend/panel_admin`, docker `/backend` y `/frontend/panel_admin`, github-actions `/`; semanal los lunes (`America/La_Paz`), límites de PRs 5/5/3/3/3, etiqueta `dependencies`, prefijo `chore(deps)`; minor+patch agrupados en pip, npm y Actions; ignora majors de Django, `@angular/*`, TypeScript, Node, y major+minor de la imagen `python` (se queda en 3.12; los parches 3.12.x llegan con `--pull` en cada build).
Verificación propia (AC-05): el archivo valida contra el JSON Schema de SchemaStore `dependabot-2.0` (0 errores, con `jsonschema` instalado solo en el venv temporal fuera del repo). Sin cambios en `deploy.yml` ni código de producto.
Desviaciones: ninguna. Acción humana pendiente: activar Dependabot alerts y security updates en Settings → Code security del repositorio; tras el merge, comprobar en Insights → Dependency graph → Dependabot que los 5 ecosistemas se leen sin error (en especial que `/backend` encuentre `requirements/*.txt`).

## Review
**Quality Gate: PASS** (subagente aislado, 2026-11-23), sin hallazgos. Alcance: solo `.github/dependabot.yml` + docs; `deploy.yml` intacto; sin secretos. AC-01..AC-04 verificados contra el YAML y los manifiestos existentes; ningún `ignore` bloquea parches de seguridad. AC-05: validación contra el JSON Schema `dependabot-2.0` con 0 errores. No verificable antes del merge: que GitHub acepte y ejecute la configuración.

## Publicación
PR #117 listo para aprobación humana; no se mergea. Pasos humanos: activar Dependabot alerts y security updates en Settings → Code security; tras el merge, revisar Insights → Dependency graph → Dependabot.
