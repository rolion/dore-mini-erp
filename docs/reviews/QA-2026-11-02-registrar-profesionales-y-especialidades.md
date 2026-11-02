# Quality Gate — registrar profesionales y especialidades

**Estado:** PASS.
**Código revisado:** c471e4c; diff `origin/main...HEAD`, con backend inalterado desde e91f7ee.
**Plan:** PLAN-2026-11-02-registrar-profesionales-y-especialidades v3, COMPLETO, READY.
**Entrada:** TASK en REVIEW.

Revisión independiente desde TASK, PLAN, ADR, DDR, CLAUDE.md, DDD, sistema de diseño y diff real. El revisor no implementó producto ni cambió pruebas. Por limitación de aprobación del subagente, el agente principal transportará la ejecución autorizada de comandos pendientes; el revisor evaluará sus logs independientemente. No se atribuyen como ejecutados comandos todavía pendientes.

## Historial de ejecución y evidencia literal

Desde frontend/panel_admin se ejecutó `npm run lint; npm audit --offline; & E:/dore-mini-erp/backend/.venv/Scripts/python.exe -m pip show bandit coverage ruff flake8 mypy; rg --files -g '*ruff*' -g '*flake8*' -g '*mypy*' -g 'pyproject.toml' -g '*coverage*' -g 'setup.cfg'`.

```text
> oreva@12.0.0 lint
> ng lint

Linting "oreva"...
All files pass linting.
found 0 vulnerabilities
WARNING: Package(s) not found: coverage, flake8, mypy, ruff
Name: bandit
Version: 1.9.4
Location: E:\dore-mini-erp\backend\.venv\Lib\site-packages
```

Lint y audit offline: PASS de esos comandos sobre versión anterior a los ajustes visuales finales. Audit offline tiene alcance de caché local; no equivale a verificar advisories nuevos online. El comando agrupado terminó exit 1 por herramientas ausentes/búsqueda sin coincidencias; no confundir con fallo de lint. No se instaló ninguna dependencia.

Backend: `DJANGO_SETTINGS_MODULE=config.settings.test`, `DATABASE_URL=postgres://personnel_test@127.0.0.1:5546/postgres`, `TEST_DATABASE_NAME=test_personnel_review`, Python existente; execute_from_command_line con `test modules.personnel modules.modularity modules.accounts.tests modules.accounts.test_guards modules.sales.tests.test_boundaries --noinput` y plantilla personnel_template.

```text
Found 157 test(s).
Creating test database for alias 'default'...
django.db.utils.OperationalError: connection failed: connection to server at "127.0.0.1", port 5546 failed: Permission denied (0x0000271D/10013)
```

Resultado: NO EJECUTADO por sandbox; solicitudes escaladas abortadas esperando aprobación. No es fallo funcional demostrado.

Frontend anterior: `node node_modules/@angular/cli/bin/ng.js test --watch=false --browsers=ChromeHeadless --preserve-symlinks --code-coverage --include='src/app/features/personnel/**/*.spec.ts' --include='src/app/layout/sidebar/**/*.spec.ts' --include='src/app/core/guards/**/*.spec.ts'`.

```text
> Building...
```

Sesión 91988 recuperada terminó exit 1 sin salida adicional. No hay resultado de pruebas ni cobertura verificable; requiere ejecución final.

`git diff --check origin/main...HEAD`: exit 0, sin salida. PASS.

## Revisión estática

AC-01/02: entidades validan nombre, longitudes y correo; campos opcionales vacíos, PATCH conserva omitidos; asociaciones deduplicadas y referencias existentes verificadas en empresa. Especialidades inactivas siguen consultables. Sin DELETE.

AC-03/06: company_id se deriva de sesión. Repositorio filtra empresa en lectura/escritura y validación de especialidades; directorio compartido filtra empresa en selector/exists, devuelve solo id/name. Ningún import accounts en negocio. Gate personnel y permiso global existentes; rutas directas tienen moduleGuard y guard admin; menú Personal filtra rol admin.

AC-04: paginación servidor máxima100; búsqueda/estado/especialidad, orden estable name/id. prefetch_related('specialties') evita N+1 en ambos campos serializados. Sin resolución de usuarios por fila en lista.

AC-05/08: autoría histórica separada de user_id; estado por métodos de dominio; save+M2M en atomic. Constraint personnel_user_unique permite NULL y bloquea vínculos duplicados incluso inactivos; captura IntegrityError después del rollback y produce error user_id. Prueba concurrente real incluida, pendiente de ejecución independiente. Sin consulta Agenda/Sucursales ni modificación de permisos.

Scope conforme al PLAN v3; ajustes dark y responsive documentados. Migración aditiva sin editar migraciones anteriores. Domain/application no importan Django; puerto de identidad y composición externa. No dependencias/lockfiles añadidos. No archivo .env incluido ni leído. Sin indicios de secretos en el diff de código revisado.

## Visual / AC-07

Se leyó [VIS](VIS-2026-11-02-registrar-profesionales-y-especialidades.md), que registra navegación real del agente principal en 390/1440 y claro/oscuro, teclado, alta mínima, asociación/vínculo y desactivación preservando autoría. No se simula E2E: PLAN dice expresamente NO.

Revisor abrió desktop-dark-form.jpg: chip legible y estructura conforme. Al abrir mobile-dark-list.jpg observó controles extremadamente estrechos y aviso letra por línea; la captura no demuestra el resultado responsive descrito en VIS. Se solicitó al principal comprobar/reemplazar evidencia final. Visual pendiente hasta resolver esa discrepancia.

Plantillas, clases existentes, labels, iconos aria-hidden, acciones con title/aria-label, español, fechas y estados de carga/vacío/error/éxito presentes en código. Hallazgo Low: [REV-01](REV-2026-11-02-registrar-profesionales-y-especialidades-01.md), Guardar no deshabilita por form.invalid.

## Pendientes del informe parcial (resueltos al cierre)

- Backend157 y migraciones accounts aisladas con PostgreSQL.
- Frontend final personnel y regresión sidebar/guards con cobertura; lint final y build producción.
- Bandit disponible y audit online si disponible.
- Cobertura backend: coverage.py ausente; terminar evaluación manual de ramas/tests sin atribuir porcentaje.
- Resolver discrepancia captura móvil y comprobar evidencias visuales finales.

No se declara PASS mientras haya comprobaciones aplicables pendientes. No hay hallazgo High/Critical confirmado en revisión estática.

## Ejecución transportada evaluada independientemente

Se leyeron run-gate.ps1, summary.json y logs frescos en `C:/Users/Lion/.codex/visualizations/2026/11/02/01a19c3b-0447-7862-9e2b-d58b4cbd64f2/personnel-gate/`. Todos los exit codes registrados son 0. Son resultados reales sobre e91f7ee, no inferencias del código.

Backend: comando Python descrito arriba, usando plantilla PostgreSQL personnel_template.

```text
Ran 157 tests in 6.470s
OK
Found 157 test(s).
System check identified no issues (0 silenced).
```

Migraciones Acceso en otra base `test_personnel_review_migrations`: mismo Python/test settings, `execute_from_command_line(['manage.py','test','modules.accounts.test_migrations','--noinput'])`.

```text
Ran 2 tests in 3.215s
OK
Found 2 test(s).
System check identified no issues (0 silenced).
```

`python manage.py makemigrations --check --dry-run`:

```text
No changes detected
```

`python -m bandit -r modules/personnel shared/identity.py`:

```text
Test results:
    No issues identified.
Code scanned:
    Total lines of code: 578
    Total lines skipped (#nosec): 0
Files skipped (0):
```

Bandit se aplica al backend nuevo/modificado, no a deuda ajena. Backend tests/migración/seguridad: PASS.

Frontend: `node node_modules/@angular/cli/bin/ng.js test --watch=false --browsers=ChromeHeadless --preserve-symlinks --code-coverage --include='src/app/features/personnel/**/*.spec.ts' --include='src/app/layout/sidebar/sidebar.component.spec.ts' --include='src/app/core/guard/*.spec.ts' --include='src/app/core/service/modules.service.spec.ts'`.

```text
TOTAL: 34 SUCCESS
Statements   : 63.08% ( 323/512 )
Branches     : 46.31% ( 88/190 )
Functions    : 53.84% ( 105/195 )
Lines        : 65.51% ( 285/435 )
```

Cobertura del conjunto ejecutado, incluida regresión; no representa todo el frontend. Warnings de icono Feather en harness no fallan tests. No umbral de cobertura requerido por PLAN. Coverage.py ausente: revisión manual identifica tests para validación de campos, edición inválida sin mutación, opcionales, normalización, ambos estados; API mínima/parcial, relaciones ajenas, filtros, permisos/gate, autoría, error constraint y concurrencia. No se atribuye cobertura porcentual backend ni cobertura exhaustiva de ramas internas de infraestructura/excepciones no reproducidas.

`node node_modules/@angular/cli/bin/ng.js build --configuration production --preserve-symlinks`, con NG_BUILD_MAX_WORKERS=2 y NODE_OPTIONS=--max-old-space-size=4096:

```text
√ Building...
                      | Initial total      |   2.22 MB |               480.79 kB
Output location: C:\Users\Lion\.codex\worktrees\6cbe\dore-mini-erp\frontend\panel_admin\dist\oreva
```

Build producción: PASS, con warnings de selectores Sass de plantilla y dependencias existentes; sin error de compilación.

Lint final de e91f7ee: `npm.cmd run lint` → `All files pass linting.`. Audit: `npm.cmd audit --offline` → `found 0 vulnerabilities`. PASS con limitación offline explícita.

La captura mobile-dark-list fue reemplazada por captura del viewport real porque fullPage provocaba reflow durante captura. El revisor la reabrió y confirma controles/aviso legibles y tabla horizontal. Mobile-light-list, mobile-light-form, mobile-dark-form y mobile-light-detail también examinados y legibles. mobile-dark-detail todavía muestra reflow en el archivo; solicitado reemplazo de ese archivo. No se concluye fallo de producto por un fallo demostrado del mecanismo de captura.

Pendiente únicamente cierre visual dark-detail y frontend/lint/build posteriores a la corrección de REV-01 que prepara el agente principal. Backend sin cambio material: no repetir su gate.

## Cierre independiente sobre c471e4c

Se inspeccionó `git diff e91f7ee..HEAD -- frontend`: único cambio funcional es agregar form.invalid al botón Guardar; el test existente comprueba ambos estados. No cambios backend; su evidencia anterior sigue aplicando. REV-01 cerrado; ningún REV abierto.

Se leyeron run-frontend-final.ps1, summary-final.json, angular-final.log, build-final.log y lint-final.log. Repiten los comandos frontend de arriba sobre producto final. Evidencia literal:

```json
{
  "angular_final": 0,
  "build_final": 0,
  "lint_final": 0
}
```

```text
TOTAL: 34 SUCCESS
Statements   : 63.08% ( 323/512 )
Branches     : 46.31% ( 88/190 )
Functions    : 53.84% ( 105/195 )
Lines        : 65.51% ( 285/435 )
Output location: C:\Users\Lion\.codex\worktrees\6cbe\dore-mini-erp\frontend\panel_admin\dist\oreva
All files pass linting.
```

Revisor reabrió mobile-dark-detail.jpg definitiva: texto, campos, estado y autoría legibles; reflow de captura resuelto sin cambio funcional. También examinó capturas escritorio light/dark list y light detail, además de móvil/formularios antes descritos. Con inspección real/teclado registrada en VIS y las imágenes finales, checklist visual aplicable queda verificada: plantillas, tokens/clases existentes, reutilización, estados, accesibilidad mínima, 390/1440 claro/oscuro, español y fechas. Sin bloqueo visual abierto.

`git diff --check origin/main...HEAD` final: exit 0, sin salida. `git status --short` al cierre del review mostró solo los dos informes QA/REV nuevos; sin temporales, logs de pruebas ni builds para publicar. No .env/credenciales leídos ni añadidos.

| Verificación | Resultado final |
|---|---|
| Backend y regresión, PostgreSQL real | PASS, 157 tests |
| Migraciones Acceso aisladas | PASS, 2 tests |
| Migración pendiente no generada | PASS, No changes detected |
| Angular Personal y regresión sidebar/guard/modules | PASS, 34 tests con cobertura |
| Lint frontend | PASS |
| Build producción | PASS |
| Seguridad código backend afectado, Bandit | PASS, 0 issues |
| Audit dependencias offline | PASS, 0 vulnerabilities; alcance caché |
| Arquitectura/aislamiento/concurrencia/autoría | PASS por código y pruebas ejecutadas |
| Visual y teclado | PASS, VIS y capturas finales |
| E2E | No aplicable, decisión explícita PLAN |

**Veredicto final: PASS.** AC-01 a AC-08 quedan respaldados por pruebas API/dominio/componentes/guard y evidencia visual según mapeo del PLAN. No quedan verificaciones aplicables pendientes. Limitaciones declaradas: audit offline, cobertura backend revisada manualmente sin porcentaje y cobertura frontend del conjunto acotado; sin umbral requerido. No se bloquea por warnings existentes de plantilla. Cambios sensibles: nuevo esquema de base de datos y autorización de módulo conforme ADR; el merge requiere aprobación humana. Este informe no hace merge, push ni modifica TASK/PR.
