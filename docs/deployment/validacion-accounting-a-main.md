# Validación de `accounting` antes de integrarla a `main` (CONT-13)

Informe de la validación (2026-11-18) sobre `origin/accounting` (c1afaf1, PR #103). Task: `docs/tasks/TASK-validar-migracion-integracion-conciliacion-contable.md`. **Este informe no autoriza merge ni despliegue**: cada push a `main` despliega a producción (`docs/deployment/github-actions.md`).

## Qué trae el PR `accounting → main`
- Sin divergencia (`main...accounting` = `0 38`): 38 commits, **87 archivos (+4985/−79)**.
- **Migraciones nuevas: ninguna.** `main` ya contiene `accounting` 0001–0011 (`git diff --name-status origin/main..origin/accounting -- 'backend/**/migrations/*.py'` vacío). El PR no cambia el esquema.
- Contenido: flujo de dinero (`accounting/application/cash_flow.py`, `ledger_report.py`, API `/api/accounting/cash-flow/`), reporte contable en `reporting`, reversión del asiento al anular un gasto, pantallas de frontend (33 archivos: Flujo de dinero, Gastos, Reportes) y documentación.

## Resultados reales
| Comprobación | Resultado |
|---|---|
| Backend completo, línea base (`manage.py test modules --parallel 4`, `config.settings.test`, PostgreSQL 16) | 2224 pruebas OK (136 s) |
| Backend completo tras añadir `test_cont13_integration` | **2230 pruebas OK** (172 s) |
| `makemigrations --check --dry-run` (sobre la copia) | «No changes detected» |
| `ruff check` y `flake8` del archivo nuevo | sin avisos |
| Frontend `npm run i18n:check` | 2328 claves usadas, 0 faltantes |
| Frontend `npm run lint` | «All files pass linting» |
| Frontend `npm run build` | OK; avisos: obsolescencias de `angular-sass`, 23 «Unmatched selector: %» y `stock-list.component.scss` excede el presupuesto de 2,00 kB por 38 bytes (aviso, no error; viene de `main`) |
| Frontend `npm test` (Karma, ChromeHeadless) | **1702 de 1702 OK** |
| `npm audit` (frontend) | 2 vulnerabilidades moderadas en dependencias transitivas (`hono`, `@hono/node-server`); no se ejecutó `audit fix` |

Entorno: Windows 11, Python 3.12, Node 22, PostgreSQL 16 local. Para ejecutar el frontend se hizo `npm ci` (sin cambios en `package*.json`).

## Flujo integrado (AC-01, AC-04) — `backend/modules/accounting/tests/test_cont13_integration.py`
Una empresa, libro de partida doble real. Importes calculados a mano; el saldo final de cada cuenta (debe − haber) coincide:

| Operación | Efecto |
|---|---|
| Apertura manual | Caja +1 000 / Capital −1 000 |
| Venta 300: anticipo 100 en preparación, entrega con saldo 200 | Anticipos 0 (cobrado y aplicado), Por cobrar +200, Ingresos −300 |
| Servicio Corona 200 prestado y cobrado 80 | Por cobrar +120, Ingresos por servicios −200, Caja +80 |
| Compra 1 000: recepción 600 y pago 400 | Inventario +600, Proveedores −200 (comercial pendiente 600), Caja −400 |
| Gasto 500 (banco) y gasto 120 (caja) anulado | Alquiler +500, Banco −500, Caja neto 0 |

Saldos finales: Caja 780, Banco −500, Por cobrar 320, Inventario 600, Alquiler 500; Proveedores −200, Ingresos −300 y −200, Capital −1 000. Suma = 0. Cada asiento cuadra (Debe = Haber = total, ≥ 2 líneas, cuentas de la empresa), 0 orígenes duplicados, 1 reversión (la del gasto) y 0 filas en el libro anterior `accounting_entry`.

## Cobertura por criterio
| AC | Verificación |
|---|---|
| AC-01, AC-04 | recorrido anterior + conciliación (`assert_books_reconcile`) y, sobre la copia migrada, las consultas de la sección siguiente |
| AC-02 | ensayo en copia (siguiente sección) y creación de la base de pruebas desde cero (cadena completa) en cada ejecución |
| AC-03 | `test_a_closed_period_blocks_records_and_the_reversal_goes_to_an_open_one`: un gasto en período cerrado se rechaza (409) sin dejar nada; anular uno anterior crea la reversión con fecha de hoy en otro período y conserva el original |
| AC-05 | `test_disabled_accounting_and_pre_cutoff_operations_are_never_posted_retroactively`: con Contabilidad deshabilitada el cobro y el gasto funcionan sin asientos; habilitar después no crea asientos; anular un gasto anterior al corte no crea reversión; desde hoy sí hay cobertura |
| AC-06 | `test_a_second_company_sees_and_changes_nothing_of_the_first`: cuentas, asientos, saldos, períodos y métodos no filtran datos; detalle de asiento ajeno 404; revertir un asiento ajeno no lo cambia; sin sesión 401. Los permisos por rol (miembro 403) ya están en las pruebas de cada API |
| AC-07 | recepción en período cerrado rechazada sin recepción, stock ni asiento; repetir un cobro con la misma clave o una recepción con el mismo `receipt_id` no duplica asientos. Concurrencia: `test_*_concurrency` de `accounting`, `purchases` y `expenses` (en la suite completa, OK) |
| AC-08 | API de cuentas, períodos, clasificaciones, métodos y configuración con sus pruebas existentes; navegación y pantallas con la suite de frontend (1702 OK). **No se hizo recorrido visual manual de los submenús.** |
| AC-09 | esta guía, `activar-accounting.md` y `transicion-partida-doble.md` |

## Ensayo de migración en copia (AC-02)
Sobre la base local `doredb` (solo lectura) con `pg_dump -Fc` → `createdb` → `pg_restore` en una copia; `migrate` y consultas solo sobre la copia. Script y volcado quedaron fuera del repositorio (ver «Recuperación»).
- Estado de `doredb`: **ya está en la cadena final** (`accounting` 0011, `expenses` 0004, `purchases` 0009, `sales` 0003, `receivables` 0002, `modularity` 0002). Desde el diagnóstico del 2026-11-16 la base cambió: `accounting_entry` quedó **vacío** (0 filas; antes 32) y hay 71 cuentas, 43 asientos y 88 líneas en el libro nuevo.
- Volcado: 262 776 bytes. La copia restaurada es **idéntica al origen** (conteos, sumas y migraciones aplicadas).
- `migrate` sobre la copia: «No migrations to apply» (dos veces); `makemigrations --check`: sin cambios; conteos y sumas idénticos tras cada ejecución.
- **Actualización desde un estado anterior:** en la copia se revirtió `accounting` a 0006 (desaplicó 0011…0007, desaparecen las tablas del libro nuevo) y se volvió a `migrate`: aplicó 0007–0011 sin errores; una segunda ejecución no aplicó nada. Las tablas heredadas (`accounting_account` y sus sumas, clasificaciones, mapeos, ajustes, cobertura, `accounting_entry`, pagos de ventas/cobros/compras y gastos) quedaron idénticas en los cuatro momentos. Límite: como `accounting_entry` está vacío, esto no ejercita conversión de datos antiguos; `test_migration_0004/0006/0010` cubren los cambios de datos de esas migraciones.
- Conciliación sobre la copia migrada: 43 asientos / 88 líneas con **Debe 8 014,00 = Haber 8 014,00**; **0 asientos descuadrados**, **0 orígenes duplicados**, **0 líneas con cuenta de otra empresa**. Base de apertura: la suma de `opening_balance` del libro anterior es 0,00 (no hay aperturas pendientes de convertir).
- Diagnóstico `diagnose_ledger_transition --json` sobre la copia: terminó sin errores (8 empresas con datos de Contabilidad); no hay entradas del libro anterior que convertir.
- Base de pruebas desde cero: cada `manage.py test` crea la base aplicando 0001…0011 y el resto de módulos sin errores (instalación nueva).

## Limitaciones
- **No implementado (fuera de alcance):** conversión del libro anterior a asientos (Etapa 2 de CONT-07). Hoy no hay datos que convertir en la base local; si una empresa de producción tiene `accounting_entry`, sigue vigente la decisión pendiente del dueño (contrapartidas, códigos, Patrimonio) — ver `transicion-partida-doble.md`.
- No se probó contra datos de producción; solo contra la base local de pruebas y la base de pruebas de Django.
- **AC-04 parcial:** se verificó cuadre, duplicados y cuentas de la empresa, pero no que cada asiento con origen apunte a un registro de origen existente (no hay FK entre módulos; queda como mejora).
- **AC-06:** el 403 para un miembro sin permiso no se repite en la prueba nueva; está en las pruebas de cada API.
- Sin prueba E2E de navegador ni recorrido visual manual de los cuatro submenús.
- Aviso de presupuesto de `stock-list.component.scss` (+38 bytes) y avisos de `angular-sass` en el build, preexistentes.

## Recuperación
1. Antes de desplegar: `pg_dump -Fc -f respaldo.dump <base>` (el deploy ya hace un backup, `docs/deployment/github-actions.md`).
2. Este PR no cambia el esquema: volver atrás es revertir el merge en `main` (git) y redesplegar; no hay migración que desaplicar.
3. Datos: restaurar el volcado con `pg_restore --clean`.
4. La copia de ensayo `doredb_cont13_copia` se elimina al cerrar el task (`dropdb`); el volcado queda fuera del repositorio.

## Cuerpo propuesto del PR `accounting → main` (no abierto)
> **Resumen:** integra a `main` los 38 commits de `accounting` (87 archivos): flujo de dinero contable, reporte contable en Reportes, reversión del asiento al anular un gasto, pantallas de Gastos/Reportes/Flujo de dinero y documentación.
> **Migraciones:** ninguna nueva (`main` ya tiene `accounting` 0001–0011).
> **Evidencia:** backend 2230 pruebas OK; frontend 1702 OK, lint, build e `i18n:check` OK; ensayo `pg_dump`→`pg_restore`→`migrate` x2 y reversión a 0006/avance a 0011 en copia sin diferencias; conciliación 8 014,00 = 8 014,00, 0 descuadres, 0 duplicados (ver `docs/deployment/validacion-accounting-a-main.md`).
> **Limitaciones:** conversión del libro anterior no implementada; sin prueba contra producción ni E2E de navegador.
> **Recuperación:** respaldo previo, `git revert` del merge y redespliegue; sin migraciones que revertir.
> **Importante:** el push a `main` despliega a producción; requiere aprobación humana, no mergear automáticamente.
