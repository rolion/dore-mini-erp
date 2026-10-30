# TASK-iniciar-valoracion-inventario-costeo: Iniciar valoración de inventario para costeo (PB-VAL-001)

**Etapa actual:** PUBLISH
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
| 2026-10-30 | ENGINEERING → REVIEW | Implementación completa según el PLAN v1 | delivery-build |
| 2026-10-30 | REVIEW → PUBLISH | Quality Gate PASS (2 hallazgos Low abiertos) | delivery-publish |

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

**Resumen.** Módulo nuevo `costing` y adopción de valoración inicial según ADR/PLAN v1, sin desviaciones de la Specification.

- **Catálogo de módulos** (`modularity/domain/modules.py`): `costing` («Costeo», requiere `inventory`, no predeterminado) — AC-08. Tests de modularity actualizados.
- **Fachada de Inventario** (`inventory/services.py`, `movement_repository.py`): `get_company_stock`, `lock_company_stock` (bloquea todos los almacenes de la empresa por id), `get_product_names` — AC-04/05/INV-04.
- **Backend `costing`** (`backend/modules/costing/`): dominio (`valuation.py`: redondeo 6 decimales `ROUND_HALF_UP`, Pendiente/costo cero declarado, adopción inmutable; INV-01..05, AC-02/03), caso de uso `AdoptValuation` (409 `negative_stock`/`stock_changed`/`valuation_already_adopted`/`adoption_id_reused`, réplica 200; AC-01/04/05/06/07), repositorio por `company_id` (INV-06, AC-09), migración `costing/0001`, API `/api/valuation/` (`GET`, `GET proposal/`, `POST adopt/`) con permiso por módulo `costing` (AC-08).
- **Frontend** (`features/inventory`): `models/valuation.ts` (estado de línea y costo unitario en aritmética entera), `valuation-api.service.ts`, `pages/valuation` (asistente Conciliar → Valores → Confirmar y consulta de solo lectura), ruta `inventory/valuation` con `moduleGuard` (`costing`) y `unsavedChangesGuard`, enlace «Valoración» en Almacenes y unidades solo con Costeo habilitado — AC-10, UI-01..07.
- **Pantalla de referencia:** `stock-opening` («Formulario con líneas y paso de resumen») y `inventory-configuration`; reutiliza `MoneyPipe`, `_inventory-table.scss`, badges y `alert-*`. No se crearon componentes compartidos ni se modificó `design-system.md`.
- **Docs:** `docs/producto/modulos-implementados.md`.

**Tests añadidos.** Backend `costing/tests/test_valuation.py` (29: dominio, API, módulo, aislamiento, concurrencia); guardas existentes ampliadas con `costing` (`accounts/test_guards.py`, `sales/tests/test_boundaries.py`). Frontend: `valuation-api.service.spec.ts`, `valuation.component.spec.ts`, spec de `inventory-configuration` ampliado.

**Verificación propia (no es el Quality Gate).** Backend `manage.py test` completo 1159 OK; `makemigrations` sin cambios pendientes tras la migración. Frontend: `ng lint` OK, `ng build` OK, Karma acotado (inventory + layout) 176 OK / 1 fallo preexistente (`FooterComponent should create`, plantilla), con `app.component.spec.ts` apartado temporalmente (roto en `main`, restaurado sin cambios). Revisión visual en navegador: no verificada. Entorno: `.env` copiado del checkout principal sin abrirlo (no versionado) y `node_modules` por enlace; sin dependencias nuevas.

**Desviaciones respecto al plan.** Ninguna de Specification. Detalles de implementación: el enlace a «Valoración» está en la pantalla Almacenes y unidades y, tras un reporte de uso (no se encontraba cómo iniciar la valoración con Costeo habilitado), también como ítem del menú Inventario visible solo con Costeo (el menú ahora filtra subítems por módulo: `visibleRoutes` en `sidebar.component.ts`, `routes.json`, i18n es/en/de); el bloqueo por stock negativo se evalúa por par producto-almacén y el total (EDGE-01, como aclara el plan); `ENABLED`/E2E: NO según plan.

**Deuda técnica.** `app.component.spec.ts` roto en `main` y specs de plantilla fallando (preexistente). Una prueba intermitente por orden en `accounts.test_migrations` (preexistente, pasa aislada).

## Review
**Veredicto: PASS** (revisor en subagente aislado, 2026-10-30). Sin hallazgos Critical/High.

- Backend `manage.py test`: 1159 OK; `makemigrations --check`: sin cambios.
- Frontend: `ng lint` OK, `ng build` OK, Karma acotado (inventory + layout) 176 OK / 1 fallo preexistente (`FooterComponent should create`); cobertura del subconjunto: sentencias 77,2 %, ramas 68,1 %, funciones 74,2 %, líneas 77,9 %.
- bandit sobre el código nuevo: 0 Medium/High (1 Low, falso positivo en un docstring).
- Límites DDD, `company_id`, `Decimal` y migración: conformes. Todos los AC/INV/API/UI del PLAN tienen verificación; sin scope creep.
- No realizado: ruff, mypy y `npm audit` (no disponibles), cobertura por archivo, Karma completo del repo, revisión visual en navegador (**no verificada**).

Hallazgos Low (**resueltos después del PASS**: REV-01 movió el enlace «Valoración» fuera del `tablist` al encabezado de la tarjeta; REV-02 agregó el `alert-success` del DDR tras adoptar; Karma de `features/inventory` 157 OK y `ng lint` OK tras el cambio): [REV-01](../reviews/REV-2026-10-30-iniciar-valoracion-inventario-costeo-01.md) enlace «Valoración» dentro de un `tablist` sin rol de pestaña; [REV-02](../reviews/REV-2026-10-30-iniciar-valoracion-inventario-costeo-02.md) el DDR pide `alert-success` y la implementación usa un toast (patrón de `stock-opening`).

## Publicación
PR https://github.com/rolion/dore-mini-erp/pull/36 listo para aprobación humana (no se mergea desde el flujo). Cambio sensible: **base de datos** (migración nueva `costing/0001`, solo tablas nuevas) y **catálogo de módulos/autorización por módulo**; respaldado por el ADR `ADR-iniciar-valoracion-inventario-costeo-modulo-costeo-y-adopcion`.
