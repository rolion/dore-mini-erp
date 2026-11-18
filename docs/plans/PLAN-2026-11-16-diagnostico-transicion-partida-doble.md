# PLAN-2026-11-16-diagnostico-transicion-partida-doble (v1)

**Task:** TASK-diagnostico-transicion-partida-doble · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** ADR-diagnostico-transicion-partida-doble-estrategia-y-contrato

## Objective
Entregar la Etapa 1 de CONT-07: un diagnóstico reproducible y de solo lectura del libro actual, el contrato de transición al modelo de partida doble y el procedimiento de respaldo/recuperación, con el resultado de conciliación de la base local. La conversión (Etapa 2) queda especificada pero no se implementa hasta que exista el esquema destino.

## Context
Ver TASK. Base `accounting`; no se mergea a `main`. La base local ya tiene `accounting` 0001–0006 aplicadas.

# Specification

## Domain context
`accounting` (dueño del libro), lectura de `sales`, `receivables`, `expenses`, `purchases`.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Entrada / movimiento | Línea de una sola cuenta del libro actual (`accounting_entry`) | `models.py` |
| Cuenta de dinero | `accounting_account`; pasa a ser cuenta de Activo | tarjeta CONT-07 |
| Contrapartida | La otra cuenta del asiento (Ingresos, Gastos, Costos, Pasivo, Patrimonio) | tarjeta |
| Corte | `accounting_settings.cutoff_date` | ADR CONT-06 |
| Pendiente | Movimiento sin contrapartida verificable: no se convierte | ADR |
| Histórico | Movimiento con fecha anterior al corte: no genera asiento | ADR CONT-06 |

## Current behavior
Ver TASK («Hechos encontrados»).

## Expected behavior
- Existe `python manage.py diagnose_ledger_transition [--company <uuid>] [--json]` que no escribe y reporta, por empresa: cuentas, saldos de apertura, entradas por dirección/operación/origen, entradas por estado de conversión, conciliación contra los pagos/gastos de origen y empresas bloqueadas.
- Existe `docs/deployment/transicion-partida-doble.md` con el procedimiento (respaldo, ensayo en copia, verificación, recuperación), el contrato de mapeo (formato JSON), las reglas de corte/apertura/doble cómputo y los casos pendientes.
- La conciliación de la base local queda registrada en el TASK.

## Domain rules / invariants
- INV-01: el diagnóstico nunca escribe (ni crea, ni actualiza, ni borra).
- INV-02: toda consulta filtra por `company_id`; el resultado de una empresa no incluye datos de otra.
- INV-03: ninguna contrapartida se asume; sin regla explícita el movimiento es «pendiente» con motivo.
- INV-04: lo anterior al corte es «histórico» y no suma al convertir (sin doble cómputo con la apertura); una empresa con entradas y sin corte está «bloqueada».
- INV-05: importes en `Decimal`, sin conversión de moneda; una discrepancia de monto o moneda con el origen es «pendiente».
- INV-06: el diagnóstico es determinista: repetirlo sobre los mismos datos da el mismo resultado.

## Acceptance criteria
- AC-01: el comando informa, por empresa, conteos e importes de cuentas (con/sin `kind`, apertura), entradas (dirección, operación, origen, regularizadas, sin clasificación) y movimientos de origen sin entrada, coincidiendo con consultas SQL directas sobre datos de prueba.
- AC-02: cada entrada se clasifica en `convertible_con_regla`, `historica` o `pendiente` con un motivo de la lista del ADR; sin reglas, ninguna es `convertible_con_regla` y todas las posteriores al corte son `pendiente/sin_regla_de_contrapartida` (aceptación 4 de la tarjeta, en modo diagnóstico).
- AC-03: con un mapeo JSON válido, las entradas cubiertas son `convertible_con_regla`; un mapeo inválido (cuenta de otra empresa, regla duplicada/solapada) se rechaza con mensaje y no se aplica nada.
- AC-04: una empresa con entradas y sin corte aparece como bloqueada; los saldos de apertura > 0 aparecen con su estado (pendiente si falta cuenta de Patrimonio o corte).
- AC-05: el comando no modifica la base: el conteo de filas de `accounting_*`, `sales_payment`, `receivables_payment`, `expenses_expense` y `purchases_payment` es idéntico antes y después, y una segunda ejecución produce el mismo resultado (INV-06).
- AC-06: el aislamiento por empresa se cumple con dos empresas de prueba (AC con `--company`, y sin él, cada empresa solo cuenta lo suyo).
- AC-07: `docs/deployment/transicion-partida-doble.md` existe con respaldo/ensayo/recuperación, formato de mapeo, reglas, lista de decisiones del dueño y resultado de conciliación local.
- AC-08: base nueva desde el código de `accounting` aplica la cadena completa (`migrate`) sin errores; una copia de la base local restaurada con `pg_restore` aplica `migrate` sin cambios (ya aplicadas) y el diagnóstico antes/después da los mismos importes (aceptaciones 1 y 2 de la tarjeta, Etapa 1).

### Contrato para la Etapa 2 (no se implementa ahora; criterios futuros)
- AC-S2-01: reejecutar la conversión no duplica cuentas ni asientos (clave natural `(company, origin_kind, origin_id, operation)`). 
- AC-S2-02: cada asiento convertido cuadra (débitos = créditos) y conserva `entry_id`/referencias; el saldo de cada cuenta convertida coincide con `account_balances`.
- AC-S2-03: ningún pendiente se convierte; la apertura se convierte por asiento balanceado.

## Edge cases / Error cases
Empresa sin cuentas; entrada con origen inexistente (huérfana); pago de origen con monto distinto de la entrada; sin `--company` con muchas empresas; mapeo con cuenta inactiva o de otra moneda; fecha de corte posterior a todos los movimientos.

## Authorization / permissions
Comando de línea de comandos (requiere acceso al servidor); no expone API ni UI. No se ofrece a miembros ni a administradores por la web.

## API contract
Ninguno (sin endpoints).

## UI behavior
No aplica.

## Non-functional requirements
Consultas por empresa con los índices existentes; salida legible y `--json`; sin dependencias nuevas.

## Out of scope
Conversión de datos (Etapa 2); esquema de partida doble, seis clasificaciones, cuentas con código (CONT-08/09); limpieza o borrado de datos de prueba; UI; merge a `main`; cambios en ventas, cobros, gastos o compras.

## Open questions (no bloquean)
Códigos de las cuentas de dinero; tratamiento de anticipos (¿Pasivo?); contrapartida de egresos; cuenta de Patrimonio para apertura; corte de las 3 empresas sin él; qué empresas son de prueba. Se registran en el documento de transición para decisión del dueño.

# Test Specification

## Unit tests
Dominio de clasificación del diagnóstico (puro, sin Django): estado y motivo por entrada, parseo y validación del mapeo, bloqueo por falta de corte.

## Integration tests
Comando sobre PostgreSQL de prueba con dos empresas: conteos, conciliación con pagos de ventas/cobros/compras/gastos, no escritura, determinismo, aislamiento y `--json`.

## E2E
**NO** — comando de gestión sin UI; la verificación de migraciones (AC-08) se hace con `migrate` en base nueva y en copia (evidencia en el documento y el PR).

## Regression tests
Se ejecutan los tests de `accounting` existentes (incl. `test_migration_0004/0006`, `regularize_ledger`).

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | integración: comparación con SQL directo |
| AC-02 | unitaria + integración |
| AC-03 | unitaria (parseo) + integración |
| AC-04 | integración |
| AC-05 | integración (conteos antes/después y segunda ejecución) |
| AC-06 | integración con dos empresas |
| AC-07 | revisión del documento |
| AC-08 | `migrate` en base nueva y en copia restaurada, registrado en el documento |

# Implementation Plan

## Architecture considerations
Seguir `regularize_ledger`: dominio puro en `domain/`, lectura en `application/` con puertos, adaptadores de lectura en `infrastructure/adapters.py`, comando en `management/commands/`. Accounting no importa infraestructura de otros módulos: para gastos/compras se usa la fachada pública o un puerto de lectura mínimo en esos módulos (permitido por `test_boundaries`).

## Proposed solution
Dominio `domain/transition.py` (estados, motivos, mapeo); caso de uso `application/transition_diagnosis.py`; adaptadores de lectura de orígenes; comando `diagnose_ledger_transition`; documento de procedimiento.

## Files/components affected
- backend: `modules/accounting/domain/transition.py`, `application/transition_diagnosis.py`, `infrastructure/adapters.py` (lectores de gastos/compras si faltan), `management/commands/diagnose_ledger_transition.py`, y los puertos de lectura mínimos en `expenses`/`purchases` si no existe fachada.
- tests: `modules/accounting/tests/test_transition_domain.py`, `test_transition_command.py`.
- docs: `docs/deployment/transicion-partida-doble.md`; `docs/deployment/activar-accounting.md` (enlace).
- migraciones: ninguna.

## Implementation steps
1. Dominio y mapeo con pruebas unitarias (AC-02, AC-03, INV-03..05).
2. Caso de uso y adaptadores de lectura por empresa (AC-01, AC-04, INV-02).
3. Comando con salida de texto y `--json` (AC-01, AC-05, AC-06).
4. Pruebas de integración (AC-01, AC-04, AC-05, AC-06).
5. Ejecutarlo sobre una copia de la base local (respaldo con `pg_dump`/`pg_restore` en otra base) y registrar la conciliación y la verificación de migraciones (AC-07, AC-08). La base local original no se modifica.
6. Documento de procedimiento y decisiones del dueño (AC-07).

## Database / migrations
Sin migraciones. Nunca editar una migración aplicada.

## Risks
Crear la copia exige `pg_dump`/`createdb` disponibles en la máquina; el uso de la base local es de solo lectura. Datos personales no deben aparecer en el documento ni el PR (solo UUID y agregados).

## New dependencies
Ninguna.
