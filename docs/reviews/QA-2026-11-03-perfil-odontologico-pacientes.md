# Quality Gate — perfil odontológico de pacientes

**Ciclo 2 · 2026-11-03 · PASS**

**Código revisado:** 706ae8f · **Plan:** v1, COMPLETO, READY · **PR:** #47

El diff desde b0086a9 corrige REV-01. Los diccionarios inglés y alemán incluyen ambos títulos de Odontología. La regresión del menú verifica 10 entradas, 27 títulos, la ruta de Pacientes y la visibilidad con el módulo habilitado y deshabilitado. Conserva las comprobaciones de los demás módulos. El diff restante es documentación de la entrega. La Specification, el backend y el manifiesto de dependencias son idénticos a los ya revisados.

El Quality Gate independiente contrastó el diff y leyó los logs de la ejecución del orquestador en `C:/Users/Lion/AppData/Local/Temp/pb-odo-001-gate2-*.log`. Los tres comandos terminaron con código 0.

```text
node node_modules/@angular/cli/bin/ng.js test --watch=false --browsers=ChromeHeadless --code-coverage --preserve-symlinks
TOTAL: 1083 SUCCESS
Statements   : 87.06% ( 5673/6516 )
Branches     : 79.78% ( 1961/2458 )
Functions    : 81.5% ( 1736/2130 )
Lines        : 87.61% ( 5138/5864 )

node node_modules/@angular/cli/bin/ng.js lint
Linting "oreva"...
All files pass linting.

node node_modules/@angular/cli/bin/ng.js build --preserve-symlinks
Application bundle generation complete. [19.198 seconds] - 2026-11-03T12:41:15.397Z
```

El build reporta deprecaciones de Sass y 23 reglas omitidas por errores de selector. El diff del ciclo 2 no toca estilos. `git diff --check origin/main...HEAD` terminó con código 0 y el árbol estaba limpio antes de añadir el informe.

Se conserva la evidencia del [ciclo 1](QA-2026-11-02-perfil-odontologico-pacientes.md) para el backend idéntico: PostgreSQL, `Ran 250 tests in 10.928s` y `OK`. Bandit registró `No issues identified.` en 1122 líneas. La cobertura backend se revisó manualmente y las ramas sin prueba directa están descritas en ese informe. `npm audit --json` terminó con código 0 y el informe `pb-odo-001-gate-audit.json` registra:

```json
"vulnerabilities": {
  "info": 0,
  "low": 0,
  "moderate": 0,
  "high": 0,
  "critical": 0,
  "total": 0
}
```

La matriz AC-01 a AC-08 del ciclo 1 se mantiene y el suite completo confirma la corrección de AC-07. Se mantiene la [evidencia visual](../tests/VISUAL-2026-11-02-perfil-odontologico-pacientes.md) del recorrido en español a 390 y 1440 px en claro y oscuro. La aceptación del diálogo de archivo quedó sin verificar en navegador por la limitación del adaptador. La transición está cubierta por API y componentes. El plan no exige E2E automatizado.

[REV-01](REV-2026-11-02-perfil-odontologico-pacientes-01.md) queda resuelto y no hay hallazgos abiertos. La revisión técnica queda aprobada. La aprobación humana del PR sigue pendiente por los cambios de autorización, arquitectura y base de datos.

## Ciclo 3 · Refactor de interfaz · PASS

Se contrastó el diff del PR contra `origin/main` y el refactor contra `e7a8afd`. El plan v1, COMPLETO, registra el ajuste de alcance y el DDR incorpora la ficha en tarjetas, el historial desplegable y el alta en modal. La Specification y el backend son idénticos al ciclo 2. El modal reutiliza el formulario compartido de Clientes y se mantienen el permiso clínico, los guardados independientes y los contratos de API. El diff no incorpora dependencias ni credenciales.

El revisor leyó los logs de ejecución del orquestador `patient-ui-release-*` para Angular y `patient-ui-final-*` para backend, Bandit y npm audit. Comprobó `git diff --check origin/main` con código 0.

Para el backend se ejecutó `python manage.py test modules.dentistry modules.customers modules.accounts modules.modularity modules.sales.tests.test_boundaries --noinput` con `DJANGO_SETTINGS_MODULE=config.settings.test` y PostgreSQL temporal en `127.0.0.1:55433`. Para seguridad se ejecutó `bandit -r modules/dentistry modules/customers config/permissions.py modules/accounts/api/permissions.py -x tests -f txt -o <log>` desde `backend/`.

Desde `frontend/panel_admin/` se ejecutó lo siguiente.

```text
node node_modules/@angular/cli/bin/ng.js test --watch=false --browsers=ChromeHeadless --code-coverage --preserve-symlinks
node node_modules/@angular/cli/bin/ng.js lint
node node_modules/@angular/cli/bin/ng.js build --preserve-symlinks
npm audit --json
```

```text
Chrome Headless 156.0.0.0 (Windows 10)
TOTAL: 1084 SUCCESS
Statements   : 86.94% ( 5694/6549 )
Branches     : 79.57% ( 1971/2477 )
Functions    : 81.42% ( 1740/2137 )
Lines        : 87.55% ( 5163/5897 )

Linting "oreva"...
All files pass linting.

Application bundle generation complete. [17.936 seconds] - 2026-11-03T13:50:44.932Z

Ran 250 tests in 11.365s
OK
System check identified no issues (0 silenced).

Test results:
    No issues identified.
Total lines of code: 1122
```

`npm audit --json` registró cero vulnerabilidades en todos los niveles. El build registró deprecaciones de Sass y 23 reglas omitidas por errores de selector, advertencias ya presentes en el ciclo 2. La cobertura backend se conserva como revisión manual del ciclo 1. El plan excluye E2E automatizado.

### Hallazgos resueltos

- [REV-01](REV-2026-11-03-perfil-odontologico-pacientes-01.md) · AC-05. El historial compara los valores crudos. La prueba nueva cubre el texto literal «No informado».
- [REV-02](REV-2026-11-03-perfil-odontologico-pacientes-02.md) · AC-08. El modal permite repetir la última búsqueda tras un error.
- [REV-03](REV-2026-11-03-perfil-odontologico-pacientes-03.md) · AC-07. El enlace directo restaura los filtros antes de abrir el modal.
- [REV-04](REV-2026-11-03-perfil-odontologico-pacientes-04.md) · Plan. El ajuste registra el alcance del formulario compartido de Clientes.
- [REV-05](REV-2026-11-03-perfil-odontologico-pacientes-05.md) · Accesibilidad. El botón de cierre incluye el título exigido por el sistema de diseño.
- [REV-06](REV-2026-11-03-perfil-odontologico-pacientes-06.md) · Accesibilidad. Las etiquetas de estado emplean los colores de texto asociados a sus fondos.

### Verificación visual

El orquestador verificó la ficha y el modal en navegador con el build de producción. Revisó la ficha a 390 y 1440 px en claro y oscuro, con tarjetas apiladas en móvil y documento de 375 px a 390 px de viewport. Verificó la visibilidad dinámica del responsable y el historial desplegable. En la revisión final comprobó el título de ficha en tema oscuro, con color calculado `rgb(206, 212, 218)`, y el botón de archivo en claro, con `rgb(102, 77, 3)`. El modal oscuro final midió 374 px a 390 px y se comprobaron las acciones de cierre y creación de cliente. Se conservan las pruebas API y de componente para la transición de archivo y reactivación.

La revisión independiente da **PASS** al estado probado. El PR queda pendiente de aprobación humana por los cambios de autorización clínica, arquitectura y base de datos de la entrega.
