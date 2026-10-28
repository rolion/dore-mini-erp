# TASK-ajustar-existencias-con-motivo: Ajustar existencias con motivo (PB-INV-006)

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-ajustar-existencias-con-motivo
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/23

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-28 | (nuevo) → INVESTIGATION | Task creado sobre `origin/main` (PB-INV-003 y PB-INV-004 ya integrados) | delivery-start |
| 2026-10-28 | INVESTIGATION → DESIGN → PLANNING | NEEDS_PLAN: una tabla nueva en `inventory` sobre el libro y la fachada existentes; sin decisión arquitectónica nueva | delivery-start |
| 2026-10-28 | PLANNING → ENGINEERING | Specification READY (supuestos documentados en el Plan, ninguno bloqueante) | delivery-start |
| 2026-10-28 | ENGINEERING → REVIEW | Implementación completa según plan v1 | delivery-build |
| 2026-10-28 | REVIEW → ENGINEERING | Ciclo 1 sin PASS: REV-01 (Medium, cantidades enormes dan 500) y REV-02 (Low, clave de otra empresa da 500) | delivery-publish |
| 2026-10-28 | ENGINEERING → REVIEW | REV-01 y REV-02 corregidos con tests de regresión (106 tests de inventory OK) | delivery-build |

## Investigación

### Requerimiento
**PB-INV-006 · Ajustar existencias con motivo** (Inventario, P1, dep. PB-INV-003 y PB-INV-004). Como administrador, quiero registrar diferencias de conteo para corregir stock conservando la trazabilidad.

- Menú y vistas: Inventario → Ajustes: listado, formulario «Nuevo ajuste» y detalle confirmado.
- Listado: referencia, fecha, producto, almacén, cantidad del sistema al confirmar, cantidad contada, diferencia, usuario y estado confirmado/revertido. Filtros por fecha, producto y almacén.
- Formulario: producto y almacén obligatorios, saldo actual de solo lectura, cantidad contada no negativa, unidad y motivo obligatorio. Diferencia y sentido entrada/salida se calculan solos.
- Acciones: revisar y confirmar; cancelar abandona el formulario. Un ajuste confirmado es de solo lectura y ofrece «Revertir» cuando PB-INV-008 lo permita.
- Interfaz: diferencia cero ⇒ «Sin diferencia» y ningún movimiento; si el saldo cambia antes de confirmar se muestra el nuevo saldo y se exige revisar y reconfirmar.
- AC: (1) producto, almacén, cantidad contada y motivo obligatorio; el sistema calcula la diferencia; (2) confirmar genera la entrada o salida de ajuste sin sobrescribir el historial; (3) si el saldo cambió entre el conteo previo y la confirmación, se exige revisar la diferencia antes de aplicarla.

### Hechos encontrados
- `backend/modules/inventory/domain/movement.py:33-36` — el catálogo `SOURCE_TYPES` ya incluye `inventory_adjustment` («Ajuste de inventario», módulo `inventory`); nadie lo produce todavía.
- `backend/modules/inventory/services.py:39-60` — fachada `record_movement(company_id, …, source_type, source_id)` idempotente por origen; `get_balance` (`:73-75`).
- `backend/modules/inventory/application/movement_use_cases.py:21-65` — `RecordMovement`: valida producto (`tracks_stock`, fracciones), almacén activo y saldo bajo `repository.locked(warehouse_id)`; `ReverseMovement` (`:68-87`) ya existe como caso de uso (sin endpoint HTTP: lo trae PB-INV-008).
- `backend/modules/inventory/application/stock_use_cases.py:46-95` — `RegisterOpening` es el patrón a seguir: clave de idempotencia del cliente, `locked`, reintento = réplica 200 / 201 al crear, contenido distinto = 409.
- `backend/modules/inventory/domain/stock.py:12-33` — `validate_quantity` (no negativa, hasta 3 decimales, nunca `float`) y `check_quantity_for_unit`; reutilizables para la cantidad contada.
- `backend/modules/inventory/infrastructure/django/models.py:28-65` — libro `StockMovementModel` (solo `status` cambia); `domain/repositories.py:30-74` — puerto `StockMovementRepository` con `locked`, `balance`, `find_by_source_id`.
- `backend/modules/inventory/api/stock_views.py:62-115` — `OpeningCreateView` (mapeo de errores a 400/404/409 con `Conflict`), `_parse_uuid`; `api/movement_views.py:25-82` — `MovementPresenter` (nombres de producto/almacén, unidad, `available` del origen) y paginación de 25.
- `backend/modules/inventory/infrastructure/django/models.py` y `migrations/0002_stock_movements.py` — última migración de `inventory`; la nueva sería `0003`.
- `backend/config/urls.py:14-16` — `api/warehouses/`, `api/stock-movements/`, `api/stock/`.
- Frontend: `features/inventory/pages/stock-opening/` (formulario editar→resumen→confirmar con clave de idempotencia, `unsavedChangesGuard`), `pages/movement-list/` y `movement-detail/` (lista con filtros y paginación de servidor, detalle de solo lectura), `inventory.routes.ts:6-9`, `app.routes.ts:105-142` (rutas con `moduleGuard`), `assets/data/routes.json`, `layout/sidebar/sidebar-menu.spec.ts`.
- `docs/design/design-system.md:153` — el submenú de Inventario ya tiene una entrada «Ajustes» (`/inventory/settings`, configuración del módulo de PB-CFG-001): **colisión de nombre** con «Inventario → Ajustes» de esta historia.
- `docs/design/DDR-registrar-existencias-iniciales-pantallas-existencias-apertura.md` — la apertura remite las correcciones a «un ajuste» (mensaje 409 `stock_history_exists`).

### Hipótesis / supuestos no confirmados
- No existe el concepto de «ajuste» como documento: `inventory_adjustment` es solo una clase de origen. Hace falta persistir el ajuste (referencia, saldo del sistema al confirmar, cantidad contada, diferencia) porque el movimiento solo guarda la cantidad de la diferencia.
- Diferencia cero: no se crea ajuste ni movimiento (no hay nada que trazar); la API lo rechaza con 409 `no_difference` como defensa, y la UI lo informa antes.
- El estado «revertido» del ajuste se deriva del movimiento vinculado (`reversed`); el botón «Revertir» no se muestra hasta PB-INV-008 (no hay endpoint de reversión).
- Se permite ajustar un producto sin movimientos previos (saldo 0): equivale a una entrada justificada.
- La referencia del ajuste se genera en el servidor (`AJ-` + 8 hex del id).

### Módulos y dependencias relacionadas
`inventory` (propietario del ajuste y del libro); `catalog` solo por `ProductDirectory` ya existente; `modularity` por `required_modules`. Sin dependencias nuevas entre módulos.

### Implementaciones similares existentes
Apertura de existencias (backend y `stock-opening`), lista/detalle de movimientos.

### Comportamiento actual
No hay forma de corregir stock: el saldo solo cambia con aperturas y movimientos de otros módulos.

### Restricciones
`Decimal` siempre; aislamiento por `company_id`; no editar migraciones aplicadas; sin dependencias nuevas; el dominio no importa Django; los módulos no se importan infraestructura.

### Riesgos identificados
- Carrera entre leer el saldo y confirmar: se resuelve comparando el saldo esperado bajo el bloqueo del almacén.
- Reintento tras éxito con saldo ya cambiado: la réplica debe evaluarse antes que la comparación de saldo.
- Nombre «Ajustes» ya usado en el menú por la configuración.

### Veredicto de complejidad
**NEEDS_PLAN** — Una tabla nueva y una pantalla de lista/formulario/detalle sobre fachada, repositorio y patrones ya decididos en los ADR de PB-INV-003/004; no cambia fronteras entre módulos, autenticación ni infraestructura.

### Diseño requerido
**SI** — Tres pantallas nuevas y un flujo de dos pasos con confirmación y reconfirmación.

## Diseño
`docs/design/DDR-ajustar-existencias-con-motivo-pantallas-ajustes-existencias.md`

## Arquitectura
No aplica según veredicto (se sigue `ADR-inventario-movimientos-trazables-registro-idempotente-y-saldo` y `ADR-registrar-existencias-iniciales-…`).

## Plan
`docs/plans/PLAN-2026-10-28-ajustar-existencias-con-motivo.md` (v1, COMPLETO)

## Implementación

**Resumen.** Backend en `inventory`: dominio `StockAdjustment` (`domain/adjustment.py`: diferencia, validaciones, referencia `AJ-xxxxxxxx`), caso de uso `ConfirmAdjustment` (`application/adjustment_use_cases.py`: bloqueo del almacén, réplica antes de comparar saldo, `BalanceChanged`, movimiento con `RecordMovement`), modelo y migración `0003_stock_adjustments`, repositorio `DjangoStockAdjustmentRepository(company_id)`, API `api/adjustment_{views,urls}.py` registrada en `config/urls.py`. Frontend en `features/inventory`: `adjustments-api.service`, `adjustment-list`, `adjustment-form` (dos pasos, «Sin diferencia», reconfirmación), `adjustment-detail`, rutas con `moduleGuard`, entrada de menú «Ajustes de existencias» (+ i18n es/en/de y `routes.json`), botón «Ajustar» en Existencias y enlace de origen `inventory_adjustment` en el detalle de movimiento.

**Cobertura.** AC-01/INV-03/INV-05: tests de dominio y API (400 por campo) + spec del formulario. AC-02/INV-07: `test_confirming_*`. AC-03/INV-06: `test_changed_balance_*`, concurrencia `test_two_counts_*` y spec de reconfirmación. AC-04/INV-04: dominio, API y spec. AC-05/AC-06: lista, filtros, detalle, 405 y specs. AC-07/INV-08: idempotencia secuencial y concurrente + doble clic. INV-09: aislamiento por empresa, 403 de miembros y módulo deshabilitado.

**Desviaciones respecto al plan.** (1) No se creó la fachada `adjust_stock` en `services.py` (el plan la dejaba opcional); la usará PB-INV-008 si hace falta. (2) La validación del producto ajeno responde 400 `product_id` antes que el 404 de almacén (el 404 se da con producto propio y almacén inexistente). (3) Fixtures de ajustes en `testing/adjustment-fixtures.ts` (archivo nuevo) en vez de ampliar `inventory-fixtures.ts`.

**UI.** Pantallas de referencia: lista = `stock-list` (tabla `inventory-table` + `ngb-pagination`) con filtros de `movement-list`; formulario = `stock-opening` (editar → resumen → confirmar con clave de idempotencia, `appendTo="body"`); detalle = `movement-detail`. Componentes compartidos reutilizados: `OpeningProductsService`, `WarehousesApiService`, `ProductsApiService`, `unsavedChangesGuard`, `ToastrService`. No se creó ningún componente compartido nuevo.

**Deuda técnica.** Dos entradas parecidas en el menú de Inventario («Ajustes» y «Ajustes de existencias») hasta unificar nombres; la UI no ofrece «Revertir» hasta PB-INV-008; `OpeningProduct` se reutiliza como tipo de producto del formulario de ajuste.

**Verificación propia (no es el Quality Gate).** Backend `manage.py test` 802 OK (incluye concurrencia con PostgreSQL), `makemigrations --check` sin cambios. Frontend: Karma acotado (inventory + sidebar) 103/103 OK con `app.component.spec.ts` apartado temporalmente (roto en `main`, restaurado sin cambios), `ng lint` OK, `ng build` OK. Revisión visual en navegador: no verificada. Entorno: `.env` copiado del checkout principal sin abrirlo (no versionado), `.venv` del checkout principal y `node_modules` por enlace.

## Review
**Ciclo 1: sin PASS.** Subagente aislado: backend 802 OK, Karma acotado 103/103, suite completa 71 fallos = línea base (ninguno en inventory ni sidebar), lint y build OK, bandit sin hallazgos en inventory, `makemigrations --check` limpio. Hallazgos: `docs/reviews/REV-2026-10-28-ajustar-existencias-con-motivo-01.md` (Medium) y `-02` (Low), ambos corregidos (tope de cantidad antes de `quantize`; `IntegrityError` de clave ajena → 409 `adjustment_id_reused`). Revisión visual en navegador: no verificada (levantar la app habría escrito en la base de desarrollo del usuario). `npm audit`: no realizable (sin lockfile).

## Publicación
_Pendiente_
