# PLAN-2026-11-19-configuracion-contable-por-defecto-nueva-empresa (v2)

**Task:** TASK-configuracion-contable-por-defecto-nueva-empresa · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** ADR-configuracion-contable-por-defecto-nueva-empresa-snapshot-y-puerto

## Objective
Que la configuración contable y de módulos de «demo dore» sea el default de toda empresa nueva y poder copiarla a una empresa específica con un script.

## Context
Ver TASK. Base de la rama: `accounting`.

# Specification
## Domain context
Contextos: accounts (alta), modularity, accounting, expenses, purchases, inventory.

## Current behavior
Empresa nueva sin configuración contable, 4 módulos, sin ajustes (`accounts/registration.py:27-49`, `modularity/domain/modules.py:43`).

## Expected behavior
- Al registrarse, la empresa recibe: 4 categorías de gasto, almacén principal, 20 cuentas del plan, 5 mapeos de método, 7 clasificaciones, 10 cuentas de asientos automáticos (roles y categorías remapeadas), corte = hoy y período del año en curso, ajuste de Compras, ajustes de Ventas y los 14 módulos habilitados.
- `copy_company_defaults` aplica lo mismo a una empresa existente completando solo lo faltante.
- `export_company_defaults` regenera el snapshot desde una empresa.

## Domain rules / invariants
- INV-01: toda escritura filtra por `company_id`; nada del snapshot contiene UUID de otra empresa.
- INV-02: aplicar es idempotente (segunda ejecución: 0 creados).
- INV-03: no se pisa configuración existente (cuentas por código o nombre, mapeos, clasificaciones, ajustes, módulos). Excepción (v2): una cuenta existente se reactiva si el snapshot la define activa y se le completan solo los datos vacíos (código, tipo, clasificación, moneda).
- INV-04: dinero en `Decimal`; saldos de apertura = 0.
- INV-05: el alta es atómica: si falla la siembra no queda empresa.

## Acceptance criteria
- AC-01: registrar empresa nueva deja las 20 cuentas con códigos/clases/tipos del snapshot.
- AC-02: quedan los 5 mapeos de método y las cuentas por rol y por categoría (categorías remapeadas a los UUID de la nueva empresa).
- AC-03: quedan las 7 clasificaciones y el ajuste de Compras apuntando a la clasificación correcta.
- AC-04: quedan los 14 módulos habilitados, cobertura de Contabilidad abierta, corte = fecha de alta y período «<año>» abierto.
- AC-05: ajustes de Ventas WHATSAPP/QR guardados; categorías de gasto y almacén creados.
- AC-06: empresas existentes no cambian al desplegar; dos altas no se mezclan (aislamiento).
- AC-07: `copy_company_defaults` en empresa vacía deja el mismo resultado que el alta; en empresa con datos solo crea lo ausente; `--dry-run` no escribe; empresa inexistente → error claro.
- AC-08: `export_company_defaults` produce un JSON sin UUID ni datos de personas, y re-aplicarlo reproduce la configuración.
- AC-09: si una sección falla en el alta, no se crea la empresa.

## Edge cases / Error cases
Nombre de empresa duplicado/ambiguo en el comando; snapshot inválido (referencia a cuenta/categoría inexistente) → error antes de escribir; empresa con parte de la configuración; empresa con asientos.

## Authorization / permissions
Comandos de gestión: solo operación (consola). Sin API nueva.

## API contract
Sin cambios; `POST /api/auth/register/` mantiene su contrato.

## Non-functional requirements
Sin secretos en el snapshot ni en la salida; salida del comando en español.

## Out of scope
Pantallas, cambio de `DEFAULT_ENABLED_KEYS` para empresas existentes, copiar saldos/asientos/movimientos, aplicar a todas las empresas en lote.

# Test Specification
## Unit tests / Integration tests
Unit: parseo/validación del snapshot y remapeo por claves naturales. Integración (DB): alta completa, copia vacía/parcial/idempotente/dry-run, export→apply round-trip, atomicidad (sección que falla), aislamiento entre dos empresas, frontera (`accounts` solo importa `shared`).
## E2E
NO — flujo cubierto por tests de API de registro y de comando.
## Regression tests
Suite existente de accounts/modularity/accounting (los tests que crean empresa con `Company.objects.create` no deben cambiar).
## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01..05 | integración: `register_company_admin` + consultas por sección |
| AC-06 | integración: dos altas y empresa creada con `Company.objects.create` sin cambios |
| AC-07 | integración: `call_command('copy_company_defaults', …)` |
| AC-08 | unit + round-trip del export |
| AC-09 | integración con sección que lanza error |

# Implementation Plan
## Architecture considerations
Ver ADR: puerto `shared/company_defaults.py`, secciones registradas en `apps.py`, orden fijo, `ctx` de mapas nombre→UUID.
## Proposed solution
Snapshot JSON + secciones export/apply por módulo + orquestador + 2 comandos + llamada en el alta.
## Files/components affected
- `backend/shared/company_defaults.py` y `backend/shared/company_defaults/snapshot.json`.
- Secciones en `modularity`, `accounting`, `expenses`, `purchases`, `inventory` (`infrastructure/defaults.py` + registro en `apps.py`).
- `backend/modules/accounts/registration.py` y comandos `export_company_defaults` / `copy_company_defaults`.
- Tests por sección y de integración; `docs/producto/modulos-implementados.md`, `CLAUDE.md` (comandos) si aplica.
## Implementation steps
1. Puerto + orquestador + validación del snapshot (INV-01..03, AC-08).
2. Secciones expenses, inventory, accounting, purchases, modularity (AC-01..05).
3. Comandos `export_company_defaults` (generar y revisar snapshot con «demo dore») y `copy_company_defaults` (AC-07, AC-08).
4. Integrar en el alta atómica (AC-06, AC-09).
5. Tests de integración y frontera; lint solo en archivos cambiados.
## Database / migrations
Sin migraciones.
## Risks
Orden de habilitación de Contabilidad (precondiciones y cobertura); snapshot desactualizado frente a nuevas configuraciones.
## New dependencies
Ninguna.

## Changelog
- **v2** (2026-11-19): [Specification] INV-03 ampliado: una cuenta existente (por código o nombre) se reactiva y se completa en sus datos vacíos, en vez de omitirse. Aprobado explícitamente por el usuario en el chat tras detectar una cuenta «Caja» sin código en `demo dore` y cuentas desactivadas.
