# PLAN-2026-11-18-validar-migracion-integracion-conciliacion-contable (v1)

**Task:** TASK-validar-migracion-integracion-conciliacion-contable · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** Ninguno

## Objective
Demostrar con evidencia real que `accounting` está lista para integrarse a `main`: migraciones en base nueva y en copia de la base local, libro conciliado (Debe = Haber, saldos, orígenes, sin duplicados), flujos integrados con Contabilidad habilitada/deshabilitada, períodos, aislamiento y concurrencia; actualizar la documentación y dejar preparado, sin mergear, el PR `accounting → main`.

## Context
Tarjeta CONT-13 (ver TASK). `accounting` está 38 commits por delante de `main` y sin divergencia. La conversión del libro anterior (Etapa 2 de CONT-07) no existe y no es parte de esta tarea.

# Specification

## Domain context
Bounded context `accounting` (libro de partida doble, períodos, cuentas, configuración de asientos). Contextos relacionados confirmados: `sales`, `receivables` (cobros), `service_catalog`/`dentistry` (servicios), `inventory`, `purchases`, `expenses`, `modularity`, `reporting` (solo lectura).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Asiento (`JournalEntry`) | Registro de partida doble con líneas debe/haber, período y origen | `models.py:198` |
| Libro anterior (`Entry`) | Movimientos de una sola cuenta previos a la partida doble | `models.py:122` |
| Corte (`cutoff_date`) | Fecha desde la cual la empresa contabiliza; lo anterior es histórico | ADR modularidad |
| Origen | `(origin_kind, origin_id)` idempotente del asiento | `models.py:236` |
| Reversión | Asiento nuevo que anula al original y lo conserva, en período abierto | TASK GAS-02 |

## Current behavior
Ver `## Investigación` del TASK: piezas aisladas con pruebas propias; no hay validación integrada ni base migrada conciliada; `activar-accounting.md` desactualizado.

## Expected behavior
Al terminar: (a) existe una prueba integrada reproducible del recorrido de la tarjeta; (b) los checks del repositorio relevantes pasan o sus fallos previos quedan documentados con evidencia; (c) hay un informe de validación con resultados reales; (d) la documentación de despliegue y activación describe el estado real; (e) queda redactado el PR `accounting → main` para aprobación humana.

## Domain rules / invariants
- INV-01 (existente): todo asiento cumple Debe = Haber y total > 0; moneda y dinero en `Decimal`.
- INV-02 (existente): un origen genera a lo sumo un asiento de registro; reintentar no duplica.
- INV-03 (existente): un período cerrado rechaza registros; la reversión usa un período abierto y conserva el asiento original.
- INV-04 (existente): sin cobertura (Contabilidad deshabilitada, o fecha anterior al corte) no hay contabilización retroactiva.
- INV-05 (existente): toda consulta filtra por `company_id`; una empresa no ve ni afecta datos de otra.
- INV-06 (existente): la migración repetida no duplica ni modifica datos.

## Acceptance criteria
- AC-01 (tarjeta 1): una prueba integrada ejecuta venta a crédito, cobro parcial, servicio cobrado, compra con recepción y pago, gasto y su reversión; todos los asientos cuadran, los saldos por cuenta y los pendientes (por cobrar, por pagar) coinciden con valores calculados a mano, y no hay asientos duplicados.
- AC-02 (tarjeta 2): `migrate` en base nueva y en copia restaurada de la base local termina sin error; una segunda ejecución no cambia nada; los conteos y sumas del libro anterior, cuentas y aperturas son idénticos antes y después.
- AC-03 (tarjeta 3): con un período cerrado, registrar en él falla; revertir un asiento de ese período crea la reversión en un período abierto y el original permanece intacto.
- AC-04: conciliación sobre la base migrada: 100 % de asientos con Debe = Haber; suma de saldos por cuenta = suma de líneas; cada asiento con origen apunta a un registro existente de su empresa; 0 duplicados por `(company, origin_kind, origin_id)`; los saldos de apertura cuadran.
- AC-05: con Contabilidad deshabilitada no se crean asientos ni se rompe la operación de negocio; una operación con fecha anterior al corte no genera asiento; habilitar después no contabiliza retroactivamente en silencio.
- AC-06: aislamiento y permisos: con dos empresas, la API de cuentas, períodos, asientos, saldos y configuración nunca expone datos de la otra; un usuario sin permiso recibe 403.
- AC-07: reintentos/concurrencia y fallos transaccionales: reintentar el mismo origen no duplica; un fallo a mitad de una operación no deja asiento ni efecto de negocio parcial.
- AC-08: las cuatro secciones del menú contable, la configuración por módulo, las clasificaciones, las cuentas y los períodos responden y se listan correctamente (API probada; navegación y textos probados en las pruebas de frontend existentes).
- AC-09: `docs/deployment/activar-accounting.md` y `docs/deployment/transicion-partida-doble.md` describen el estado real (partida doble, períodos, procedimiento de respaldo/recuperación, orden de migraciones); existe un informe de validación `docs/deployment/validacion-accounting-a-main.md` con resultados reales y limitaciones.
- AC-10 (tarjeta 4): los checks relevantes (backend completo, `makemigrations --check`, lint de los archivos cambiados, frontend `npm test`, `npm run lint`, `npm run build`, `npm run i18n:check`) se ejecutan y su resultado real —incluidos fallos— se documenta en el informe y el PR.
- AC-11: queda redactado el cuerpo del PR `accounting → main` (resumen de cambios, migraciones, evidencia, limitaciones, recuperación) sin abrirlo ni mergearlo.

## Edge cases / Error cases
- EDGE-01: base local sin corte en algunas empresas (bloqueadas por CONT-07): la validación las informa y no las convierte.
- EDGE-02: el libro anterior con entradas y el libro nuevo en la misma empresa: los reportes contables no cuentan ambos (ADR de reportes).
- EDGE-03: reversión de un asiento ya revertido: rechazada.
- EDGE-04: moneda distinta de la de la empresa: rechazada, sin conversión de divisas.

## Authorization / permissions
Sin cambios; se verifican los permisos existentes (AC-06).

## API contract
Sin cambios de contrato. Si una validación revela que un contrato debe cambiar, se detiene el trabajo y se versiona este plan (con ADR si corresponde).

## UI behavior
Sin cambios de UI. Solo se comprueba lo existente (AC-08).

## Non-functional requirements
Reproducibilidad: toda evidencia indica comando, fecha y entorno. Nunca se transforman datos de `doredb` directamente; solo copias restauradas. Sin `--fake`, sin borrar ni editar migraciones aplicadas.

## Out of scope
Conversión del libro anterior a asientos (Etapa 2 de CONT-07); datos reales de producción; merge o despliegue a `main`; nuevas funciones contables; conversión de divisas.

## Open questions
- No bloqueante: contrapartidas, códigos y cuenta de Patrimonio de la conversión del libro anterior siguen abiertos (decisión del dueño, CONT-07); se documentan como limitación.

# Test Specification

## Unit tests / Integration tests
Integración backend (PostgreSQL) en `backend/modules/accounting/tests/test_cont13_integration.py` (y complementarias si hace falta): AC-01, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08. Prueba de migración con `MigrationExecutor` (patrón `test_migration_0010.py`) para la idempotencia estructural de AC-02. Unit: solo si se corrige código de producto.

## E2E
**NO** — el recorrido crítico se cubre con integración de API sobre PostgreSQL; no se instala Playwright. La verificación visual de los submenús se limita a las pruebas de componentes existentes y, si el entorno lo permite, a una pasada manual documentada.

## Regression tests
Suite completa del backend y del frontend sobre `accounting` HEAD antes y después de los cambios.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | `test_cont13_integration` (flujo integrado con importes calculados a mano) |
| AC-02 | `migrate` en base nueva (creación de la base de pruebas), ensayo `pg_dump`→`pg_restore`→`migrate` x2 en copia de `doredb` con conteos/sumas antes y después; prueba con `MigrationExecutor` |
| AC-03 | `test_cont13_integration` (período cerrado + reversión) |
| AC-04 | Consultas de conciliación SQL/ORM sobre la base de pruebas del flujo y sobre la copia migrada; resultados en el informe |
| AC-05 | `test_cont13_integration` (módulo deshabilitado, anterior al corte, habilitación posterior) |
| AC-06 | `test_cont13_integration` (dos empresas, sin permiso) |
| AC-07 | `test_cont13_integration` + `test_*_concurrency` existentes ejecutados |
| AC-08 | Pruebas de API de cuentas/períodos/clasificaciones/configuración + pruebas de frontend existentes |
| AC-09 | Revisión de los tres documentos contra el código (`archivo:línea`) |
| AC-10 | Salida real de cada comando registrada en el informe |
| AC-11 | Archivo con el cuerpo del PR en el informe; verificado que no se abre ni mergea |

# Implementation Plan

## Architecture considerations
No se añaden abstracciones ni módulos. Las pruebas integradas viven en `accounting/tests` (como `test_unified_journey.py`, que ya importa otros módulos); respetar `sales/tests/test_boundaries.py`.

## Proposed solution
Primero medir (línea base de checks y ensayo de migración en copia), luego cerrar el hueco de pruebas integradas, corregir lo estrictamente necesario si algo falla, y por último documentar con resultados reales.

## Files/components affected
- Backend (pruebas): `backend/modules/accounting/tests/test_cont13_integration.py` (nuevo), posibles ajustes en `journal_support.py`.
- Backend (producto): solo si una validación falla; cada cambio acotado y citado en el informe.
- Migraciones: ninguna prevista.
- Docs: `docs/deployment/validacion-accounting-a-main.md` (nuevo), `docs/deployment/activar-accounting.md`, `docs/deployment/transicion-partida-doble.md`, TASK.

## Implementation steps
1. Línea base: con el venv y `node_modules` de la copia principal, correr suite backend completa, `makemigrations --check`, lint de archivos cambiados y checks de frontend sobre `accounting` HEAD (AC-10).
2. Base nueva: crear base vacía y `migrate`; registrar cadena aplicada (AC-02).
3. Ensayo en copia: localizar `pg_dump`/`pg_restore` (Docker o ruta de instalación); respaldo de `doredb` → restaurar en copia → conteos/sumas → `migrate` x2 → conteos/sumas → diagnóstico CONT-07 (AC-02, AC-04). Solo lectura sobre `doredb`.
4. Conciliación sobre la copia: Debe = Haber por asiento, saldos por cuenta, orígenes, duplicados, aperturas (AC-04).
5. Escribir `test_cont13_integration.py` por escenarios AC-01, 03, 05, 06, 07, 08; ejecutar las pruebas de concurrencia existentes (AC-01…AC-08).
6. Si algo falla: corregir con el cambio mínimo y prueba de regresión; si implica cambio de contrato o de Specification, detener y volver a `delivery-start`.
7. Actualizar `activar-accounting.md` y `transicion-partida-doble.md`; escribir el informe con resultados reales y el cuerpo del PR `accounting → main` (AC-09, AC-11).
8. Repetir los checks tras los cambios (AC-10).

## Database / migrations
No se crean migraciones. Nunca editar una migración aplicada; solo `migrate` sobre copias; respaldo antes de cualquier prueba con datos.

## Risks
- Hallazgos que obliguen a corregir producto (se acotan y documentan).
- `pg_dump` no accesible → limitación documentada, ensayo con alternativa (Docker) o marcado como no realizado.
- Frontend: `npm test` (Karma) requiere navegador headless; si no corre, se registra.

## New dependencies
Ninguna. (No se instala Playwright ni paquetes.)
