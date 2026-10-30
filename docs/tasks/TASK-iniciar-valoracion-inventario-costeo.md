# TASK-iniciar-valoracion-inventario-costeo: Iniciar valoración de inventario para costeo (PB-VAL-001)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-iniciar-valoracion-inventario-costeo
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/36

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-30 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta Trello PB-VAL-001 | delivery-start |
| 2026-10-30 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | Módulo nuevo `costing`, tablas nuevas, pantalla nueva | delivery-start |
| 2026-10-30 | PLANNING → ENGINEERING | Specification READY, PR abierto | delivery-start |

## Investigación

### Requerimiento
Tarjeta Trello https://trello.com/c/zDDVig5Z — **PB-VAL-001 · Iniciar valoración de inventario para costeo** (P2, módulo Inventario y valoración; dependencias PB-INV-004 y PB-CAT-001).

Como administrador, asignar valores iniciales a las existencias para que los consumos posteriores tengan un costo conocido. Menú: Inventario → Configuración → Valoración (asistente de adopción y consulta de valores por producto); «capacidad opcional necesaria para Costeo». Datos: fecha de corte, producto, cantidad conciliada, unidad base, valor total inicial en BOB, costo unitario derivado, fuente y usuario. Método propuesto: promedio ponderado móvil por producto y empresa; cantidades siguen separadas por almacén. Acciones: conciliar cantidades, revisar valores, confirmar adopción. Costo cero requiere declaración explícita; costo ausente = «Pendiente», nunca cero.

Criterios de la tarjeta: (1) activar valoración no crea segunda apertura de cantidades ni altera movimientos; registra una base monetaria en un corte protegido; (2) método = propuesta técnica para costo de gestión, no política fiscal, sin mezclar con libros contables; (3) bloquear adopción con stock negativo o saldo sin conciliar; sin valores completos no se habilita Costeo; (4) decimales con precisión interna suficiente, importes BOB, redondeo explícito, historial, sin recalcular el pasado.

**Aclaraciones del usuario (2026-10-30):**
1. El promedio ponderado móvil queda **validado** como método de costo de gestión.
2. La «capacidad opcional» se modela como **módulo nuevo «Costeo»** (opcional, requiere Inventario, deshabilitado por defecto); la valoración vive en Inventario → Configuración y exige Costeo habilitado.
3. Alcance: **backend + asistente UI**. Corte = momento de la confirmación (hoy); el admin ingresa el valor total en BOB por producto; costo unitario derivado; ausente = Pendiente (bloquea la adopción); 0 solo con declaración explícita; corte inmutable tras confirmar.

### Hechos encontrados
- `backend/modules/inventory/` ya tiene `domain/ application/ infrastructure/ api/` y migraciones 0001-0003; libro de movimientos inmutable `StockMovementModel` (`infrastructure/django/models.py:27`) con `quantity` Decimal(16,4) y saldo calculado (sin tabla de saldos), por producto y almacén.
- La apertura de cantidades (PB-INV-003) usa el libro: `application/stock_use_cases.py` (`RegisterOpening`). No existe concepto de costo/valoración en ningún módulo (solo `docs/producto/modulos-implementados.md` lo cita, como «sin valoración»).
- Fachada pública de Inventario: `backend/modules/inventory/services.py` (`get_balance`, `get_balances` por almacén y productos, `list_active_warehouses`, `get_stock_products`, `allow_negative_stock`). No hay función que devuelva el saldo total por producto de la empresa.
- Repositorio del libro: `movement_repository.py:97` `locked(warehouse_id)` (bloqueo por almacén), `:167` `balances_for`, `:190` `list_balances`.
- Catálogo de módulos: `backend/modules/modularity/domain/modules.py:16` `MODULE_CATALOG` (inventario: `requires=('catalog',)`); `DEFAULT_ENABLED_KEYS` en `:27`. Tests de catálogo en `modularity/tests/test_domain.py` y `test_api.py:40`.
- Puerto de módulos habilitados: `backend/shared/module_gate.py`; el permiso por módulo de la API sigue `docs/adr/ADR-bloquear-api-modulos-deshabilitados-permiso-por-modulo.md`.
- Ajuste `inventory.allow_negative_stock` (`modularity/domain/settings.py`) permite saldos negativos, por lo que la adopción debe detectarlos.
- Montaje de URLs en `backend/config/urls.py:14-17`.
- Frontend: `frontend/panel_admin/src/app/features/inventory/` con `pages/inventory-configuration`, `pages/stock-opening` (plantilla «Formulario con líneas y paso de resumen»), `services/`, `models/`, `testing/`.
- Sistema de diseño: `docs/design/design-system.md` (secciones 5: «Configuración con listados en pestañas», «Formulario con líneas y paso de resumen», «Sección condicionada por módulo»).

### Hipótesis / supuestos no confirmados
- Una empresa tiene **una sola adopción** (corte único); rehacer o reiniciar la valoración queda fuera de alcance.
- Se valoran los productos que controlan stock con saldo total (suma de almacenes) distinto de cero; con saldo cero no se pide valor.
- Con la empresa sin existencias se permite adoptar con 0 líneas.
- Fuente = texto libre por línea (por defecto «Ingreso manual»).

### Módulos y dependencias relacionadas
`inventory` (cantidades, almacenes), `catalog` (nombre, unidad base vía `ProductDirectory`), `modularity` (catálogo de módulos). Módulo nuevo `costing` → `inventory` (solo fachada).

### Implementaciones similares existentes
Apertura de existencias (`RegisterOpening`: idempotencia por clave del cliente, 409 con detalle, todo o nada bajo bloqueo) y su pantalla `stock-opening`; `purchases` como módulo opcional con capas completas.

### Comportamiento actual
No hay costos ni valoración; Inventario solo conoce cantidades.

### Restricciones
`company_id` en toda consulta; dinero en `Decimal`; no editar migraciones aplicadas; los módulos se hablan por fachada; el frontend no es la barrera de seguridad.

### Riesgos identificados
- Concurrencia: un movimiento entre «revisar» y «confirmar» invalidaría la cantidad conciliada (se resuelve bloqueando almacenes y comparando).
- Cambiar `MODULE_CATALOG` toca tests de modularity y la pantalla de módulos.
- Redondeo del costo unitario frente al futuro costeo.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — módulo nuevo (`costing`), tablas y migración nuevas, dependencia entre módulos, cambio en el catálogo de módulos y cálculo de dinero.

### Diseño requerido
**SI** — pantalla nueva de asistente (conciliar → valores → confirmar) y de consulta.

## Diseño
`docs/design/DDR-iniciar-valoracion-inventario-costeo-asistente-valoracion.md`.

## Arquitectura
`docs/adr/ADR-iniciar-valoracion-inventario-costeo-modulo-costeo-y-adopcion.md`.

## Plan
`docs/plans/PLAN-2026-10-30-iniciar-valoracion-inventario-costeo.md` (v1, COMPLETO, READY).

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
