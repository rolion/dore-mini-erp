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
