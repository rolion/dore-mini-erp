# PLAN-2026-10-30-iniciar-valoracion-inventario-costeo (v1)

**Task:** TASK-iniciar-valoracion-inventario-costeo · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-iniciar-valoracion-inventario-costeo-asistente-valoracion · ADR-iniciar-valoracion-inventario-costeo-modulo-costeo-y-adopcion

## Objective
Permitir que el admin adopte una valoración inicial del inventario (valor total en BOB por producto, método promedio ponderado móvil) en un corte inmutable, detrás del módulo opcional «Costeo», sin alterar cantidades ni movimientos.

## Context
Tarjeta Trello PB-VAL-001 (https://trello.com/c/zDDVig5Z). Investigación y decisiones del usuario en el TASK (método validado; módulo «Costeo»; backend + asistente UI).

# Specification

## Domain context
Bounded context nuevo **Costeo** (`costing`), que lee cantidades de **Inventario** por su fachada. Catálogo aporta nombre y unidad base (vía Inventario).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Adopción de valoración | Acto único que fija la base monetaria inicial de la empresa | Tarjeta PB-VAL-001 |
| Corte | Momento de la confirmación; congela cantidades conciliadas y valores | Tarjeta / aclaración |
| Cantidad conciliada | Saldo total del producto (suma de almacenes) coincidente con el libro al confirmar | Tarjeta |
| Valor total inicial | Importe en BOB asignado al total del producto | Tarjeta |
| Costo unitario derivado | Valor total ÷ cantidad conciliada, 6 decimales, `ROUND_HALF_UP` | ADR |
| Pendiente | Línea sin valor; nunca equivale a cero | Tarjeta |
| Costo cero declarado | Valor 0 con declaración explícita | Tarjeta |

## Current behavior
Sin costos ni valoración (`backend/modules/inventory/` solo cantidades; ver TASK).

## Expected behavior
Con `costing` habilitado, el admin ve la propuesta de conciliación, ingresa valores, revisa y confirma. Queda una adopción inmutable con sus líneas; el libro de movimientos no cambia. Consultar la valoración muestra el corte y el valor por producto.

## Domain rules / invariants
- INV-01 (nueva): una empresa tiene como máximo una adopción; es inmutable.
- INV-02: `total_value` ≥ 0 con ≤ 2 decimales; `unit_cost = total_value / quantity` a 6 decimales `ROUND_HALF_UP`; sin `float`.
- INV-03: valor ausente = Pendiente (no se adopta); 0 solo con `declared_zero`; `declared_zero` con valor > 0 es inválido.
- INV-04: no se adopta con algún saldo negativo ni con cantidades distintas al saldo actual del libro.
- INV-05: la adopción no crea ni modifica movimientos de Inventario.
- INV-06: toda consulta filtra por `company_id`; la empresa sale del usuario autenticado.

## Acceptance criteria
- AC-01: adoptar crea una sola adopción con una línea por producto con saldo ≠ 0 y el libro de movimientos queda idéntico (sin nuevos movimientos).
- AC-02: el costo unitario derivado y el valor total se guardan con la precisión/redondeo de INV-02.
- AC-03: una línea sin valor se rechaza (400, error por línea «Pendiente»); valor 0 sin declaración se rechaza; con `declared_zero` se acepta.
- AC-04: con algún saldo total negativo → 409 `negative_stock` y no se guarda nada.
- AC-05: si cambió algún saldo (o el conjunto de productos) entre la propuesta y la confirmación → 409 `stock_changed` y no se guarda nada.
- AC-06: segunda adopción con otro `adoption_id` → 409 `valuation_already_adopted`; reenviar el mismo `adoption_id` con el mismo contenido → 200 réplica; mismo id con otro contenido → 409.
- AC-07: sin existencias (0 líneas) se puede adoptar.
- AC-08: con el módulo `costing` deshabilitado la API responde 403; `costing` solo se habilita si `inventory` lo está.
- AC-09: el aislamiento por empresa impide ver o adoptar sobre datos de otra.
- AC-10: UI: asistente de 3 pasos con resumen previo, estados cargando/vacío/error/éxito, y consulta de solo lectura tras adoptar; entrada «Valoración» visible solo con Costeo habilitado.

## Edge cases / Error cases
- EDGE-01: producto con saldo negativo en un almacén pero total positivo: se usa el total; se informa el desglose (decisión: el bloqueo aplica al saldo total por producto negativo, y también si cualquier almacén es negativo → bloquea; ver nota abajo).
- EDGE-02: producto sin control de stock: no se incluye.
- EDGE-03: cantidad con fracción: la cantidad conciliada conserva los 4 decimales del libro.
- EDGE-04: valor con más de 2 decimales o no numérico → 400 por línea.
- EDGE-05: `reconciled_quantity` o `product_id` repetido/ausente → 400.

Nota EDGE-01: se bloquea si **algún** par producto-almacén tiene saldo negativo (la tarjeta pide bloquear «stock negativo»); el desglose por almacén se devuelve en `negative_stock`.

## Authorization / permissions
Solo usuarios autenticados con empresa (rol admin hoy). Permiso por módulo `costing` (ADR de módulos). El frontend solo oculta la entrada.

## API contract
- API-01 `GET /api/valuation/` → `{status: 'not_adopted'|'adopted', adoption: {id, cutoff_at, method, user_name, lines: [{product_id, product_name, unit_abbreviation, reconciled_quantity, total_value, unit_cost, declared_zero, source}]} | null}`.
- API-02 `GET /api/valuation/proposal/` → `{lines: [{product_id, product_name, unit_abbreviation, reconciled_quantity, warehouses: [{warehouse_id, warehouse_name, quantity}]}], blockers: [{product_id, product_name, warehouse_id, warehouse_name, quantity}]}`.
- API-03 `POST /api/valuation/adopt/` body `{adoption_id, lines: [{product_id, reconciled_quantity, total_value, declared_zero, source}]}` → 201 (o 200 réplica) con la forma de API-01; errores 400 (por línea), 409 (`negative_stock`, `stock_changed`, `valuation_already_adopted`), 403.
Montos y cantidades como cadenas decimales. Compatibilidad: endpoints nuevos, sin cambios en los existentes (salvo `GET /api/modules/` que lista un módulo más).

## UI behavior
Según el DDR: UI-01 enlace «Valoración» en Inventario → Configuración solo con Costeo habilitado; UI-02 pasos Conciliar → Valores → Confirmar (plantilla «Formulario con líneas y paso de resumen»); UI-03 «Pendiente» y casilla «Costo cero»; UI-04 aviso de costo de gestión; UI-05 consulta de solo lectura; UI-06 bloqueos 409 en `alert alert-warning`; UI-07 idempotencia: la clave se genera al abrir y se reutiliza en reintentos.

## Non-functional requirements
Confirmar atómico bajo bloqueo de almacenes (orden por id); consultas con `company_id` indexado; textos en español.

## Out of scope
Costeo de consumos/ventas/compras, recálculo, revaluación o corrección de la adopción, corte retroactivo, costo por almacén, libros contables, reportes de valor.

# Test Specification

## Unit tests
Dominio: cálculo y redondeo (INV-02), Pendiente/costo cero (INV-03), validaciones de línea, inmutabilidad (no hay mutadores). Catálogo de módulos: `costing` requiere `inventory`, no es predeterminado.

## Integration tests
API/aplicación en `modules/costing/tests`: adopción feliz (AC-01/02/06/07), bloqueos 409 (AC-04/05), 403 sin módulo (AC-08), aislamiento (AC-09), libro sin cambios (AC-01), concurrencia con `select_for_update` (patrón `TASK-confirmar-cancelar-compras`). Frontend: specs de servicio (`valuation-api.service.spec.ts`), del cálculo de costo unitario/estado Pendiente y de la página (pasos, deshabilitar revisar con Pendiente, estados).

## E2E
**NO** — no es un flujo crítico de punta a punta ni exige instalar Playwright.

## Regression tests
Tests existentes de modularity (`test_domain.py`, `test_api.py`), inventario (`test_stock*`) y sidebar siguen verdes.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Integración: adopción + conteo de movimientos antes/después |
| AC-02 | Unit dominio + integración (valores persistidos) |
| AC-03 | Unit dominio + API 400 |
| AC-04 | Integración API 409 con stock negativo (política activada) |
| AC-05 | Integración: movimiento entre propuesta y adopción → 409 |
| AC-06 | Integración: réplica / otro id / otro contenido |
| AC-07 | Integración sin existencias |
| AC-08 | Integración 403 + unit catálogo de módulos |
| AC-09 | Integración con dos empresas |
| AC-10 | Specs Karma de página y servicio; revisión visual en `delivery-publish` |

# Implementation Plan

## Architecture considerations
Ver ADR. `costing` sigue las capas de `purchases`; el dominio no importa Django; infraestructura detrás de repositorio `DjangoValuationRepository(company_id)`.

## Proposed solution
Agregado `ValuationAdoption` + caso de uso `AdoptValuation`/`GetValuation`/`GetProposal` que leen Inventario por una fachada ampliada.

## Files/components affected
- Backend nuevo: `backend/modules/costing/{domain,application,infrastructure/django,api,tests,migrations}`, registro en `INSTALLED_APPS` y `config/urls.py` (`api/valuation/`).
- Backend modificado: `inventory/services.py` (+`get_company_balances`, `lock_company_stock`) y repositorio del libro (saldos por empresa), `modularity/domain/modules.py` (+`costing`), permiso por módulo para `costing`, tests de modularity.
- Frontend: `features/inventory/pages/valuation/`, `services/valuation-api.service.ts`, `models/valuation.ts`, ruta `inventory/valuation` con guardia de módulo `costing`, enlace en `inventory-configuration`, specs y fixtures.
- Docs: `docs/producto/modulos-implementados.md`.

## Implementation steps
1. Catálogo de módulos: agregar `costing` y ajustar tests (AC-08).
2. Fachada de Inventario: saldos totales por producto con desglose por almacén y bloqueo de la empresa (AC-04/05).
3. Dominio `costing`: valor, línea, adopción, redondeo, errores (INV-01..05, AC-02/03).
4. Modelos + migración `costing/0001`, repositorio (INV-01, INV-06).
5. Casos de uso y API `/api/valuation/` + serializers (AC-01..07, AC-09).
6. Pruebas backend (incluida concurrencia).
7. Frontend: modelos, servicio, página con pasos, ruta y enlace condicionado (AC-10).
8. Specs frontend y actualización de `docs/producto/modulos-implementados.md`.

## Database / migrations
Migración nueva `costing/0001_initial` (solo tablas nuevas); no se edita ninguna migración aplicada.

## Risks
Interbloqueos al bloquear varios almacenes (mitigado con orden por id); crecimiento del catálogo de módulos en la UI de módulos; redondeo del costo unitario (documentado, 6 decimales).

## New dependencies
Ninguna.
