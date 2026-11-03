# Quality Gate — perfil odontológico de pacientes

**Código revisado:** b0086a9 · **Plan:** v1, COMPLETO, READY · **Resultado ciclo 1:** FAIL.

Revisión independiente desde CLAUDE.md, delivery-publish, TASK en REVIEW, PLAN vigente, ADR, DDR, sistema de diseño, código y diff `origin/main...HEAD`. Sin asumir requisitos conversacionales. No se corrigió código, ni se modificó PR ni se hizo merge. El orquestador actuó también como runner por restricciones del sandbox; el revisor leyó los logs directamente. El primer intento backend ordinario falló por `Permission denied (0x0000271D/10013)` a 55433; el reintento escalado sí ejecutó los tests. No se usaron otras bases ni se instalaron dependencias.

## Hallazgos

[REV-01](REV-2026-11-02-perfil-odontologico-pacientes-01.md): **Medium / IMPLEMENTATION / AC-07**. Dos pruebas del sidebar fallan tras agregar Odontología: expectativas de estructura anteriores y claves nuevas sin traducción en en/de. No hay hallazgos High/Critical identificados. La regla de delivery-publish exige FAIL por cualquier test fallando sin autorización; procede delivery-build.

## Evidencia ejecutada

Logs en `C:/Users/Lion/AppData/Local/Temp/pb-odo-001-gate-*.log`, revisados directamente. Las siguientes salidas son extractos literales, sin convertir verificaciones pendientes en aprobadas.

Backend desde `backend/`, Python `E:/dore-mini-erp/backend/.venv/Scripts/python.exe`, `DJANGO_SETTINGS_MODULE=config.settings.test`, `DATABASE_URL=postgresql://taskuser@127.0.0.1:55433/postgres`, `TEST_DATABASE_NAME=test_pb_odo_001_gate`:

```text
manage.py test modules.dentistry modules.customers modules.accounts modules.modularity modules.sales.tests.test_boundaries --noinput
Ran 250 tests in 10.928s
OK
Found 250 test(s).
System check identified no issues (0 silenced).
```

Frontend desde `frontend/panel_admin/`:

```text
node node_modules/@angular/cli/bin/ng.js test --watch=false --browsers=ChromeHeadless --code-coverage --preserve-symlinks
TOTAL: 2 FAILED, 1081 SUCCESS
Statements   : 87.06% ( 5673/6516 )
Branches     : 79.78% ( 1961/2458 )
Functions    : 81.5% ( 1736/2130 )
Lines        : 87.61% ( 5138/5864 )

node node_modules/@angular/cli/bin/ng.js lint
Linting "oreva"...
All files pass linting.
```

Bandit sobre Dentistry y Customers, con exclusión de tests, log leído:

```text
Test results:
    No issues identified.
Total lines of code: 1122
Total lines skipped (#nosec): 0
Files skipped (0):
```

`git diff --check origin/main...HEAD`: exit 0, sin salida. Build final y npm audit pendientes de lectura al emitir este ciclo fallido; deben registrarse antes de un PASS. No hay ruff/flake8/mypy configurados entre los archivos de configuración localizados. Coverage.py no está instalado: no se afirma cobertura backend numérica. No hay dependencias nuevas.

## Conformidad por criterio

| Criterio | Implementación y evidencia revisada |
|---|---|
| AC-01 | Creación conserva UUID Customer, fachada acotada, restricción SQL empresa/cliente; test concurrente espera 201/409 con un perfil/un evento; componentes selección/alta rápida/conflicto. |
| AC-02 | Cinco textos opcionales, strip/límite 4000 y vacío desconocido; dominio, API y formulario asociados; sin ausencia automática. |
| AC-03 | CompanyClinicalPermission compone empresa activa, rol, módulos y política clínica. Todas las vistas clínicas heredan ClinicalView. Tests denegación política, módulos, rol inválido, empresa ausente/inactiva, anónimo, datos ajenos y guard Angular. |
| AC-04 | Dominio demografía con fecha inyectada; tests desconocido, menor, aniversario18, futuro, contacto parcial,29/02, PATCH parcial y rollback. Validación frontend y preservación del borrador. |
| AC-05 | Creación y cambios clínicos atómicos; actualizaciones bloquean fila. Demografía bloquea Customer incluso en primera escritura. Snapshots antes/después, actor autenticado, no-op y rollback probados. Historial GET paginado; sin escritura/borrado público. |
| AC-06 | Archivo conserva clínica, UUID, historia y estado del Customer. Unicidad también archivado. PATCH clínico409 y reactivación probados. |
| AC-07 | Listado paginado en servidor, filtros URL conservados, guard, pestañas separadas y ausencia de futuras capacidades. **Regresión del sidebar abierta en REV-01.** |
| AC-08 | Carga/vacío/reintento/errores/éxito, errores asociados a campos, doble envío, formularios independientes, beforeunload y guard. Pruebas de componentes y evidencia visual delegada, con límites siguientes. |

## Arquitectura, seguridad y alcance

INV-01/04: company_id procede de shared.tenancy, nunca del payload. Consultas nuevas de negocio y auditoría filtradas por empresa; clientes ajenos devuelven404. No imports accounts dentro de Dentistry/Customers. Permiso global no se relajó. INV-02/03: clínica solo en Dentistry, demografía en Customers, DTO administrativos sin clínica y API Customer existente preservada. INV-05: transacciones y bloqueo coherentes, auditoría protegida y solo lectura. INV-06: sin nacimiento no se presume mayoría; pareja responsable y límites validados.

Dominio nuevo sin Django; dependencia Dentistry→Customers únicamente por adaptador/fachada/DTO. Lectura de resúmenes en lote evita N+1; listado e historiales paginados. Migraciones nuevas aditivas, sin modificación de migraciones ya aplicadas. Ajuste de test_migrations y catálogo/límites corresponde a regresión documentada. No se observó scope creep ni secretos en el diff revisado; no se leyó .env.

Revisión manual de ramas backend: textos válido/vacío/exceso, archivo/activación, errores de cliente/perfil, no-op, auditoría fallida, concurrencia y límites de edad/contacto están ejercitados. No se afirma cobertura exhaustiva: no hay tests directos específicos para ambas ramas defensivas de exceso de longitud del nombre/teléfono en Demographics.validated ni para todo error interno inesperado. Serializers limitan esos campos en HTTP. No se instaló coverage.py para medir.

## Diseño y revisión visual

Checklist §8 revisada estáticamente: estructura lista/formulario/detalle con tarjetas y breadcrumbs; clases de plantilla, sin HEX/fuentes nuevas; ngx-datatable, botones, badges, Reactive Forms y alta rápida reutilizados; estados y labels/aria de controles presentes; español y fechas locales. La pantalla de acceso denegado sigue patrón de tarjeta y ofrece reintento.

El revisor técnico no operó navegador. Evidencia visual ejecutada por el orquestador y leída en [VISUAL](../tests/VISUAL-2026-11-02-perfil-odontologico-pacientes.md): escritorio1440/móvil390, claro/oscuro, alta desde Customer, validación menor, guardados y auditoría; sin overflow global. Archivo por navegador solo llegó a confirmación nativa; aceptación no verificada visualmente por limitación del adaptador, compensada con API/componente. No se afirma ese paso como ejecutado por UI. E2E automatizado no exigido por el plan, por lo que no es una verificación omitida.

## Siguiente paso

Corregir REV-01 y repetir las pruebas de sidebar/feature más la suite completa que falló. Conservar los checks backend ya aprobados si no cambia backend; repetir Quality Gate sobre el nuevo HEAD y completar build/audit antes de considerar PASS. Este informe no aprueba publicación ni merge.
