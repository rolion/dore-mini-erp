# PLAN-2026-11-14-conciliar-regularizar-pagos-historicos (v1)

**Task:** TASK-conciliar-regularizar-pagos-historicos · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** ADR-conciliar-regularizar-pagos-historicos-comando-y-fuentes

## Objective
Crear el comando administrativo `regularize_ledger` que compara los pagos históricos de pedidos (`PRODUCT`) y de proformas (`SERVICE`) con el libro de entradas por identidad de origen, previsualiza (obligatorio) y aplica solo las entradas faltantes elegibles con mapeo histórico explícito, sin alterar pagos, imputaciones ni saldos.

## Context
Ver TASK y ADR. Insumo: Trello PB-ACC-004. Dependencias ya en `main`: PB-ACC-003 y PB-COB-002.

# Specification

## Domain context
`accounting` (libro) como dueño del proceso; `sales` y `receivables` como fuentes de solo lectura vía `services`.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Regularizar | Crear la entrada que falta de un pago anterior al libro | Trello |
| Faltante | Pago sin entrada con su `(origin_kind, origin_id)` | Trello |
| Existente | Pago con entrada idéntica | Trello |
| Conflicto | Entrada existente con otro monto/fecha/método/moneda | Trello |
| Pendiente | Pago elegible sin mapeo aplicable; no se escribe | Trello |
| Mapeo histórico | Regla explícita método → cuenta, con rango de fechas efectivas | Trello |
| Pago anulado | No existe como estado en ningún origen | hecho |

## Current behavior
Solo los pagos nuevos crean entrada (`sales/infrastructure/adapters.py` `PaymentLedgerAdapter`, `receivables/infrastructure/adapters.py:58-70`). No hay comando de gestión en el repositorio ni lectura de pagos entre módulos que incluya pedidos cancelados.

## Expected behavior
`python manage.py regularize_ledger --company <uuid> [--from F] [--to T] --mapping m.json` imprime la previsualización sin escribir. Con `--apply --executed-by "<nombre>"` crea solo los faltantes elegibles y mapeados, y emite el resumen de resultados y errores.

## Domain rules / invariants
- INV-01 Previsualización sin escritura alguna; `--apply` es explícito y recalcula el plan al aplicar.
- INV-02 Identidad por `(company_id, origin_kind, origin_id)`; el comando solo lee pagos de la empresa indicada y nunca toca los de otra.
- INV-03 Sin mapeo aplicable (método sin regla o fecha fuera de rangos) → pendiente con motivo; jamás cuenta por defecto ni el mapeo vigente.
- INV-04 La entrada conserva fecha efectiva, monto, método, referencia de documento, comprobante y autor original si existe; fecha/usuario de regularización van aparte (`regularized_at`, `regularized_by_name`). Campo histórico ausente → «ausente» en el informe, nunca inventado.
- INV-05 El pago de un pedido cancelado es elegible; no existe estado «anulado» (se informa 0 excluidos).
- INV-06 No se modifican pagos, imputaciones, saldos ni entradas existentes; diferencias de importe/fecha/método/moneda → conflicto, de cuenta vs. mapeo → diferencia de destino; ambos solo se informan.
- INV-07 Idempotente y seguro ante concurrencia: segunda ejecución crea 0; dos simultáneas no duplican (bloqueo por empresa + unicidad del libro).
- INV-08 Dinero en `Decimal`; el informe agrupa por origen × cuenta × moneda.

## Acceptance criteria
- AC-01 Dataset con tres pagos (pedido A sin entrada, pedido/proforma con entrada idéntica, pedido cancelado con pago): la previsualización lista 2 faltantes y 1 existente sin escribir (cuenta de entradas igual antes y después); `--apply` crea exactamente los 2 faltantes (incluido el del pedido cancelado).
- AC-02 Método sin regla de mapeo (o fecha fuera de sus rangos) queda pendiente con motivo; no se crea entrada ni se asigna cuenta.
- AC-03 Con rangos por periodo, pagos del mismo método de distinto periodo van a cuentas distintas.
- AC-04 Segunda ejecución con `--apply` crea 0 entradas. Dos ejecuciones simultáneas (hilos, BD real) dejan una sola entrada por pago y la segunda informa «en curso» o 0 creadas.
- AC-05 Las entradas creadas conservan fecha, monto, método, `origin_document_ref`, comprobante y autor original; Ventas (sin autor) queda con autor vacío y el informe lo marca ausente; `regularized_at/by` se llenan solo en entradas regularizadas (no en las de cobros normales).
- AC-06 Pagos, imputaciones, `paid_total`/saldos y estados de pedidos/proformas son idénticos antes y después; regularizar la empresa A no crea ni lee entradas de la B.
- AC-07 Entrada existente con importe (o fecha/método) distinto → conflicto reportado y entrada intacta; con cuenta distinta a la mapeada → diferencia de destino reportada, intacta.
- AC-08 El informe separa cantidades e importes por origen × cuenta × moneda para faltantes, existentes, pendientes, conflictos y errores; y reporta el filtro de periodo y la cobertura del mapeo.
- AC-09 `--apply` sin `--executed-by` o sin `--mapping` (cuando hay faltantes), `--company` inexistente o mapeo inválido (cuenta ajena, inactiva, no BOB, rangos solapados, método desconocido) → error de uso con exit ≠ 0 y sin escrituras.
- AC-10 Un error en una entrada (p. ej. rechazo del libro) se informa y no impide crear las demás; no queda entrada parcial.

## Edge cases / Error cases
- EDGE-01 `--from > --to` o fechas inválidas → error de uso.
- EDGE-02 Empresa sin pagos o sin faltantes → informe vacío, exit 0.
- EDGE-03 Pagos con monto que el libro rechaza → categoría `invalid`/error, no aborta.
- EDGE-04 Cobro nuevo concurrente que crea la entrada entre la lectura y la creación → `created=False`, contado como existente.
- EDGE-05 Módulo `accounting` deshabilitado para la empresa: el comando funciona igual (permite regularizar antes de habilitar); lo declara el informe.

## Authorization / permissions
Sin API ni pantalla; solo quien ejecuta comandos en el servidor. La empresa la indica `--company` (identificador explícito del operador); jamás se infiere de datos de otra empresa.

## API contract
Sin cambios de API HTTP. Contrato interno nuevo: `sales.services.list_historical_payments` y `receivables.services.list_historical_payments` (DTO inmutables, empresa primer argumento).

## UI behavior
Sin UI (la interfaz de entradas existente no cambia).

## Non-functional requirements
Lectura en lotes por empresa y periodo; sin N+1 al comparar (un `IN` por origen). Sin dependencias nuevas.

## Out of scope
Partida doble, fiscal, egresos, transferencias, saldos iniciales, reversiones, endpoint/pantalla, cambiar el reporte ventas − gastos, modificar pagos o saldos, anulaciones.

## Open questions
- Si en el futuro aparece un estado «anulado» de pago: el DTO ya reserva `document_state`; no bloquea.

# Test Specification

## Unit tests
Dominio/aplicación (con fuentes y libro en memoria): clasificación faltante/existente/pendiente/conflicto/diferencia de destino (AC-02, AC-03, AC-07), validación del mapeo (AC-09), agregación del informe (AC-08).

## Integration tests
BD real: dataset de AC-01 con ambos orígenes, previsualización sin escritura (conteos), aplicación, segunda pasada (AC-04), conservación de campos (AC-05), invarianza de pagos/saldos y aislamiento por empresa (AC-06), error en una entrada (AC-10), comando por `call_command` (códigos de salida/mensajes, AC-09); concurrencia con hilos (AC-04). `test_boundaries` actualizado.

## E2E
**NO** — proceso de servidor sin UI.

## Regression tests
Suites de `accounting`, `sales` y `receivables` completas; migración `0003` aditiva.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | integración dataset |
| AC-02 | unit + integración |
| AC-03 | unit |
| AC-04 | integración (segunda pasada) + concurrencia con hilos |
| AC-05 | integración |
| AC-06 | integración (snapshot de pagos/saldos y empresa B) |
| AC-07 | unit + integración |
| AC-08 | unit + `call_command` (texto y `--json`) |
| AC-09 | `call_command` |
| AC-10 | integración con libro que falla |

# Implementation Plan

## Architecture considerations
Ver ADR. `accounting.application` define el puerto de fuentes; adaptadores importan solo `sales.services` y `receivables.services`. Comando delgado: parsea argumentos, invoca el caso de uso y formatea el informe.

## Files/components affected
- backend `accounting`: `domain/regularization.py` (clasificación pura, mapeo por rangos, reporte), `application/regularize.py` (caso de uso y puertos), `infrastructure/historical_sources.py`, `management/commands/regularize_ledger.py`, `infrastructure/django/models.py` + repositorio (columnas nuevas, `insert` con metadatos de regularización), migración `0003_entry_regularization`, `services.py` (`EntryInput` con `regularized_*` opcionales, lectura de entradas por origen).
- backend `sales/services.py`, `receivables/services.py` (+ consultas de solo lectura en sus `infrastructure/django/`).
- tests: nuevos en `accounting/tests/`, `sales/tests/test_boundaries.py` (mapa), tests de las dos fachadas.
- docs: `docs/architecture/ddd.md` (nota y dependencias), TASK.

## Implementation steps
1. Migración y modelo/repositorio con `regularized_at/by` (INV-04).
2. Fachadas de lectura en `sales` y `receivables` (incluyen cancelados) con pruebas (INV-05).
3. Dominio de regularización: mapeo por rangos y clasificación (INV-02, INV-03, INV-06, AC-02, AC-03, AC-07).
4. Caso de uso: plan → informe; aplicar con bloqueo por empresa y una transacción por entrada (INV-01, INV-07, AC-04, AC-10).
5. Comando y formato de informe texto/JSON, validaciones de uso (AC-08, AC-09).
6. Pruebas de integración y de concurrencia; actualizar `test_boundaries` y `ddd.md`.
7. Comandos de auditoría SQL de entradas regularizadas en el TASK.

## Database / migrations
`accounting/0003_entry_regularization`: dos columnas nulables en `accounting_entry`, aditiva, sin tocar migraciones aplicadas.

## Risks
- Datos históricos con montos/dato inválidos: se informan como error por pago, no abortan.
- Diferencias de zona horaria en `payment_date`: es `date`, sin conversión.
- Bloqueo advisory solo existe en PostgreSQL (el proyecto lo exige; los tests usan PostgreSQL).
- Mapeo mal armado por el operador: la previsualización con totales por cuenta es la salvaguarda.

## New dependencies
Ninguna.
