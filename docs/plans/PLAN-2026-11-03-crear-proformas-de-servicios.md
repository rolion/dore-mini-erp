# PLAN-2026-11-03-crear-proformas-de-servicios (v3)

**Task:** TASK-crear-proformas-de-servicios · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** [DDR](../design/DDR-crear-proformas-de-servicios-pantallas-proformas.md) · [ADR](../adr/ADR-crear-proformas-de-servicios-contexto-congelacion-y-versiones.md)

## Objective
Permitir al operador elaborar, guardar y presentar proformas de servicios con líneas cuyo nombre y precio quedan congelados al incorporarlas, con total recalculado por el servidor y sin generar obligaciones de cobro.

## Context
Ver el TASK. Rama base: `task/TASK-agendar-y-gestionar-citas` (PR #50) por indicación del usuario; este PR se apila sobre ese.

# Specification

## Domain context
Nuevo bounded context **Cotizaciones** (`quotations`). Consume Servicios y Clientes solo por fachadas.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Proforma | Documento comercial con servicios, precios y condiciones | Tarjeta |
| Línea | Servicio + descripción y precio congelados + cantidad | Tarjeta |
| Total propuesto | Suma de subtotales calculada por el servidor | Tarjeta |
| Total aceptado | Monto aceptado por el cliente; fuera de esta historia | Tarjeta |
| Versión | Copia numerada de una proforma presentada | Tarjeta (semántica asumida, ver Open questions) |

## Current behavior
No hay cotizaciones; el catálogo expone `get_service_for_new_use` (`service_catalog/services.py:34`).

## Expected behavior
Existe el agregado Proforma con numeración por empresa y versiones; los precios de las líneas no cambian cuando cambia el catálogo; guardar o presentar no crea ventas, cuentas por cobrar, pagos ni movimientos de stock.

## Domain rules / invariants
- INV-01 Cantidad > 0 (máx. 9999.99, 2 decimales); precio unitario ≥ 0 (2 decimales); subtotal = cantidad × precio redondeado a 2 decimales (`ROUND_HALF_UP`); total = suma de subtotales. Todo en `Decimal`.
- INV-02 Al incorporar una línea se copian nombre y precio vigentes del servicio (activo, de la empresa); las líneas existentes no se vuelven a leer del catálogo.
- INV-03 Solo se editan líneas/cabecera en `draft`. `present()` exige ≥ 1 línea válida y cliente. Estados `draft → presented → superseded`; sin otras transiciones.
- INV-04 Número `PRO-NNNNNN` consecutivo por empresa; `(empresa, número, versión)` único.
- INV-05 «Nueva versión» solo desde `presented`, copia líneas congeladas y exige que no haya otro borrador del mismo número; al presentar la versión nueva la anterior pasa a `superseded`.
- INV-06 Cliente activo al crear y **cada vez que se guarda** un borrador (también si es el mismo cliente de antes), al **presentar** y al crear una **nueva versión**; `customer_name` se guarda como snapshot. Vigencia opcional ≥ fecha de la proforma.
- INV-07 Moneda siempre BOB. `accepted_total` no se expone ni se calcula.

## Acceptance criteria
- AC-01 Dos servicios de 100 y 150 (cantidad 1) → total 250.00; cambiar luego precio o nombre en el catálogo, o desactivar el servicio, no altera la proforma guardada.
- AC-02 Cantidad 0 o negativa y precio negativo se rechazan (400) con error por línea; el servidor ignora subtotales/total enviados y los recalcula.
- AC-03 Un `unit_price` distinto del vigente solo se acepta si el usuario puede editar precio; si no, 403 y nada se guarda.
- AC-04 Servicio inactivo, ajeno o inexistente, o cliente inactivo/ajeno, se rechazan al incorporarlos.
- AC-05 Presentar sin líneas → 400/409; con líneas pasa a `presented` y queda inmutable (editar → 409).
- AC-06 Guardar el borrador repetidamente no crea ninguna venta, cuenta por cobrar, pago ni movimiento (el módulo no tiene dependencia hacia ellos; verificado por prueba de límites y por conteo de filas).
- AC-07 Numeración consecutiva por empresa, única bajo creaciones concurrentes y independiente entre empresas.
- AC-08 Nueva versión copia líneas congeladas, incrementa versión, y al presentarla la anterior queda `superseded`; el detalle lista las versiones.
- AC-09 Lista paginada filtrable por cliente (búsqueda), rango de fechas y estado, aislada por empresa; detalle devuelve `allowed_actions` y `can_edit_price`.
- AC-10 Módulo `quotations` deshabilitado → 403 `module_disabled`; ajeno → 404; requiere `services` y `customers` para habilitarse.
- AC-11 UI según DDR: tabla editable con subtotales y total a 2 decimales, «cambios sin guardar», errores por línea, estados cargando/vacío/error/éxito, doble envío bloqueado, teclado, confirmación al presentar.

## Edge cases / Error cases
Cabecera sin cliente → 400; vigencia anterior a la fecha → 400; más de 200 líneas → 400; línea repetida del mismo servicio permitida; borrar todas las líneas de un borrador permitido (solo falla al presentar); `page`/`page_size` inválidos → 400.

## Authorization / permissions
Admin de empresa activa y módulo `quotations` habilitado (permiso por defecto). `can_edit_price(user)` = admin hoy. Empresa siempre de la sesión.

## API contract
- API-01 `GET/POST /api/quotations/proformas/` (filtros `customer`, `from`, `to`, `status`; paginado).
- API-02 `GET/PUT /api/quotations/proformas/{id}/` (PUT reemplaza cabecera y líneas de un borrador; líneas con `id` conservan snapshot, sin `id` se capturan del catálogo).
- API-03 `POST …/{id}/present/`, `POST …/{id}/new-version/`.
- Respuesta: `number`, `version`, `status`, `customer`, `date`, `valid_until`, `currency`, `notes`, `lines[]` (`id`, `service_id`, `description`, `quantity`, `unit_price`, `subtotal`, `treatment_item_id`, `piece`), `total`, `allowed_actions`, `can_edit_price`, `versions[]`.
Compatibilidad: rutas existentes sin cambios.

## UI behavior
UI-01 Lista · UI-02 Formulario con tabla de líneas · UI-03 Detalle con versiones · UI-04 Diálogo «Presentar», según el DDR y `design-system.md` §5.

## Non-functional requirements
Mensajes en español; consultas sin N+1; migración aditiva.

## Out of scope
Aceptar/rechazar/vencer, total aceptado, conversión a venta/cobro, PDF/impresión, envío por correo, tratamientos y piezas (columnas reservadas sin validar), descuentos e impuestos, múltiples monedas, roles distintos de admin, Sucursales.

## Open questions
No bloquean (se asumió lo indicado): semántica de versiones (copia inmutable + «Nueva versión»); si la interpretación de «referencia autorizada» exige validar tratamiento/pieza en esta historia (se difiere); nombre del permiso de precio cuando existan roles.

# Test Specification

## Unit tests
Dominio puro: INV-01 (redondeo, 100+150), INV-02/03/05 (transiciones, líneas congeladas, presentar sin líneas).

## Integration tests
API con dos empresas, módulo deshabilitado, snapshot tras cambiar catálogo, precio no autorizado (con `can_edit_price` parcheado a falso), cliente/servicio inactivos o ajenos, paginación, filtros, `TransactionTestCase` con `Barrier` para numeración concurrente (PostgreSQL), conteo de filas en `sales`/`inventory` sin cambios, límites de módulos en `test_boundaries`, catálogo de módulos y dependencias.

## E2E
**NO** — se cubre con integración y recorrido local; sin Playwright.

## Regression tests
Suites de `modularity`, `service_catalog`, `agenda`, `sales` (límites) siguen verdes; specs del sidebar.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Dominio + integración |
| AC-02 | Dominio + integración |
| AC-03 | Integración |
| AC-04 | Integración |
| AC-05 | Dominio + integración |
| AC-06 | Prueba de límites + integración |
| AC-07 | Integración concurrente en PostgreSQL |
| AC-08 | Integración |
| AC-09 | Integración |
| AC-10 | Integración + modularity |
| AC-11 | `ng build`, specs de servicio/componentes y recorrido local |

# Implementation Plan

## Architecture considerations
Según ADR: dominio puro, contador bloqueado, fachadas por adaptador, snapshots, migración aditiva.

## Proposed solution
`quotations/application/proformas.py` orquesta (leer fachadas → construir/mutar agregado → persistir en transacción); vistas delgadas y serializers de forma; frontend en `features/quotations/`.

## Files/components affected
- Backend: `modules/quotations/{domain/proforma.py, application/proformas.py, infrastructure/{adapters.py,django/{models,repositories}.py}, api/{serializers,views,urls}.py, migrations/0001_initial.py, tests/}`, `config/settings/base.py`, `config/urls.py`, `modularity/domain/modules.py` (+ tests), `sales/tests/test_boundaries.py`.
- Frontend: `features/quotations/{models,services,pages,components}`, `app.routes.ts`, `assets/data/routes.json`, i18n `es/en/de`, spec del sidebar.
- Docs: `design-system.md` no cambia.

## Implementation steps
1. Dominio `Proforma` y pruebas (INV-01..07, AC-01, 02, 05).
2. Módulo en catálogo de `modularity`, app Django, modelos y migración 0001 (AC-07, AC-10).
3. Adaptadores a Servicios/Clientes, caso de uso de crear/editar/presentar y política `can_edit_price` (AC-01..06).
4. Numeración con contador y nueva versión (AC-07, AC-08).
5. Endpoints, serializers, lista/filtros, detalle y límites de módulos (AC-09, AC-10).
6. Frontend: servicio, lista, formulario con tabla de líneas, detalle, diálogo, menú y rutas (AC-11).
7. Verificaciones de la Test Specification y registro de resultados.

## Database / migrations
`quotations/0001_initial` aditiva: `Proforma`, `ProformaLine`, `ProformaCounter`; `CheckConstraint` de cantidad > 0, precio ≥ 0; únicos `(company_id, number, version)` y contador por empresa; índices `(company_id, status, date)` y `(company_id, customer_id)`. No se editan migraciones aplicadas.

## Risks
Numeración concurrente (contador bloqueado + prueba); conflictos de fusión con la rama base; redondeo en cantidades decimales; ambigüedad de versiones (supuesto declarado); edición concurrente de un mismo borrador (último guardado gana; fuera de alcance).

## New dependencies
Ninguna.

## Changelog
- **v3** (2026-11-04): [Specification] INV-06 extendida a presentar y nueva versión tras aprobación explícita del usuario en el chat (REV-09).
- **v2** (2026-11-03): [Specification] INV-06 aclarada tras aprobación explícita del usuario en el chat: guardar un borrador exige cliente activo aunque no haya cambiado (REV-04).
